# app.py — Launch Flask server and provide API endpoints for frontend data access

import os
import re
import json
import hashlib
from datetime import timedelta
from functools import wraps
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request, abort, session
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# --- Basic Config ---
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=14)
CORS(
    app,
    resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}},
    supports_credentials=True,
)

# --- Error Handlers ---
@app.errorhandler(HTTPException)
def handle_http_error(e: HTTPException):
    return jsonify({"code": e.code, "message": e.description}), e.code

@app.errorhandler(Exception)
def handle_any_error(e: Exception):
    app.logger.exception(e)
    return jsonify({"code": 500, "message": str(e)}), 500


# --- Paths ---
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data" / "raw" / "reddit"

SUBMISSIONS_CANDIDATES = [
    DATA_DIR / "final_data_demoB.csv",
    DATA_DIR / "final_data_demoB.parquet",
    DATA_DIR / "final_data_demoB.xlsx",
    DATA_DIR / "reddit_data.csv",
    DATA_DIR / "submissions_cleaned.csv",
    DATA_DIR / "reddit_data",
]
COMMENTS_CSV = DATA_DIR / "comments_cleaned.csv"

USERS_DIR = ROOT_DIR / "data" / "user"
USERS_CSV = USERS_DIR / "user.csv"

# --- Utils (safe helpers) ---
def _first_existing(paths):
    for p in paths:
        if p.exists():
            return p
    return None

def _read_csv_safe(path: Path) -> pd.DataFrame:
    if not path or not path.exists():
        abort(404, description=f"{path} not found")
    suf = path.suffix.lower()
    if suf == ".parquet":
        return pd.read_parquet(path)
    if suf in (".xlsx", ".xls"):
        return pd.read_excel(path)
    tried = []
    for enc in [None, "utf-8", "utf-8-sig", "gb18030", "gbk", "latin1"]:
        try:
            return pd.read_csv(path, sep=None, engine="python", encoding=enc, on_bad_lines="skip")
        except Exception as e:
            tried.append(f"{enc or 'default'}: {e}")
    abort(500, description=f"Failed to read {path.name}. Tried -> " + " | ".join(tried))

def _str_series(x):
    # 将 NaN 变空串，避免 JSON 里出现 NaN
    if isinstance(x, pd.Series):
        s = x.astype(str).fillna("").str.strip()
        s = s.mask(s.str.lower().isin(["nan", "none", "null"]), "")
        return s
    return pd.Series(dtype=object)

def _to_ymd(s: pd.Series) -> pd.Series:
    ts = pd.to_datetime(s, errors="coerce", utc=False, format="mixed")
    out = ts.dt.strftime("%Y-%m-%d")
    out = out.where(~ts.isna(), _str_series(s))
    return out

def _s(v):
    # 单值安全字符串化
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return ""
    except Exception:
        pass
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none", "null") else s

def _normalize_parent_id(pid: str) -> str:
    if not pid:
        return ""
    if "_" in pid:
        return pid.split("_", 1)[1]
    return pid

def _split_pipes(s):
    txt = _s(s)
    return [p.strip() for p in txt.split("|") if p.strip()] if txt else []

def _json_try(s):
    if isinstance(s, dict):
        return s
    txt = _s(s)
    if not txt:
        return {}
    try:
        return json.loads(txt)
    except Exception:
        try:
            return json.loads(txt.replace("'", '"'))
        except Exception:
            return {}

# --- Loaders ---
def load_posts_raw() -> pd.DataFrame:
    path = _first_existing(SUBMISSIONS_CANDIDATES)
    if not path:
        abort(404, description="final_data_demoB.* / reddit_data.csv / submissions_cleaned.csv not found")
    return _read_csv_safe(path)

def load_posts() -> pd.DataFrame:
    """
    支持 final_data_demoB:
    tag,text,author,score,comment_count,content,created_time,dimensions,subthemes,subs_sentiment,confidence,subs_evidences,source
    """
    df = load_posts_raw()
    col = {c.lower(): c for c in df.columns}
    def pick(*names):
        for n in names:
            if n in df.columns: return df[n]
            if n.lower() in col: return df[col[n.lower()]]
        return pd.Series(dtype=object)

    out = pd.DataFrame({
        "tag": _str_series(pick("tag")),
        "title": _str_series(pick("text", "title")),
        "author": _str_series(pick("author")),
        "content": _str_series(pick("content", "selftext")),
        "score": pd.to_numeric(pick("score", "ups", "likes"), errors="coerce").fillna(0).astype(int),
        "comment_count_file": pd.to_numeric(pick("comment_count", "num_comments"), errors="coerce"),
        "time_raw": _str_series(pick("created_time", "time", "created_utc")),
        "time": _to_ymd(_str_series(pick("created_time", "time", "created_utc"))),
        "source": _str_series(pick("source", "domain", "subreddit")),
        "dimensions_raw": _str_series(pick("dimensions", "initial dimensions", "initial_dimensions")),
        "subthemes_raw": _str_series(pick("subthemes")),
        "subs_sentiment_raw": pick("subs_sentiment"),
    })

    # 生成稳定 id：Forum 用 tag；Article 用 (title|time|source) 的 md5
    def make_id(row):
        tag = _s(row.get("tag"))
        if tag:
            return tag
        base = f"{_s(row.get('title'))}|{_s(row.get('time'))}|{_s(row.get('source'))}"
        return "art-" + hashlib.md5(base.encode("utf-8", "ignore")).hexdigest()[:16]

    out["id"] = out.apply(make_id, axis=1)
    out["dimensions"] = out["dimensions_raw"].map(_split_pipes)
    out["subthemes"] = out["subthemes_raw"].map(_split_pipes)
    out["subs_sentiment"] = out["subs_sentiment_raw"].map(_json_try)
    out["type"] = out["source"].str.contains("reddit", case=False, na=False).map({True: "forum", False: "article"})
    out["is_post"] = out["type"].eq("forum")

    try:
        t = pd.to_datetime(out["time_raw"], errors="coerce", utc=False, format="mixed")
        out = out.assign(_t=t).sort_values("_t", ascending=False).drop(columns=["_t"])
    except Exception:
        pass

    return out.drop(columns=["time_raw", "dimensions_raw", "subthemes_raw", "subs_sentiment_raw"])

def load_comments() -> pd.DataFrame:
    """
    comments_cleaned.csv:
    "ID","Comment_ID","Tag","Author","Content","Score","Time","Depth","Parent_ID"
    Depth：0=一级，1=二级
    """
    df = _read_csv_safe(COMMENTS_CSV)
    need = ["Tag","Author","Content","Score","Time","Depth","Parent_ID","Comment_ID"]
    miss = [c for c in need if c not in df.columns]
    if miss:
        raise RuntimeError(f"comments_cleaned.csv miss: {miss}")
    out = pd.DataFrame({
        "tag": _str_series(df["Tag"]),
        "author": _str_series(df["Author"]),
        "content": _str_series(df["Content"]),
        "score": pd.to_numeric(df["Score"], errors="coerce").fillna(0).astype(int),
        "time_raw": _str_series(df["Time"]),
        "time": _to_ymd(_str_series(df["Time"])),
        "depth": pd.to_numeric(df["Depth"], errors="coerce").fillna(0).astype(int),
        "parent_id": _str_series(df["Parent_ID"]),
        "parent_id_norm": _str_series(df["Parent_ID"]).map(_normalize_parent_id),
        "comment_id": _str_series(df["Comment_ID"]),
    })
    return out

# --- Auth helpers (原样保留) ---
def _load_users():
    users = {}
    if USERS_CSV.exists():
        df = pd.read_csv(USERS_CSV)
        for _, r in df.iterrows():
            email = str(r.get("email", "")).strip().lower()
            if not email:
                continue
            users[email] = {
                "email": email,
                "name": str(r.get("name", "")).strip() or email.split("@")[0],
                "role": str(r.get("role", "")).strip() or "user",
                "password_hash": (str(r.get("password_hash", "")).strip() or None),
                "password": (str(r.get("password", "")).strip() or None),
            }
        return users
    users["admin@example.com"] = {
        "email": "admin@example.com",
        "name": "Admin",
        "role": "admin",
        "password_hash": generate_password_hash("admin123"),
        "password": None,
    }
    return users

def _verify_password(user_row, plain_password: str) -> bool:
    if user_row.get("password_hash"):
        try:
            return check_password_hash(user_row["password_hash"], plain_password)
        except Exception:
            return False
    if user_row.get("password") is not None:
        return user_row["password"] == plain_password
    return False

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return jsonify({"message": "Unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper

def _is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email))

# --- Health ---
@app.get("/health")
def health():
    return jsonify({"ok": True})

# ===================== Posts APIs =====================

@app.get("/api/posts")
def api_posts():
    posts = load_posts()
    comments = load_comments()

    # Forum 才统计评论数
    if posts["comment_count_file"].isna().all():
        cmt_map = comments.groupby("tag")["comment_id"].count().to_dict()
        posts = posts.assign(
            comment_count=posts.apply(
                lambda r: int(cmt_map.get(r["tag"], 0)) if r["type"] == "forum" else 0, axis=1
            )
        )
    else:
        posts = posts.assign(
            comment_count=posts.apply(
                lambda r: int(r["comment_count_file"] or 0) if r["type"] == "forum" else 0, axis=1
            )
        )

    q = (request.args.get("q") or "").strip().lower()
    if q:
        posts = posts[
            posts["title"].str.lower().str.contains(q, na=False)
            | posts["content"].str.lower().str.contains(q, na=False)
            | posts["author"].str.lower().str.contains(q, na=False)
            | posts["source"].str.lower().str.contains(q, na=False)
            | posts["dimensions"].apply(lambda arr: any(q in d.lower() for d in (arr or [])))
        ]

    try:
        page = max(1, int(request.args.get("page", 1)))
        size = min(100, max(1, int(request.args.get("size", 10))))
    except Exception:
        page, size = 1, 10

    start, end = (page - 1) * size, (page - 1) * size + size
    page_df = posts.iloc[start:end].copy()

    items = [{
        "id": _s(r["id"]),
        "tag": _s(r["tag"]),
        "title": _s(r["title"]),
        "author": _s(r["author"]),
        "time": _s(r["time"]),
        "score": int(r["score"]),
        "comment_count": int(r["comment_count"]),
        "is_post": bool(r["type"] == "forum"),
        "type": _s(r["type"]),
        "source": _s(r["source"]),
        "dimensions": list(r["dimensions"] or []),
    } for _, r in page_df.iterrows()]

    return jsonify({"total": int(len(posts)), "page": page, "size": size, "items": items})

@app.get("/api/posts/<post_id>")
def api_post_detail(post_id: str):
    posts = load_posts()
    row = posts[(posts["id"] == str(post_id)) | (posts["tag"] == str(post_id))].head(1)
    if row.empty:
        abort(404, description=f"post {post_id} not found")
    r = row.iloc[0]
    data = {
        "id": _s(r["id"]),
        "tag": _s(r["tag"]),
        "title": _s(r["title"]),
        "content": _s(r["content"]),
        "author": _s(r["author"]),
        "time": _s(r["time"]),
        "score": int(r["score"]),
        "source": _s(r["source"]),
        "type": _s(r["type"]),
        "is_post": bool(r["type"] == "forum"),
        "dimensions": list(r["dimensions"] or []),
        "subthemes": list(r["subthemes"] or []),
        "subs_sentiment": r["subs_sentiment"] if isinstance(r["subs_sentiment"], dict) else {},
    }
    return jsonify(data)

@app.get("/api/posts/<post_id>/comments")
def api_post_comments(post_id: str):
    posts = load_posts()
    row = posts[(posts["id"] == str(post_id)) | (posts["tag"] == str(post_id))].head(1)
    if row.empty:
        abort(404, description=f"post {post_id} not found")
    r = row.iloc[0]

    if str(r["type"]) != "forum":
        return jsonify({"total": 0, "page": 1, "size": 100, "items": []})

    tag = r["tag"]
    cdf = load_comments()
    df = cdf[cdf["tag"] == tag].copy()

    # 0=一级；1=二级
    df["level"] = df["depth"].apply(lambda d: 1 if int(d) == 0 else 2)

    try:
        t = pd.to_datetime(df["time"], errors="coerce", utc=False, format="mixed")
        df = df.assign(_t=t)
    except Exception:
        df = df.assign(_t=pd.NaT)

    # 父评论分页，子评论跟随父评论一起返回
    parents = df[df["level"] == 1].sort_values(by=["score", "_t"], ascending=[False, False])
    total_parents = int(len(parents))

    try:
        page = max(1, int(request.args.get("page", 1)))
        size = min(100, max(1, int(request.args.get("size", 10))))
    except Exception:
        page, size = 1, 10

    start, end = (page - 1) * size, (page - 1) * size + size
    page_parents = parents.iloc[start:end].copy()

    parent_ids = set(page_parents["comment_id"].map(_normalize_parent_id))
    df["comment_id_norm"] = df["comment_id"].map(_normalize_parent_id)
    children = df[(df["level"] == 2) & (df["parent_id_norm"].isin(parent_ids))].copy()

    ordered = []
    pmap = { _normalize_parent_id(r["comment_id"]): r for _, r in page_parents.iterrows() }
    grouped = { pid: [] for pid in parent_ids }
    for _, cr in children.iterrows():
        grouped.setdefault(cr["parent_id_norm"], []).append(cr)

    for pid, pr in pmap.items():
        ordered.append(pr)
        for cr in grouped.get(pid, []):
            ordered.append(cr)

    items = [{
        "comment_id": _s(r["comment_id"]),
        "comment_id_norm": _s(r.get("comment_id_norm", _normalize_parent_id(r["comment_id"]))),
        "author": _s(r["author"]),
        "content": _s(r["content"]),
        "score": int(r["score"]),
        "time": _s(r["time"]),
        "depth": int(r["depth"]),
        "level": int(r["level"]),
        "parent_id": _s(r["parent_id"]),
        "parent_comment_id_norm": _s(r["parent_id_norm"]),
    } for _, r in pd.DataFrame(ordered).iterrows()]

    return jsonify({"total": total_parents, "page": page, "size": size, "items": items})

# ===================== Auth APIs (原样保留) =====================

@app.post("/api/login")
def api_login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", "")).strip()
    remember = bool(data.get("remember", False))
    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400
    users = _load_users()
    user_row = users.get(email)
    if not user_row or not _verify_password(user_row, password):
        return jsonify({"message": "Invalid credentials"}), 401
    session["user"] = {"email": user_row["email"], "name": user_row["name"], "role": user_row["role"]}
    session.permanent = bool(remember)
    return jsonify({"message": "Login success", "user": session["user"]}), 200

@app.post("/api/logout")
def api_logout():
    session.pop("user", None)
    return jsonify({"message": "Logged out"}), 200

@app.get("/api/me")
def api_me():
    user = session.get("user")
    if not user:
        return jsonify({"message": "Unauthorized"}), 401
    return jsonify({"user": user}), 200

@app.post("/api/register")
def api_register():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", "")).strip()
    name = (str(data.get("name", "")).strip() or email.split("@")[0])
    role = (str(data.get("role", "")).strip() or "user")
    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400
    if not _is_valid_email(email):
        return jsonify({"message": "Invalid email format"}), 400
    if len(password) < 6:
        return jsonify({"message": "Password must be at least 6 characters"}), 400
    users = _load_users()
    if email in users:
        return jsonify({"message": "Email already registered"}), 409
    USERS_DIR.mkdir(parents=True, exist_ok=True)
    password_hash = generate_password_hash(password)
    row = {"email": email, "password_hash": password_hash, "name": name, "role": role}
    import csv
    file_exists = USERS_CSV.exists()
    with open(USERS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["email", "password_hash", "name", "role"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    session["user"] = {"email": email, "name": name, "role": role}
    return jsonify({"message": "Register success", "user": session["user"]}), 201

# --- Entrypoint ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

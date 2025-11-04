import os
import re
import json
import hashlib
import sqlite3
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

DB_DIR = ROOT_DIR / "data" / "database"
NEWS_DB = DB_DIR / "news_data.db"
REDDIT_DB = DB_DIR / "reddit_data.db"

SBI_CSV = ROOT_DIR / "data" / "raw" / "reddit" / "SBI_month.csv"

USERS_DIR = ROOT_DIR / "data" / "user"
USERS_CSV = USERS_DIR / "user.csv"

# --- Utils ---
def _read_sql(db_path: Path, sql: str, params: tuple | list = ()):
    if not db_path.exists():
        abort(404, description=f"DB not found: {db_path}")
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        return pd.read_sql_query(sql, conn, params=params)

def _s(v):
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return ""
    except Exception:
        pass
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none", "null") else s

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

def _normalize_parent_id(pid: str) -> str:
    if not pid:
        return ""
    if "_" in pid:
        return pid.split("_", 1)[1]
    return pid

def _to_ymd_series(s: pd.Series) -> pd.Series:
    ts = pd.to_datetime(s, errors="coerce", utc=False, format="mixed")
    out = ts.dt.strftime("%Y-%m-%d")
    return out.where(~ts.isna(), s.astype(str))

# --- Loaders (DB) ---
def load_posts() -> pd.DataFrame:
    """
    从 news_data.db 的 news 表读取：
    tag,text,author,score,comment_count,content,created_time,dimensions,subthemes,subs_sentiment,confidence,subs_evidences,source
    """
    sql = """
        SELECT tag, text, author, score, comment_count, content, created_time,
               dimensions, subthemes, subs_sentiment, confidence, subs_evidences, source
        FROM news
        ORDER BY created_time DESC
    """
    df = _read_sql(NEWS_DB, sql)


    out = pd.DataFrame({
        "tag": df["tag"].astype(str),
        "title": df["text"].astype(str),
        "author": df["author"].astype(str),
        "content": df["content"].astype(str),
        "score": pd.to_numeric(df["score"], errors="coerce").fillna(0).astype(int),
        "comment_count_file": pd.to_numeric(df["comment_count"], errors="coerce"),
        "time_raw": df["created_time"].astype(str),
        "time": _to_ymd_series(df["created_time"].astype(str)),
        "source": df.get("source", pd.Series(dtype=object)).astype(str),
        "dimensions_raw": df.get("dimensions", pd.Series(dtype=object)).astype(str),
        "subthemes_raw": df.get("subthemes", pd.Series(dtype=object)).astype(str),
        "subs_sentiment_raw": df.get("subs_sentiment", pd.Series(dtype=object)),
    })


    def make_id(row):
        tag = _s(row.get("tag"))
        if tag and tag.lower() != "nan":
            return tag
        base = f"{_s(row.get('title'))}|{_s(row.get('time'))}|{_s(row.get('source'))}"
        return "art-" + hashlib.md5(base.encode("utf-8", "ignore")).hexdigest()[:16]

    out["id"] = out.apply(make_id, axis=1)

    out["type"] = out["tag"].map(lambda t: "forum" if _s(t) else "article")
    out["is_post"] = out["type"].eq("forum")

    out["dimensions"] = out["dimensions_raw"].map(_split_pipes)
    out["subthemes"] = out["subthemes_raw"].map(_split_pipes)
    out["subs_sentiment"] = out["subs_sentiment_raw"].map(_json_try)


    try:
        t = pd.to_datetime(out["time_raw"], errors="coerce", utc=False, format="mixed")
        out = out.assign(_t=t).sort_values("_t", ascending=False).drop(columns=["_t"])
    except Exception:
        pass

    return out.drop(columns=["time_raw", "dimensions_raw", "subthemes_raw", "subs_sentiment_raw"])

def load_comments_by_tag(tag: str) -> pd.DataFrame:
    sql = """
        SELECT ID, Comment_ID, Tag, Author, Content, Score, Time, Depth, Parent_ID
        FROM reddit
        WHERE Tag = ?
        ORDER BY Time ASC
    """
    df = _read_sql(REDDIT_DB, sql, (tag,))

    out = pd.DataFrame({
        "tag": df["Tag"].astype(str),
        "author": df["Author"].astype(str),
        "content": df["Content"].astype(str),
        "score": pd.to_numeric(df["Score"], errors="coerce").fillna(0).astype(int),
        "time_raw": df["Time"].astype(str),
        "time": _to_ymd_series(df["Time"].astype(str)),
        "depth": pd.to_numeric(df["Depth"], errors="coerce").fillna(0).astype(int),
        "parent_id": df["Parent_ID"].astype(str),
        "parent_id_norm": df["Parent_ID"].astype(str).map(_normalize_parent_id),
        "comment_id": df["Comment_ID"].astype(str),
    })
    return out

def _read_csv_safe(path: Path) -> pd.DataFrame:
    if not path or not path.exists():
        abort(404, description=f"{path} not found")
    tried = []
    for enc in [None, "utf-8", "utf-8-sig", "gb18030", "gbk", "latin1"]:
        try:
            return pd.read_csv(path, sep=None, engine="python", encoding=enc, on_bad_lines="skip")
        except Exception as e:
            tried.append(f"{enc or 'default'}: {e}")
    abort(500, description=f"Failed to read {path.name}. Tried -> " + " | ".join(tried))

def load_sbi_table() -> pd.DataFrame:
    if not SBI_CSV.exists():

        return pd.DataFrame(columns=["year", "month", "sbi"])

    df = _read_csv_safe(SBI_CSV)
    cols = {c.lower(): c for c in df.columns}

    def pick(*names):
        for n in names:
            if n in df.columns:
                return df[n]
            if n.lower() in cols:
                return df[cols[n.lower()]]
        return pd.Series(dtype=object)


    month_str = pick("Month")
    if month_str.size and month_str.notna().any():
        mtxt = month_str.astype(str).str.strip()


        y = mtxt.str.extract(r"(?P<y>\d{4})", expand=True)["y"]
        m = mtxt.str.extract(r"\d{4}[-/\.](?P<m>\d{1,2})", expand=True)["m"]

        yy = pd.to_numeric(y, errors="coerce").astype("Int64")
        mm = pd.to_numeric(m, errors="coerce").astype("Int64")
        sbi = pd.to_numeric(pick("SBI", "sbi", "value", "index", "score"), errors="coerce")

        out = pd.DataFrame({"year": yy, "month": mm, "sbi": sbi}).dropna(subset=["year", "month"])
        out["year"] = out["year"].astype(int)
        out["month"] = out["month"].astype(int)
        return out


    yy = pd.to_numeric(pick("Year"), errors="coerce").astype("Int64")
    mm = pd.to_numeric(pick("Month", "Mon"), errors="coerce").astype("Int64")
    sbi = pd.to_numeric(pick("SBI", "sbi", "value", "index", "score"), errors="coerce")

    out = pd.DataFrame({"year": yy, "month": mm, "sbi": sbi}).dropna(subset=["year", "month"])
    if not out.empty:
        out["year"] = out["year"].astype(int)
        out["month"] = out["month"].astype(int)
    return out

def load_sbi_info(year: int, month: int | None):
    t = load_sbi_table()  # year, month, sbi

    yy = t[t["year"] == int(year)].copy()
    months_with_data = sorted(yy["month"].unique().tolist())

    cur_sbi = 0.0
    delta = 0.0

    if month and (month in months_with_data):

        cur_row = yy[yy["month"] == int(month)].tail(1)
        if not cur_row.empty and pd.notna(cur_row["sbi"].iloc[0]):
            cur_sbi = float(cur_row["sbi"].iloc[0])


        prev_candidates = [mm for mm in months_with_data if mm < int(month)]
        if prev_candidates:
            prev_m = max(prev_candidates)
            prev_row = yy[yy["month"] == prev_m].tail(1)
            if not prev_row.empty and pd.notna(prev_row["sbi"].iloc[0]):
                delta = float(cur_sbi - float(prev_row["sbi"].iloc[0]))

    # [-100, 100]
    cur_sbi = max(-100.0, min(100.0, float(cur_sbi)))
    delta = max(-200.0, min(200.0, float(delta)))

    return {"year": int(year), "months_with_data": months_with_data, "sbi": cur_sbi, "delta": delta}

# --- Auth helpers ---
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

# ===================== APIs =====================

@app.get("/api/sbi")
def api_sbi():
    year = request.args.get("year", type=int)
    if not year:
        return jsonify({"code": 400, "message": "year is required"}), 400
    month = request.args.get("month", type=int)
    info = load_sbi_info(year, month)
    return jsonify(info)

@app.get("/api/sbi/years")
def api_sbi_years():
    t = load_sbi_table()
    years = sorted(t["year"].unique().tolist())
    return jsonify({"years": years})

@app.get("/api/posts")
def api_posts():
    posts = load_posts()


    if posts["comment_count_file"].isna().all():

        forum_tags = posts[posts["type"] == "forum"]["tag"].tolist()
        if forum_tags:
            placeholders = ",".join(["?"] * len(forum_tags))
            sql = f"SELECT Tag, COUNT(1) AS cnt FROM reddit WHERE Tag IN ({placeholders}) GROUP BY Tag"
            cdf = _read_sql(REDDIT_DB, sql, tuple(forum_tags))
            cmt_map = dict(zip(cdf["Tag"].astype(str), cdf["cnt"].astype(int)))
        else:
            cmt_map = {}
        posts = posts.assign(
            comment_count=posts.apply(
                lambda r: int(cmt_map.get(str(r["tag"]), 0)) if r["type"] == "forum" else 0, axis=1
            )
        )
    else:
        posts = posts.assign(
            comment_count=posts.apply(
                lambda r: int(r["comment_count_file"] or 0) if r["type"] == "forum" else 0, axis=1
            )
        )


    y = request.args.get("year", type=int)
    m = request.args.get("month", type=int)
    if y or m:
        tt = pd.to_datetime(posts["time"], errors="coerce", utc=False, format="mixed")
        posts = posts.assign(_y=tt.dt.year, _m=tt.dt.month)
        if y:
            posts = posts[posts["_y"] == y]
        if m:
            posts = posts[posts["_m"] == m]

    # 关键字
    q = (request.args.get("q") or "").strip().lower()
    if q:
        posts = posts[
            posts["title"].str.lower().str.contains(q, na=False)
            | posts["content"].str.lower().str.contains(q, na=False)
            | posts["author"].str.lower().str.contains(q, na=False)
            | posts["source"].str.lower().str.contains(q, na=False)
            | posts["dimensions"].apply(lambda arr: any(q in d.lower() for d in (arr or [])))
        ]

    # 分页
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

    tag = _s(r["tag"])
    df = load_comments_by_tag(tag).copy()

    df["level"] = df["depth"].apply(lambda d: 1 if int(d) == 0 else 2)
    try:
        t = pd.to_datetime(df["time"], errors="coerce", utc=False, format="mixed")
        df = df.assign(_t=t)
    except Exception:
        df = df.assign(_t=pd.NaT)

    parents = df[df["level"] == 1].sort_values(by=["score", "_t"], ascending=[False, False])
    total_parents = int(len(parents))

    try:
        page = max(1, int(request.args.get("page", 1)))
        size = min(10000, max(1, int(request.args.get("size", 10))))
    except Exception:
        page, size = 1, 10

    start, end = (page - 1) * size, (page - 1) * size + size
    page_parents = parents.iloc[start:end].copy()

    parent_ids = set(page_parents["comment_id"].map(_normalize_parent_id))
    df["comment_id_norm"] = df["comment_id"].map(_normalize_parent_id)
    children = df[(df["level"] == 2) & (df["parent_id_norm"].isin(parent_ids))].copy()

    ordered = []
    pmap = {_normalize_parent_id(r["comment_id"]): r for _, r in page_parents.iterrows()}
    grouped = {pid: [] for pid in parent_ids}
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

# --- Auth APIs ---
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

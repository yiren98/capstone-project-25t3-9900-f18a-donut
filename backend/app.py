# Launch Flask server and provide API endpoints for frontend data access

import re
from flask import Flask, jsonify, request, abort, session
from flask_cors import CORS
import pandas as pd
from pathlib import Path
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import HTTPException
import os
from functools import wraps
from datetime import timedelta

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


ROOT_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT_DIR / "data" / "raw" / "reddit"

SUBMISSIONS_CANDIDATES = [
    DATA_DIR / "reddit_data.csv",
    DATA_DIR / "submissions_cleaned.csv",
    DATA_DIR / "reddit_data",
]
COMMENTS_CSV = DATA_DIR / "comments_cleaned.csv"

USERS_DIR = ROOT_DIR / "data" / "user"
USERS_CSV = USERS_DIR / "user.csv"


# --- Utils ---
def _first_existing(paths):
    for p in paths:
        if p.exists():
            return p
    return None

def _read_csv_safe(path: Path) -> pd.DataFrame:
    if not path or not path.exists():
        abort(404, description=f"{path} not found")
    try:
        return pd.read_csv(path)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="utf-8-sig", engine="python")

def _str_series(x):
    return x.astype(str).fillna("").str.strip()

def _to_ymd(s: pd.Series) -> pd.Series:

    ts = pd.to_datetime(s, errors="coerce", utc=False, format="mixed")
    out = ts.dt.strftime("%Y-%m-%d")

    out = out.where(~ts.isna(), _str_series(s))
    return out

def _normalize_parent_id(pid: str) -> str:
 
    if not pid:
        return ""
    if "_" in pid:
        return pid.split("_", 1)[1]

    return pid

# --- Loaders ---
def load_posts_raw() -> pd.DataFrame:
    path = _first_existing(SUBMISSIONS_CANDIDATES)
    if not path:
        abort(404, description="reddit_data.csv / submissions_cleaned.csv not found")
    return _read_csv_safe(path)

def load_posts() -> pd.DataFrame:

    df = load_posts_raw()

    col = {c.lower(): c for c in df.columns}
    def pick(*names):
        for n in names:
            if n in df.columns:
                return df[n]
       
            if n.lower() in col:
                return df[col[n.lower()]]
        return pd.Series(dtype=object)

    id_col = pick("ID")  
    tag_col = pick("Tag")
    title_col = pick("Text")
    author_col = pick("Author")
    content_col = pick("Content")
    score_col = pick("Score")
    cmt_cnt_col = pick("Comment_Count")
    time_col = pick("Created_Time", "Time")
    location_col = pick("Location")
    source_col = pick("Source")
    init_dim_col = pick("Initial Dimensions", "Dimensions")

    out = pd.DataFrame({
        "id": _str_series(id_col) if not id_col.empty else _str_series(tag_col),
        "tag": _str_series(tag_col),
        "title": _str_series(title_col),
        "author": _str_series(author_col),
        "content": _str_series(content_col),
        "score": pd.to_numeric(score_col, errors="coerce").fillna(0).astype(int) if not score_col.empty else 0,
        "time_raw": _str_series(time_col),
        "time": _to_ymd(_str_series(time_col)),  
        "location": _str_series(location_col) if not location_col.empty else "",
        "source": _str_series(source_col) if not source_col.empty else "",
        "initial_dimensions": _str_series(init_dim_col) if not init_dim_col.empty else "",
        "comment_count_file": pd.to_numeric(cmt_cnt_col, errors="coerce").fillna(0).astype(int) if not cmt_cnt_col.empty else None,
    })


    try:
        t = pd.to_datetime(out["time_raw"], errors="coerce", utc=False, format="mixed")
        out = out.assign(_t=t).sort_values("_t", ascending=False).drop(columns=["_t"])
    except Exception:
        pass

    return out.drop(columns=["time_raw"])

def load_comments() -> pd.DataFrame:
    """
    comments_cleaned.csv:
    "ID","Comment_ID","Tag","Author","Content","Score","Time","Depth","Parent_ID"
    """
    df = _read_csv_safe(COMMENTS_CSV)

    need = ["Tag", "Author", "Content", "Score", "Time", "Depth", "Parent_ID", "Comment_ID"]
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

# ===================== Posts APIs =====================

@app.get("/api/posts")
def api_posts():
    """
    GET /api/posts?page=1&size=10&q=keyword&tag=xxx
    -> { total, page, size, items: [{ id, tag, title, author, time, score, comment_count }] }
    """
    posts = load_posts()
    comments = load_comments()


    if posts["comment_count_file"].isna().all():
        comment_counts = comments.groupby("tag")["comment_id"].count().to_dict()
        posts = posts.assign(comment_count=posts["tag"].map(comment_counts).fillna(0).astype(int))
    else:
        posts = posts.assign(comment_count=posts["comment_count_file"].fillna(0).astype(int))

    q = (request.args.get("q") or "").strip().lower()
    if q:
        mask = (
            posts["title"].str.lower().str.contains(q, na=False) |
            posts["content"].str.lower().str.contains(q, na=False) |
            posts["author"].str.lower().str.contains(q, na=False) |
            posts["location"].str.lower().str.contains(q, na=False) |
            posts["source"].str.lower().str.contains(q, na=False)
        )
        posts = posts[mask]

    tag_eq = (request.args.get("tag") or "").strip()
    if tag_eq:
        posts = posts[posts["tag"] == tag_eq]

    try:
        page = max(1, int(request.args.get("page", 1)))
        size = min(100, max(1, int(request.args.get("size", 10))))
    except Exception:
        page, size = 1, 10

    start, end = (page - 1) * size, (page - 1) * size + size
    page_df = posts.iloc[start:end].copy()

    items = [{
        "id": r["id"],
        "tag": r["tag"],
        "title": r["title"],      
        "author": r["author"],  
        "time": r["time"],          
        "score": int(r["score"]),
        "comment_count": int(r["comment_count"]),
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
        "id": r["id"],
        "tag": r["tag"],
        "title": r["title"],
        "content": r["content"],
        "author": r["author"],
        "time": r["time"],  # YYYY-MM-DD
        "score": int(r["score"]),
        "location": r["location"],
        "source": r["source"],
        "initial_dimensions": r["initial_dimensions"],
    }
    return jsonify(data)

@app.get("/api/posts/<post_id>/comments")
def api_post_comments(post_id: str):

    posts = load_posts()
    row = posts[(posts["id"] == str(post_id)) | (posts["tag"] == str(post_id))].head(1)
    if row.empty:
        abort(404, description=f"post {post_id} not found")
    tag = row.iloc[0]["tag"]

    cdf = load_comments()
    df = cdf[cdf["tag"] == tag].copy()


    df["level"] = df["depth"].apply(lambda d: 1 if d <= 1 else 2)


    try:
        t = pd.to_datetime(df["time"], errors="coerce", utc=False, format="mixed")
        df = df.assign(_t=t).sort_values(by=["level", "score", "_t"], ascending=[True, False, False]).drop(columns=["_t"])
    except Exception:
        df = df.sort_values(by=["level", "score"], ascending=[True, False])

    try:
        page = max(1, int(request.args.get("page", 1)))
        size = min(500, max(1, int(request.args.get("size", 100))))
    except Exception:
        page, size = 1, 100

    start, end = (page - 1) * size, (page - 1) * size + size
    page_df = df.iloc[start:end].copy()

    items = [{
        "comment_id": r["comment_id"],
        "author": r["author"],
        "content": r["content"],
        "score": int(r["score"]),
        "time": r["time"],  # YYYY-MM-DD
        "depth": int(r["depth"]),
        "level": int(r["level"]), 
        "parent_id": r["parent_id"],
        "parent_comment_id_norm": r["parent_id_norm"],  
    } for _, r in page_df.iterrows()]

    return jsonify({"total": int(len(df)), "page": page, "size": size, "items": items})

# ===================== Auth APIs  =====================

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

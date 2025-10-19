# Launch Flask server and provide API endpoints for frontend data access

from flask import Flask, jsonify, request, abort
from flask_cors import CORS
import pandas as pd
from pathlib import Path

app = Flask(__name__)
CORS(app)

# -------- Path Configuration --------
ROOT_DIR = Path(__file__).resolve().parents[1]   # one level above backend/
DATA_DIR = ROOT_DIR / "data"
PROC_DIR = DATA_DIR / "processed"

NEW_DATASET_CSV_1 = PROC_DIR / "new_dataset.csv"
NEW_DATASET_CSV_2 = PROC_DIR / "newdataset.csv"
COMMENTS_CSV = PROC_DIR / "comments.csv"

def _pick_new_dataset_path():
    if NEW_DATASET_CSV_1.exists():
        return NEW_DATASET_CSV_1
    if NEW_DATASET_CSV_2.exists():
        return NEW_DATASET_CSV_2
    abort(404, description="new_dataset.csv / newdataset.csv not found in data/processed/")

ANNOTATED_CSV = PROC_DIR / "annotated.csv"


# -------- Utility (shared) --------
def _to_pipe_list(raw: str):
    """Parse a 'A|B|C' or single string into a cleaned list."""
    if raw is None:
        return []
    s = str(raw).strip()
    if not s:
        return []
    return [x.strip() for x in s.split("|") if x.strip()]


# =========================
# =========================
# def _normalize(df: pd.DataFrame) -> pd.DataFrame:
#     """
#     Normalize key columns and unify schema:
#     - must have sentiment and text
#     - support both 'dimension' and 'dimensions' columns
#     - keep year as string (e.g. '2025-06')
#     """
#     m = {c.lower(): c for c in df.columns}
#
#     if "sentiment" not in m or "text" not in m:
#         abort(500, description="annotated.csv missing required columns: sentiment or text")
#
#     df["sentiment"] = df[m["sentiment"]].fillna("").astype(str).str.lower()
#     df["text"] = df[m["text"]].fillna("").astype(str)
#
#     # optional columns
#     df["id"] = pd.to_numeric(df[m["id"]], errors="coerce") if "id" in m else pd.NA
#     df["region"] = df[m["region"]].fillna("").astype(str) if "region" in m else ""
#     df["year"] = df[m["year"]].fillna("").astype(str) if "year" in m else ""
#     df["source"] = df[m["source"]].fillna("").astype(str) if "source" in m else ""
#
#     # handle dimension/dimensions
#     raw_dim_col = ""
#     if "dimensions" in m:
#         raw_dim_col = m["dimensions"]
#     elif "dimension" in m:
#         raw_dim_col = m["dimension"]
#
#     if raw_dim_col:
#         dims_list = df[raw_dim_col].fillna("").astype(str).apply(_to_pipe_list)
#     else:
#         dims_list = pd.Series([[]] * len(df))
#
#     df["dimensions"] = dims_list
#     df["dimensions_str"] = df["dimensions"].apply(lambda arr: "|".join(arr) if arr else "")
#
#     return df
#
# def load_annotated() -> pd.DataFrame:
#     """Load processed/annotated.csv and normalize it."""
#     if not ANNOTATED_CSV.exists():
#         abort(404, description="annotated.csv not found. Please run the data pipeline first.")
#     df = pd.read_csv(ANNOTATED_CSV)
#     return _normalize(df)
#
# def _filter_by_region_year(df: pd.DataFrame, region: str, year: str) -> pd.DataFrame:
#     """(Old) Filter by region and year (string)."""
#     if region and region.lower() != "all":
#         df = df[df["region"].astype(str).str.lower() == region.lower()]
#     if year and year.lower() != "all":
#         ys = str(year).strip()
#         if len(ys) == 4 and ys.isdigit():
#             df = df[df["year"].astype(str).str.startswith(ys)]
#         else:
#             df = df[df["year"].astype(str) == ys]
#     return df
#
# def _filter_by_dimensions(df: pd.DataFrame, dims_param: str, mode: str) -> pd.DataFrame:
#     """(Old) Filter reviews by dimensions."""
#     if not dims_param:
#         return df
#     wanted = [x.strip() for x in dims_param.split(",") if x.strip()]
#     if not wanted:
#         return df
#     wanted_set = set(wanted)
#     def match(row_dims):
#         s = set(row_dims or [])
#         return s.issuperset(wanted_set) if mode == "all" else bool(s & wanted_set)
#     return df[df["dimensions"].apply(match)]


def load_posts() -> pd.DataFrame:
    """
      - ID
      - Reddit_ID
      - Location
      - Time
      - Title-Content
      - Source
    """
    path = _pick_new_dataset_path()
    df = pd.read_csv(path)

    m = {c.lower(): c for c in df.columns}
    required = ["id", "reddit_id", "location", "time", "title-content", "source"]
    for key in required:
        if key not in m:
            abort(500, description=f"new_dataset missing column: {key}")

    out = pd.DataFrame({
        "id": df[m["id"]],
        "reddit_id": df[m["reddit_id"]].astype(str),
        "location": df[m["location"]].astype(str),
        "time": df[m["time"]].astype(str),
        "title_content": df[m["title-content"]].astype(str),  # Title-Content -> title_content
        "source": df[m["source"]].astype(str),
    })
    return out


def load_comments() -> pd.DataFrame:
    """
      - ID
      - Comment_ID
      - Parent_ID
      - Submission_ID
      - Author
      - Body
      - Score
      - Created_UTC
      - Created_Time
      - Depth
      - Crawled_Time
    """
    if not COMMENTS_CSV.exists():
        abort(404, description="comments.csv not found in data/processed/")
    df = pd.read_csv(COMMENTS_CSV)

    m = {c.lower(): c for c in df.columns}
    required = [
        "id", "comment_id", "parent_id", "submission_id", "author", "body",
        "score", "created_utc", "created_time", "depth", "crawled_time"
    ]
    for key in required:
        if key not in m:
            abort(500, description=f"comments.csv missing column: {key}")

    out = pd.DataFrame({
        "id": df[m["id"]],
        "comment_id": df[m["comment_id"]].astype(str),
        "parent_id": df[m["parent_id"]].astype(str),
        "submission_id": df[m["submission_id"]].astype(str),
        "author": df[m["author"]].astype(str),
        "body": df[m["body"]].astype(str),
        "score": pd.to_numeric(df[m["score"]], errors="coerce").fillna(0).astype(int),
        "created_utc": df[m["created_utc"]].astype(str),
        "created_time": df[m["created_time"]].astype(str),
        "depth": pd.to_numeric(df[m["depth"]], errors="coerce").fillna(0).astype(int),
        "crawled_time": df[m["crawled_time"]].astype(str),
    })
    return out


# -------- Basic Routes --------
@app.get("/health")
def health():
    """Health check endpoint."""
    return jsonify({"ok": True})


@app.get("/api/posts")
def api_posts():
    """
    """
    df = load_posts()

    cdf = load_comments()
    comment_counts = cdf["submission_id"].value_counts()  

    has_comments = (request.args.get("has_comments") or "").lower() in {"1", "true", "yes"}
    if has_comments:
        df = df[df["reddit_id"].isin(comment_counts.index)]

    df = df.assign(comment_count=df["reddit_id"].map(comment_counts).fillna(0).astype(int))

    q = (request.args.get("q") or "").strip().lower()
    if q:
        mask = (
            df["title_content"].str.lower().str.contains(q, na=False) |
            df["location"].str.lower().str.contains(q, na=False) |
            df["source"].str.lower().str.contains(q, na=False)
        )
        df = df[mask]

    try:
        page = max(1, int(request.args.get("page", 1)))
        size = min(100, max(1, int(request.args.get("size", 10))))
    except Exception:
        page, size = 1, 10

    start, end = (page - 1) * size, (page - 1) * size + size
    page_df = df.iloc[start:end].copy()

    def to_item(row):
        return {
            "id": int(row["id"]) if pd.notna(row["id"]) else None,
            "reddit_id": row["reddit_id"],
            "location": row["location"],
            "time": row["time"],
            "title_content": row["title_content"],
            "source": row["source"],
            "comment_count": int(row.get("comment_count", 0)),
        }

    items = [to_item(r) for _, r in page_df.iterrows()]
    return jsonify({
        "total": int(len(df)),
        "page": page,
        "size": size,
        "items": items
    })


@app.get("/api/posts/<reddit_id>/comments")
def api_post_comments(reddit_id: str):
    """
    """
    posts = load_posts()
    if not (posts["reddit_id"] == str(reddit_id)).any():
        abort(404, description=f"reddit_id {reddit_id} not found in posts.")

    cdf = load_comments()
    df = cdf[cdf["submission_id"] == str(reddit_id)].copy()

    df = df.sort_values(by=["depth", "score"], ascending=[True, False])

    try:
        page = max(1, int(request.args.get("page", 1)))
        size = min(200, max(1, int(request.args.get("size", 50))))
    except Exception:
        page, size = 1, 50

    start, end = (page - 1) * size, (page - 1) * size + size
    page_df = df.iloc[start:end].copy()

    def to_item(row):
        return {
            "comment_id": row["comment_id"],
            "parent_id": row["parent_id"],
            "author": row["author"],
            "body": row["body"],
            "score": int(row["score"]),
            "created_time": row["created_time"],
            "depth": int(row["depth"]),
        }

    items = [to_item(r) for _, r in page_df.iterrows()]
    return jsonify({
        "total": int(len(df)),
        "page": page,
        "size": size,
        "items": items
    })


# =========================
# =========================
# @app.get("/api/years")
# def api_years():
#     df = load_annotated()
#     ser = df["year"].astype(str).str.strip()
#     ser = ser[(ser != "") & (ser.str.lower() != "all")]
#     norm = ser.where(ser.str.contains(r"^\d{4}-\d{2}$"), ser + "-01")
#     parsed = pd.to_datetime(norm, errors="coerce", format="mixed")
#     tmp = pd.DataFrame({"val": ser, "parsed": parsed})
#     tmp = tmp.dropna(subset=["parsed"]).drop_duplicates(subset=["val"]).
#         sort_values("parsed", ascending=False)
#     years = ["All"] + tmp["val"].tolist()
#     return jsonify({"years": years})
#
# @app.get("/api/reviews")
# def api_reviews():
#     df = load_annotated()
#     sentiment = (request.args.get("sentiment") or "all").lower()
#     dims_param = (request.args.get("dimensions") or "").strip()
#     mode = (request.args.get("mode") or "any").lower()
#     if mode not in {"any", "all"}:
#         mode = "any"
#     region = request.args.get("region") or "All"
#     year = request.args.get("year") or "All"
#     df = _filter_by_dimensions(df, dims_param, mode)
#     df = _filter_by_region_year(df, region, year)
#     if sentiment in {"positive", "negative", "neutral"}:
#         df = df[df["sentiment"] == sentiment]
#     try:
#         page = max(1, int(request.args.get("page", 1)))
#         size = min(100, max(1, int(request.args.get("size", 10))))
#     except Exception:
#         page, size = 1, 10
#     start, end = (page - 1) * size, (page - 1) * size + size
#     page_df = df.iloc[start:end].copy()
#     def to_item(row):
#         return {
#             "id": int(row["id"]) if pd.notna(row["id"]) else None,
#             "text": row["text"],
#             "sentiment": row["sentiment"],
#             "dimensions": list(row["dimensions"]) if isinstance(row["dimensions"], list) else [],
#             "dimensions_str": row.get("dimensions_str", ""),
#             "source": row.get("source", ""),
#             "region": row.get("region", ""),
#             "year": row.get("year", ""),
#         }
#     items = [to_item(r) for _, r in page_df.iterrows()]
#     return jsonify({"total": int(len(df)), "page": page, "size": size, "items": items})
#
# @app.get("/api/kpis")
# def api_kpis():
#     df = load_annotated()
#     dims_param = (request.args.get("dimensions") or "").strip()
#     mode = (request.args.get("mode") or "any").lower()
#     if mode not in {"any", "all"}:
#         mode = "any"
#     region = request.args.get("region") or "All"
#     year = request.args.get("year") or "All"
#     df = _filter_by_dimensions(df, dims_param, mode)
#     df = _filter_by_region_year(df, region, year)
#     total = int(len(df))
#     pos = int((df["sentiment"] == "positive").sum())
#     neg = int((df["sentiment"] == "negative").sum())
#     return jsonify({"total": total, "positive_count": pos, "negative_count": neg})


if __name__ == "__main__":
    # Use 0.0.0.0 for Docker or LAN access; for local testing visit http://localhost:5000
    app.run(host="0.0.0.0", port=5000, debug=True)

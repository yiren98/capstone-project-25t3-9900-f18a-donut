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
ANNOTATED_CSV = PROC_DIR / "annotated.csv"


# -------- Utility Functions --------
def _to_pipe_list(raw: str):
    """Parse a 'A|B|C' or single string into a cleaned list."""
    if raw is None:
        return []
    s = str(raw).strip()
    if not s:
        return []
    return [x.strip() for x in s.split("|") if x.strip()]


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize key columns and unify schema:
    - must have sentiment and text
    - support both 'dimension' and 'dimensions' columns
    - keep year as string (e.g. '2025-06')
    """
    m = {c.lower(): c for c in df.columns}

    if "sentiment" not in m or "text" not in m:
        abort(500, description="annotated.csv missing required columns: sentiment or text")

    df["sentiment"] = df[m["sentiment"]].fillna("").astype(str).str.lower()
    df["text"] = df[m["text"]].fillna("").astype(str)

    # optional columns
    df["id"] = pd.to_numeric(df[m["id"]], errors="coerce") if "id" in m else pd.NA
    df["region"] = df[m["region"]].fillna("").astype(str) if "region" in m else ""
    df["year"] = df[m["year"]].fillna("").astype(str) if "year" in m else ""
    df["source"] = df[m["source"]].fillna("").astype(str) if "source" in m else ""

    # handle dimension/dimensions
    raw_dim_col = ""
    if "dimensions" in m:
        raw_dim_col = m["dimensions"]
    elif "dimension" in m:
        raw_dim_col = m["dimension"]

    if raw_dim_col:
        dims_list = df[raw_dim_col].fillna("").astype(str).apply(_to_pipe_list)
    else:
        dims_list = pd.Series([[]] * len(df))

    df["dimensions"] = dims_list
    df["dimensions_str"] = df["dimensions"].apply(lambda arr: "|".join(arr) if arr else "")

    return df


def load_annotated() -> pd.DataFrame:
    """Load processed/annotated.csv and normalize it."""
    if not ANNOTATED_CSV.exists():
        abort(404, description="annotated.csv not found. Please run the data pipeline first.")
    df = pd.read_csv(ANNOTATED_CSV)
    return _normalize(df)


def _filter_by_dimensions(df: pd.DataFrame, dims_param: str, mode: str) -> pd.DataFrame:
    """
    Filter reviews by dimensions.
    dims_param: comma-separated list like "Collaboration,Leadership"
    mode: 'any' (OR) or 'all' (AND)
    """
    if not dims_param:
        return df
    wanted = [x.strip() for x in dims_param.split(",") if x.strip()]
    if not wanted:
        return df

    wanted_set = set(wanted)

    def match(row_dims):
        s = set(row_dims or [])
        return s.issuperset(wanted_set) if mode == "all" else bool(s & wanted_set)

    return df[df["dimensions"].apply(match)]


# -------- Basic Routes --------
@app.get("/health")
def health():
    """Health check endpoint."""
    return jsonify({"ok": True})


# -------- Business Routes --------
@app.get("/api/reviews")
def api_reviews():
    """
    Get review list with support for sentiment and multi-dimension filters.
    Query params:
      sentiment = all | positive | negative | neutral
      dimensions = comma-separated list (e.g. Collaboration,Recognition)
      mode = any | all (default any)
      page, size = pagination (default 1,10)
    """
    df = load_annotated()

    sentiment = (request.args.get("sentiment") or "all").lower()
    dims_param = (request.args.get("dimensions") or "").strip()
    mode = (request.args.get("mode") or "any").lower()
    if mode not in {"any", "all"}:
        mode = "any"

    df = _filter_by_dimensions(df, dims_param, mode)

    if sentiment in {"positive", "negative", "neutral"}:
        df = df[df["sentiment"] == sentiment]

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
            "text": row["text"],
            "sentiment": row["sentiment"],
            "dimensions": list(row["dimensions"]) if isinstance(row["dimensions"], list) else [],
            "dimensions_str": row.get("dimensions_str", ""),
            "source": row.get("source", ""),
            "region": row.get("region", ""),
            "year": row.get("year", ""),
        }

    items = [to_item(r) for _, r in page_df.iterrows()]
    return jsonify({
        "total": int(len(df)),
        "page": page,
        "size": size,
        "items": items
    })


@app.get("/api/kpis")
def api_kpis():
    """
    Return KPI counts.
    Optional query params:
      dimensions = comma-separated list
      mode = any | all
    Response:
      total, positive_count, negative_count
    """
    df = load_annotated()

    dims_param = (request.args.get("dimensions") or "").strip()
    mode = (request.args.get("mode") or "any").lower()
    if mode not in {"any", "all"}:
        mode = "any"

    df = _filter_by_dimensions(df, dims_param, mode)

    total = int(len(df))
    pos = int((df["sentiment"] == "positive").sum())
    neg = int((df["sentiment"] == "negative").sum())

    return jsonify({
        "total": total,
        "positive_count": pos,
        "negative_count": neg
    })


if __name__ == "__main__":
    # Use 0.0.0.0 for Docker or LAN access; for local testing visit http://localhost:5000
    app.run(host="0.0.0.0", port=5000, debug=True)

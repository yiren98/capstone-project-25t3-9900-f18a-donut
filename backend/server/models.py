import csv
import hashlib
import json
import re
import pandas as pd
from functools import lru_cache
from pathlib import Path
from flask import abort
from werkzeug.security import check_password_hash, generate_password_hash

from config import (
    NEWS_DB, REDDIT_DB, USERS_CSV, USERS_DIR,
    SBI_CSV, DIM_CSV, MAP_CSV,
    SUGG_DIR, SR_OVERALL, SR_DIM_DIR, SR_SUB_DIR, SR_MAP_CSV
)
from utils import (
    _s, _split_pipes, _json_try, _to_ymd_series, _normalize_parent_id,
    _read_sql, _read_csv_safe
)

# ---------- JSON readers (cached) ----------
@lru_cache(maxsize=256)
def _read_json_file(p: Path):
    if not p.exists():
        print("!! JSON not found:", p)
        return None
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

# ---------- Mapping for suggestions / subthemes ----------
@lru_cache(maxsize=1)
def _load_mapping():
    """
    Build:
      by_dim: { dimName: [{name, file}, ...] }
      file_of_sub: { subthemeName: mapped_file }
      dims_of_sub: { subthemeName: [dims...] }
    """
    by_dim, file_of_sub, dims_of_sub = {}, {}, {}

    print(">> SUGG_DIR:", SUGG_DIR)
    print(">> MAP CSV:", SR_MAP_CSV, SR_MAP_CSV.exists())

    if not SR_MAP_CSV.exists():
        return {"by_dim": by_dim, "file_of_sub": file_of_sub, "dims_of_sub": dims_of_sub}

    with SR_MAP_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        norm = lambda k: (k or "").strip().lower()
        COL_SUB  = next((c for c in reader.fieldnames if norm(c) in {"subthemes","subtheme","子主题"}), None)
        COL_DIM  = next((c for c in reader.fieldnames if norm(c) in {"mapped_dimension","dimension","dimensions"}), None)
        COL_FILE = next((c for c in reader.fieldnames if norm(c) in {"mapped_file","file","filename"}), None)

        for row in reader:
            sub  = (row.get(COL_SUB)  or "").strip()
            dims = (row.get(COL_DIM)  or "").strip()
            fil  = (row.get(COL_FILE) or "").strip()
            if not sub:
                continue
            file_of_sub[sub] = fil or file_of_sub.get(sub, "")
            dim_list = [d.strip() for d in re.split(r"[;|,]", dims) if d.strip()]
            dims_of_sub[sub] = dim_list or dims_of_sub.get(sub, [])
            for d in dim_list:
                by_dim.setdefault(d, []).append({"name": sub, "file": fil})
    return {"by_dim": by_dim, "file_of_sub": file_of_sub, "dims_of_sub": dims_of_sub}

def _read_mapping_exploded(primary_csv: Path, fallback_csv: Path | None = None) -> pd.DataFrame:
    """
    Read subtheme-dimension mapping and explode cells like 'A; B; C' to multiple rows.
    Returns DataFrame with ['subtheme', 'dimension'].
    """
    path = None
    if isinstance(primary_csv, Path) and primary_csv.exists():
        path = primary_csv
    elif fallback_csv and isinstance(fallback_csv, Path) and fallback_csv.exists():
        path = fallback_csv
    else:
        abort(404, description=f"mapping csv not found: {primary_csv} / {fallback_csv}")

    df_raw = _read_csv_safe(path)
    cols = {c.lower(): c for c in df_raw.columns}

    sub_col = cols.get("subthemes") or cols.get("subtheme") or cols.get("sub_topic") or cols.get("sub") \
              or cols.get("子主题")
    dim_col = cols.get("mapped_dimension") or cols.get("dimension") or cols.get("dimensions") or cols.get("dim")

    if not sub_col or not dim_col:
        abort(500, description="mapping csv missing required columns (subtheme/mapped_dimension)")

    out_rows = []
    for _, row in df_raw.iterrows():
        sub = str(row.get(sub_col, "")).strip()
        if not sub:
            continue
        dims_txt = str(row.get(dim_col, "")).strip()
        if not dims_txt:
            continue
        dims = [d.strip() for d in re.split(r"[;|,]", dims_txt) if d and d.strip()]
        for d in dims:
            out_rows.append({"subtheme": sub, "dimension": d})

    if not out_rows:
        return pd.DataFrame(columns=["subtheme", "dimension"])
    return pd.DataFrame(out_rows)

# ---------- Posts / Comments loaders ----------
def load_posts() -> pd.DataFrame:
    sql = """
        SELECT tag, text, author, score, comment_count, content, created_time,
               dimensions, subthemes, subs_sentiment, source
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

# ---------- SBI loaders ----------
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

    cur_sbi = max(-100.0, min(100.0, float(cur_sbi)))
    delta = max(-200.0, min(200.0, float(delta)))

    return {"year": int(year), "months_with_data": months_with_data, "sbi": cur_sbi, "delta": delta}

# ---------- Users ----------
def _load_users():
    users = {}
    if USERS_CSV.exists():
        df = _read_csv_safe(USERS_CSV)
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

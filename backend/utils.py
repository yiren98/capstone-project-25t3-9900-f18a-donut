import json
import re
import sqlite3
from functools import lru_cache
from pathlib import Path
import pandas as pd
from flask import abort
from werkzeug.security import check_password_hash, generate_password_hash

# ---------- Generic helpers ----------
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

def _slugify(name: str) -> str:
    return re.sub(r"[\s\-]+", "_", name.strip().lower())

def _is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email))

# ---------- IO helpers ----------
def _read_sql(db_path: Path, sql: str, params: tuple | list = ()):
    if not db_path.exists():
        abort(404, description=f"DB not found: {db_path}")
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        return pd.read_sql_query(sql, conn, params=params)

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

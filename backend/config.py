import os
from pathlib import Path

# Root and data paths
ROOT_DIR = Path(__file__).resolve().parents[1]

DB_DIR = ROOT_DIR / "data" / "database"
NEWS_DB = DB_DIR / "news_data.db"
REDDIT_DB = DB_DIR / "reddit_data.db"

SBI_CSV = ROOT_DIR / "data" / "raw" / "reddit" / "SBI_month.csv"

USERS_DIR = ROOT_DIR / "data" / "user"
USERS_CSV = USERS_DIR / "user.csv"

DIM_CSV = ROOT_DIR / "data" / "dimension_sub" / "dimensions_sentiment_counts.csv"
MAP_CSV = ROOT_DIR / "data" / "dimension_sub" / "subthemes_with_dim.csv"

# Suggestion directory (can be overridden by env)
PROJECT_ROOT = ROOT_DIR

SUGG_DIR = Path(os.getenv("SUGG_DIR", str(PROJECT_ROOT / "data" / "suggestion"))).resolve()

SR_OVERALL = SUGG_DIR / "overall_sr.json"
SR_DIM_DIR = SUGG_DIR / "dimensions_sr"
SR_SUB_DIR = SUGG_DIR / "subthemes_sr"
SR_MAP_CSV = SUGG_DIR / "subthemes_with_dim_update.csv"

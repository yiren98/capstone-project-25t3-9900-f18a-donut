# data_process.py
# Extract open subthemes and evidences from raw text.
# Usage: python data_process.py path/data.csv
# Input: initial data file with [Title] and [Content] or a single [text] column.
# Default API: Google/Gemini. Optional API: OpenRouter/DeepSeek.
# Outputs:
#   1) data/processed/comments.csv
#      [ID,text,subthemes,subs_sentiment,confidence,subs_evidences]
#   2) data/processed/subthemes.csv
#      [sub_theme,count,attitudes_raw,att_pos,att_neg,att_neu,avg_conf,example,ids]

import os
import json
import time
import sys
from pathlib import Path
from collections import defaultdict, Counter  # kept for compatibility, even if not used directly

import pandas as pd

from data_process_llm import (
    PROVIDER,
    SLEEP_SECONDS,
    RETRIES,
    call_llm,
    validate_subs_against_text,
    flatten_subs,
)

# ---- paths ----
ROOT_DIR = Path(__file__).resolve().parents[1]

if len(sys.argv) > 1:
    CSV_IN = Path(sys.argv[1])
else:
    print("The input file is required.")
    CSV_IN = None

CSV_OUT = ROOT_DIR / "data" / "processed" / "comments.csv"   # output file
SUBS_CSV = ROOT_DIR / "data" / "processed" / "subthemes.csv" # summary file

# ---- progress helper ----
def get_prev_progress(path_obj: Path) -> int:
    """Return how many rows are already written to comments.csv (for resume)."""
    if not path_obj.exists():
        return 0
    try:
        old = pd.read_csv(path_obj, dtype=str)
        return len(old)
    except Exception:
        return 0

# ---- append one processed row ----
def append_one_row(text_value: str, row_out: dict, header_if_new: bool, id_value: int) -> None:
    """Append a single processed row to comments.csv with given ID and text."""
    to_write = dict(row_out)
    to_write["text"] = text_value
    to_write["ID"] = id_value

    cols = ["ID", "text", "subthemes", "subs_sentiment", "confidence", "subs_evidences"]
    out_df = pd.DataFrame([to_write], columns=cols)
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(
        CSV_OUT,
        mode="a",
        header=header_if_new,
        index=False,
        encoding="utf-8-sig",
    )

# ---- rebuild subthemes summary CSV ----
def rebuild_subtheme_summary() -> None:
    """Rebuild subthemes.csv from comments.csv with aggregated stats."""
    if not CSV_OUT.exists():
        return

    try:
        df_all = pd.read_csv(CSV_OUT, dtype=str)
    except Exception:
        return

    if len(df_all) == 0:
        return

    df_all = df_all.fillna("")
    rows = []

    for i, row in df_all.iterrows():
        if "ID" in df_all.columns:
            rid = int(row.get("ID", i + 1))
        else:
            rid = i + 1

        try:
            s_map = json.loads(row.get("subs_sentiment", "{}"))
        except Exception:
            s_map = {}
        if not isinstance(s_map, dict):
            s_map = {}

        try:
            e_map = json.loads(row.get("subs_evidences", "{}"))
        except Exception:
            e_map = {}
        if not isinstance(e_map, dict):
            e_map = {}

        try:
            conf = float(row.get("confidence", 0.0))
        except Exception:
            conf = 0.0

        for sub_name, att in s_map.items():
            name = (sub_name or "").strip()
            if name == "":
                continue
            ev = e_map.get(name, "")
            rows.append(
                {
                    "sub_theme": name,
                    "attitude": str(att).lower() if att else "neutral",
                    "confidence": conf,
                    "example": ev,
                    "row_id": rid,
                }
            )

    if not rows:
        print("Summary updated (0 rows)")
        return

    rec = pd.DataFrame(rows)
    grp = rec.groupby("sub_theme", sort=True)

    agg = grp.agg(
        count=("attitude", "size"),
        att_pos=("attitude", lambda s: (s == "positive").sum()),
        att_neg=("attitude", lambda s: (s == "negative").sum()),
        att_neu=("attitude", lambda s: (s == "neutral").sum()),
        avg_conf=("confidence", "mean"),
    )

    # Example row per subtheme: pick row with max confidence
    idx_max = grp["confidence"].idxmax()
    examples = rec.loc[idx_max].set_index("sub_theme")["example"]

    # Collect IDs per subtheme
    ids_series = grp.apply(
        lambda g: ", ".join(map(str, sorted(set(g["row_id"].tolist())))),
        include_groups=False,
    )

    agg["avg_conf"] = agg["avg_conf"].round(3)
    agg["attitudes_raw"] = (
        "neutral:" + agg["att_neu"].astype(int).astype(str)
        + ", positive:" + agg["att_pos"].astype(int).astype(str)
        + ", negative:" + agg["att_neg"].astype(int).astype(str)
    )

    out = (
        agg.join(examples.rename("example"))
        .join(ids_series.rename("ids"))
        .reset_index()
        .loc[
            :,
            [
                "sub_theme",
                "count",
                "attitudes_raw",
                "att_pos",
                "att_neg",
                "att_neu",
                "avg_conf",
                "example",
                "ids",
            ],
        ]
        .sort_values("count", ascending=False)
    )

    SUBS_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(SUBS_CSV, index=False, encoding="utf-8")
    print(f"Summary updated → {SUBS_CSV} ({len(out)} rows)")

# ---- input loader ----
def load_input_df(path_obj: Path) -> pd.DataFrame:
    """
    Load the raw input CSV and return a DataFrame with a single 'text' column.

    Rules:
      - If there is a 'text' column (any case), use it directly.
      - Else, try Title + Content / selftext / body and join them.
    """
    df = None
    try:
        df = pd.read_csv(path_obj, encoding="utf-8-sig", dtype=str)
    except Exception:
        try:
            df = pd.read_csv(path_obj, dtype=str)
        except Exception as e:
            raise RuntimeError("Cannot read input: " + str(e))

    if df is None:
        raise RuntimeError("Empty input")

    cols_lower = {}
    for c in df.columns:
        cols_lower[str(c).lower()] = c

    # Case 1: direct text column
    if "text" in cols_lower:
        col_text = cols_lower["text"]
        df["text"] = df[col_text].fillna("").astype(str)
        return df[["text"]].copy()

    # Case 2: Title + Content-style columns
    title_col = None
    content_col = None
    if "title" in cols_lower:
        title_col = cols_lower["title"]
    if "content" in cols_lower:
        content_col = cols_lower["content"]
    elif "selftext" in cols_lower:
        content_col = cols_lower["selftext"]
    elif "body" in cols_lower:
        content_col = cols_lower["body"]

    if title_col is None and content_col is None:
        raise RuntimeError("Need 'text' or Title/Content columns")

    if title_col is None:
        title_series = None
    else:
        title_series = df[title_col].fillna("").astype(str)

    if content_col is None:
        content_series = None
    else:
        content_series = df[content_col].fillna("").astype(str)

    if title_series is None and content_series is not None:
        out_series = content_series
    elif content_series is None and title_series is not None:
        out_series = title_series
    else:
        # Join title and content with a separator
        out_series = (
            title_series.str.strip()
            + " — "
            + content_series.str.strip()
        ).str.strip(" —")

    out = pd.DataFrame({"text": out_series})
    return out

# ---- ensure comments.csv has ID column ----
def ensure_out_csv_has_ids(path_obj: Path) -> None:
    """If comments.csv exists but has no ID column, add ID = 1..N."""
    if not path_obj.exists():
        return
    df_old = pd.read_csv(path_obj, dtype=str)
    if "ID" not in df_old.columns:
        df_old.insert(0, "ID", range(1, len(df_old) + 1))
        df_old.to_csv(path_obj, index=False, encoding="utf-8-sig")

# ---- main entry ----
def main() -> None:
    """Main entry: run subthemes extraction and update both output CSVs."""
    if CSV_IN is None:
        return

    ensure_out_csv_has_ids(CSV_OUT)

    df = load_input_df(CSV_IN)
    df["text"] = df["text"].fillna("").astype(str)
    df["Content"] = df["text"]

    n_done = get_prev_progress(CSV_OUT)
    start_idx = n_done
    header_if_new = n_done == 0

    if start_idx >= len(df):
        print(f"All done ({n_done} rows).")
        rebuild_subtheme_summary()
        return

    print(
        f"[provider={PROVIDER}] Resume at {start_idx + 1}/{len(df)} "
        f"(done={n_done})."
    )

    # Quick smoke test for the first pending row
    try:
        smoke_text = df.iloc[start_idx]["Content"]
        smoke = call_llm(smoke_text)
        try:
            subs_n = len(smoke.get("subthemes_open", []))
        except Exception:
            subs_n = 0
        print(
            "[smoke] overall_confidence=",
            smoke.get("confidence", 0.0),
            "subs_n=",
            subs_n,
        )
    except Exception as e:
        print("[smoke warn]", str(e))

    try:
        i = start_idx
        while i < len(df):
            text_i = df.iloc[i]["Content"]
            r = call_llm(text_i)

            subs = r.get("subthemes_open", [])
            subs_valid = validate_subs_against_text(subs, text_i)
            flat = flatten_subs(subs_valid, r.get("confidence", 0.0))
            flat["text"] = text_i

            row_id = i + 1
            append_one_row(text_i, flat, header_if_new, row_id)
            header_if_new = False

            if ((i + 1) % 10 == 0) or ((i + 1) == len(df)):
                print(f"Processed {i + 1}/{len(df)}")

            time.sleep(SLEEP_SECONDS)
            i += 1

        print("Done.")
        rebuild_subtheme_summary()

    except KeyboardInterrupt:
        print("Interrupted. Progress saved.")
        rebuild_subtheme_summary()
    except Exception as e:
        print("[fatal]", repr(e))
        rebuild_subtheme_summary()

if __name__ == "__main__":
    # Simple key checks before running
    if PROVIDER == "gemini" and not os.getenv("GOOGLE_API_KEY"):
        print("GOOGLE_API_KEY missing (PROVIDER=gemini).")
    if PROVIDER == "openrouter" and not os.getenv("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY missing (PROVIDER=openrouter).")
    main()

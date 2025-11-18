# subthe_dimen_core.py
# Core logic for subtheme/dimension summaries:
# - data loading
# - aggregation
# - pipeline runner (no argparse here)

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Callable

import pandas as pd


def slugify(name: str) -> str:
    # Convert label to safe lowercase slug for filenames.
    name = name.strip()
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug.lower() or "item"


def safe_json_loads(s):
    # Safely parse JSON string; return None on failure.
    if pd.isna(s) or not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def aggregate_by_subtheme(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    # Group comments by subtheme and build stats + examples.
    agg: Dict[str, Dict[str, Any]] = {}

    for _, row in df.iterrows():
        body = (row.get("content") or "").strip() or (row.get("text") or "").strip()
        created_time = str(row.get("created_time", ""))
        source = str(row.get("source", ""))
        confidence = row.get("confidence", None)

        dims_raw = row.get("dimensions")
        subs_raw = row.get("subthemes")
        subs_sent_raw = row.get("subs_sentiment")
        subs_evid_raw = row.get("subs_evidences")

        if pd.isna(subs_raw) or not str(subs_raw).strip():
            continue

        subthemes_list = [s.strip() for s in str(subs_raw).split("|") if s.strip()]
        if not subthemes_list:
            continue

        dims_list = [d.strip() for d in str(dims_raw).split("|")] if dims_raw else []
        if dims_list and len(dims_list) < len(subthemes_list):
            dims_list += [dims_list[-1]] * (len(subthemes_list) - len(dims_list))

        sent_map = safe_json_loads(subs_sent_raw) or {}
        evid_map = safe_json_loads(subs_evid_raw) or {}

        for i, sub in enumerate(subthemes_list):
            sent = sent_map.get(sub)
            if sent is None and len(sent_map) == 1:
                sent = list(sent_map.values())[0]

            if sent not in ("positive", "negative"):
                continue

            dim = dims_list[i] if dims_list and i < len(dims_list) else None

            if sub in evid_map:
                ev = evid_map.get(sub)
            elif len(evid_map) == 1:
                ev = list(evid_map.values())[0]
            else:
                ev = ""

            if sub not in agg:
                agg[sub] = {
                    "total_mentions": 0,
                    "sentiment_counts": Counter(),
                    "confidences": [],
                    "dimensions_counter": Counter(),
                    "examples": [],
                }

            item = agg[sub]
            item["total_mentions"] += 1
            item["sentiment_counts"][sent] += 1

            if isinstance(confidence, (int, float)):
                item["confidences"].append(float(confidence))

            if dim:
                item["dimensions_counter"][dim] += 1

            item["examples"].append(
                {
                    "sentiment": sent,
                    "dimension": dim or "",
                    "subtheme": sub,
                    "confidence": float(confidence) if isinstance(confidence, (int, float)) else None,
                    "created_time": created_time,
                    "source": source,
                    "evidence": ev,
                    "content": body[:1000],
                }
            )

    result: Dict[str, Dict[str, Any]] = {}
    for sub, item in agg.items():
        confs = item["confidences"]
        avg_conf = sum(confs) / len(confs) if confs else 0.0
        result[sub] = {
            "total_mentions": item["total_mentions"],
            "sentiment_counts": dict(item["sentiment_counts"]),
            "avg_confidence": avg_conf,
            "dimensions_counter": dict(item["dimensions_counter"]),
            "examples": item["examples"],
        }
    return result


def aggregate_dimensions_from_sub_agg(sub_agg: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    # Build dimension-level stats from subtheme-level aggregation.
    dim_agg: Dict[str, Dict[str, Any]] = {}

    for sub, data in sub_agg.items():
        for ex in data["examples"]:
            dim = ex.get("dimension") or ""
            if not dim:
                continue
            sent = ex.get("sentiment")
            if sent not in ("positive", "negative"):
                continue

            if dim not in dim_agg:
                dim_agg[dim] = {
                    "total_mentions": 0,
                    "sentiment_counts": Counter(),
                    "confidences": [],
                    "subthemes_counter": Counter(),
                    "examples": [],
                }

            item = dim_agg[dim]
            item["total_mentions"] += 1
            item["sentiment_counts"][sent] += 1
            conf = ex.get("confidence")
            if isinstance(conf, (int, float)):
                item["confidences"].append(float(conf))
            item["subthemes_counter"][sub] += 1

            item["examples"].append(
                {
                    "subtheme": sub,
                    "sentiment": sent,
                    "confidence": conf if isinstance(conf, (int, float)) else None,
                    "created_time": ex.get("created_time", ""),
                    "source": ex.get("source", ""),
                    "evidence": ex.get("evidence", ""),
                    "content": ex.get("content", "")[:1000],
                }
            )

    result: Dict[str, Dict[str, Any]] = {}
    for dim, item in dim_agg.items():
        confs = item["confidences"]
        avg_conf = sum(confs) / len(confs) if confs else 0.0
        result[dim] = {
            "total_mentions": item["total_mentions"],
            "sentiment_counts": dict(item["sentiment_counts"]),
            "avg_confidence": avg_conf,
            "subthemes_counter": dict(item["subthemes_counter"]),
            "examples": item["examples"],
        }
    return result


def load_df(csv_path: Path) -> pd.DataFrame:
    # Read CSV with fallback encodings and ensure required columns exist.
    for enc in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            df = pd.read_csv(csv_path, encoding=enc, on_bad_lines="skip")
            break
        except Exception:
            continue
    else:
        raise RuntimeError(f"Failed to read CSV: {csv_path}")

    df.columns = [
        str(c).encode("utf-8", "ignore").decode("utf-8").strip().lstrip("\ufeff")
        for c in df.columns
    ]

    required = [
        "content",
        "dimensions",
        "subthemes",
        "subs_sentiment",
        "confidence",
        "subs_evidences",
        "author",
        "source",
        "created_time",
        "text",
    ]
    for col in required:
        if col not in df.columns:
            df[col] = None

    for col in required:
        df[col] = df[col].fillna("")

    df["raw_text"] = df.apply(
        lambda r: (r.get("content") or "").strip() or (r.get("text") or "").strip(),
        axis=1,
    )
    return df


def run_pipeline(
    args,
    build_client_fn: Callable[[], Any],
    call_llm_fn: Callable[[Any, str, str], Dict[str, Any]],
    quota_check_fn: Callable[[Exception], bool],
) -> None:
    # Run subtheme + dimension summary pipeline using parsed args and injected LLM helpers.
    overwrite_value = str(args.overwrite).strip().lower()
    overwrite_all = overwrite_value == "all"
    overwrite_list = set()

    if not overwrite_all and overwrite_value not in ("none", "", "null"):
        overwrite_list = {
            token.strip().lower()
            for token in str(args.overwrite).split(",")
            if token.strip()
        }

    def should_overwrite(name: str) -> bool:
        # Decide if this label should be overwritten.
        if overwrite_all:
            return True
        if not overwrite_list:
            return False
        lname = name.lower()
        return any(key in lname for key in overwrite_list)

    csv_path = Path(args.csv)
    sub_out_dir = Path(args.outdir)
    sub_out_dir.mkdir(parents=True, exist_ok=True)

    dim_out_dir = None
    if args.dim_outdir:
        dim_out_dir = Path(args.dim_outdir)
        dim_out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[cfg] CSV         = {csv_path}")
    print(f"[cfg] SUB_OUTDIR  = {sub_out_dir}")
    print(f"[cfg] DIM_OUTDIR  = {dim_out_dir if dim_out_dir else '(disabled)'}")
    print(f"[cfg] MODEL       = {args.model}")
    print(f"[cfg] OVERWRITE   = {args.overwrite}")

    df = load_df(csv_path)
    print(f"[info] Loaded {len(df)} rows from {csv_path}")

    sub_agg = aggregate_by_subtheme(df)
    all_subthemes = sorted(sub_agg.keys())
    print(f"[info] Found {len(all_subthemes)} subthemes with positive/negative data")

    if args.limit_subthemes > 0:
        all_subthemes = all_subthemes[: args.limit_subthemes]
        print(
            f"[debug] limit-subthemes = {args.limit_subthemes} "
            f"(effective count = {len(all_subthemes)})"
        )

    client = build_client_fn()

    # Subtheme summaries
    from subthe_dimen_llm import build_prompt_for_subtheme, build_prompt_for_dimension  # lazy import to avoid cycle

    for idx, sub in enumerate(all_subthemes, start=1):
        slug = slugify(sub)
        out_path = sub_out_dir / f"subtheme_{slug}.json"

        if out_path.exists() and not should_overwrite(sub):
            print(f"[{idx}/{len(all_subthemes)}] (subtheme) {sub} -> skip (exists, overwrite=False)")
            continue

        data = sub_agg[sub]
        stats = {
            "total_mentions": data["total_mentions"],
            "sentiment_counts": {
                "positive": data["sentiment_counts"].get("positive", 0),
                "negative": data["sentiment_counts"].get("negative", 0),
            },
            "avg_confidence": data["avg_confidence"],
            "dimensions_counter": data["dimensions_counter"],
        }
        examples = data["examples"][: args.max_examples]

        print(
            f"[{idx}/{len(all_subthemes)}] (subtheme) {sub} "
            f"(mentions={stats['total_mentions']}, examples={len(examples)})"
        )

        prompt = build_prompt_for_subtheme(sub, stats, examples)

        try:
            json_obj = call_llm_fn(client, args.model, prompt)
        except Exception as e:
            print(f"[error] LLM failed for subtheme '{sub}': {e}")

            if quota_check_fn(e):
                print("[fatal] Quota or rate-limit issue detected. Please refresh your API key or wait.")
                return

            json_obj = {
                "subtheme": sub,
                "parent_dimensions": sorted(stats["dimensions_counter"].keys()),
                "overview": "ERROR: LLM call failed.",
                "key_patterns": [],
                "sentiment_snapshot": {
                    "positive": stats["sentiment_counts"]["positive"],
                    "negative": stats["sentiment_counts"]["negative"],
                    "average_confidence": stats["avg_confidence"],
                },
                "typical_contexts": [],
                "risks_and_blindspots": [],
                "recommendations": [],
            }

        with out_path.open("w", encoding="utf-8") as f:
            json.dump(json_obj, f, ensure_ascii=False, indent=2)
        print(f"    -> wrote {out_path}")

    # Dimension summaries (optional)
    if dim_out_dir is not None:
        dim_agg = aggregate_dimensions_from_sub_agg(sub_agg)
        all_dims = sorted(dim_agg.keys())
        print(f"[info] Found {len(all_dims)} dimensions with positive/negative data")

        for idx, dim in enumerate(all_dims, start=1):
            slug = slugify(dim)
            out_path = dim_out_dir / f"dimension_{slug}.json"

            if out_path.exists() and not should_overwrite(dim):
                print(f"[{idx}/{len(all_dims)}] (dimension) {dim} -> skip (exists, overwrite=False)")
                continue

            data = dim_agg[dim]
            stats = {
                "total_mentions": data["total_mentions"],
                "sentiment_counts": {
                    "positive": data["sentiment_counts"].get("positive", 0),
                    "negative": data["sentiment_counts"].get("negative", 0),
                },
                "avg_confidence": data["avg_confidence"],
                "subthemes_counter": data["subthemes_counter"],
            }
            examples = data["examples"][: args.max_examples]

            print(
                f"[{idx}/{len(all_dims)}] (dimension) {dim} "
                f"(mentions={stats['total_mentions']}, examples={len(examples)})"
            )

            prompt = build_prompt_for_dimension(dim, stats, examples)

            top_subthemes_sorted = sorted(
                stats["subthemes_counter"].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            top_subthemes_list = [
                {"subtheme": name, "count": count}
                for name, count in top_subthemes_sorted
            ]

            try:
                json_obj = call_llm_fn(client, args.model, prompt)
                json_obj["sentiment_snapshot"] = {
                    "positive": stats["sentiment_counts"]["positive"],
                    "negative": stats["sentiment_counts"]["negative"],
                    "average_confidence": stats["avg_confidence"],
                }
                json_obj["top_subthemes"] = top_subthemes_list
            except Exception as e:
                print(f"[error] LLM failed for dimension '{dim}': {e}")

                if quota_check_fn(e):
                    print("[fatal] Quota or rate-limit issue detected. Please refresh your API key or wait.")
                    return

                json_obj = {
                    "dimension": dim,
                    "overview": "ERROR: LLM call failed.",
                    "key_patterns": [],
                    "sentiment_snapshot": {
                        "positive": stats["sentiment_counts"]["positive"],
                        "negative": stats["sentiment_counts"]["negative"],
                        "average_confidence": stats["avg_confidence"],
                    },
                    "top_subthemes": top_subthemes_list,
                    "risks_and_blindspots": [],
                    "recommendations": [],
                }

            with out_path.open("w", encoding="utf-8") as f:
                json.dump(json_obj, f, ensure_ascii=False, indent=2)
            print(f"    -> wrote {out_path}")

    print("[done] All subthemes processed; dimensions summarised as requested.")

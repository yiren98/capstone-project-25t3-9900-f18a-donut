"""
Generate an overall corporate culture summary JSON from comments.csv,
using the same data model as test.py (subthemes/dimensions, positive/negative only).

This script:
- Reuses aggregation functions from test.py
- Computes overall sentiment counts and average confidence
- Derives dataset metadata: time coverage, sources, counts
- Asks DeepSeek to produce a single overall report JSON
- Then injects dataset_metadata into the final JSON
"""

import json
import argparse
from pathlib import Path
import pandas as pd

from subthe_dimen_sr import (
    load_df,
    aggregate_by_subtheme,
    aggregate_dimensions_from_sub_agg,
    build_client,
    call_deepseek_json,
    is_quota_or_ratelimit_error,
    DEFAULT_MODEL,
)


def build_overall_prompt(report_title: str,
                         global_stats: dict,
                         top_dimensions: list,
                         top_subthemes: list) -> str:
    """
    Build the DeepSeek prompt for a single overall report.

    global_stats = {
        "total_rows": int,
        "total_mentions": int,
        "sentiment_counts": {"positive": int, "negative": int},
        "average_confidence": float,
    }

    top_dimensions = [
        {"dimension": "...", "mentions": int, "positive": int, "negative": int},
        ...
    ]

    top_subthemes = [
        {"subtheme": "...", "dimension": "...", "mentions": int,
         "positive": int, "negative": int},
        ...
    ]
    """
    pos = global_stats["sentiment_counts"].get("positive", 0)
    neg = global_stats["sentiment_counts"].get("negative", 0)
    avg_conf = global_stats["average_confidence"]

    # Format dimensions block
    dim_lines = []
    for d in top_dimensions:
        dim_lines.append(
            f"- {d['dimension']}: mentions={d['mentions']}, "
            f"positive={d['positive']}, negative={d['negative']}"
        )
    dim_block = "\n".join(dim_lines) if dim_lines else "(no dimension stats)"

    # Format subthemes block
    sub_lines = []
    for s in top_subthemes:
        sub_lines.append(
            f"- {s['subtheme']} (dim={s['dimension']}): mentions={s['mentions']}, "
            f"positive={s['positive']}, negative={s['negative']}"
        )
    sub_block = "\n".join(sub_lines) if sub_lines else "(no subtheme stats)"

    prompt = f"""
        You are a senior corporate culture and ESG advisor.
        You will receive high-level statistics about an organisation's culture-related discourse
        (based on news, social media, analyst commentary, etc.) and must write a single
        executive-level summary and recommendation pack.

        CONTEXT
        =======

        Overall dataset:
        - Total raw rows (comments/news/posts): {global_stats["total_rows"]}
        - Total labelled mentions (subtheme-level): {global_stats["total_mentions"]}
        - Overall sentiment counts (subtheme-level, neutral removed):
        - positive: {pos}
        - negative: {neg}
        - Average confidence (weighted by mentions): {avg_conf:.3f}

        Top dimensions (by mentions):
        {dim_block if dim_block else "(none)"}

        Top subthemes (by mentions):
        {sub_block if sub_block else "(none)"}

        TASK
        ====

        Write a concise overall report in JSON form, targeting a senior executive audience
        (e.g., Group CEO, Board, Chief People Officer). The report should:

        1. Summarise the overall sentiment and main storylines.
        2. Highlight 3–5 key insights that matter most for leadership.
        3. Clearly state whether overall sentiment is predominantly "positive" or "negative"
        (you must infer this from the counts and patterns, but the label must be either
        "positive" or "negative").
        4. Identify 3–5 key risks and 3–5 key opportunities.
        5. Provide 3–5 actionable recommendations with explicit ownership and expected impact.
        6. Include a brief note on limitations / next steps (e.g., need for continued monitoring).

        OUTPUT FORMAT
        =============

        Return STRICT JSON ONLY, with exactly this structure and field names:

        {{
        "report_title": "{report_title}",
        "section": {{
            "executive_briefing": {{
            "title": "<short title for this briefing>",
            "key_insights": [
                "<key insight 1>",
                "<key insight 2>",
                "<key insight 3>",
                "<key insight 4>"
            ],
            "sentiment_and_confidence": {{
                "overall_sentiment": "<\"positive\" or \"negative\">",
                "summary": "<2–3 sentence explanation of the overall sentiment pattern, including counts and confidence in plain language>",
                "counts": {{
                "positive": {pos},
                "negative": {neg}
                }},
                "average_confidence": {avg_conf:.3f}
            }},
            "risks_and_opportunities": {{
                "risks": [
                {{
                    "name": "<risk name>",
                    "description": "<1–2 sentences describing this risk>"
                }},
                {{
                    "name": "<risk name>",
                    "description": "<1–2 sentences describing this risk>"
                }}
                ],
                "opportunities": [
                {{
                    "name": "<opportunity name>",
                    "description": "<1–2 sentences describing this opportunity>"
                }},
                {{
                    "name": "<opportunity name>",
                    "description": "<1–2 sentences describing this opportunity>"
                }}
                ]
            }},
            "actionable_recommendations": [
                {{
                "recommendation": "<clear action statement>",
                "ownership": "<role or team that should own this>",
                "impact": "<short description of expected impact>"
                }},
                {{
                "recommendation": "<clear action statement>",
                "ownership": "<role or team that should own this>",
                "impact": "<short description of expected impact>"
                }},
                {{
                "recommendation": "<clear action statement>",
                "ownership": "<role or team that should own this>",
                "impact": "<short description of expected impact>"
                }}
            ],
            "note": "<brief note on data limitations and need for ongoing monitoring>"
            }}
        }}
        }}

        IMPORTANT:
        - Use the positive/negative counts and average_confidence EXACTLY as given above
        in the 'counts' and 'average_confidence' fields.
        - Do NOT invent new numeric values. You may describe patterns in words, but
        must not contradict the numbers given.
        - Speak as a human consultant, not as an AI model.
        - Output must be valid JSON and parseable.
        """
    return prompt.strip()


def compute_global_stats(df, sub_agg, dim_agg) -> tuple[dict, list, list]:
    """
    Compute overall sentiment stats + top dimensions + top subthemes.

    Returns:
        global_stats, top_dimensions, top_subthemes
    """
    # --- Overall sentiment (from sub_agg) ---
    total_mentions = 0
    total_pos = 0
    total_neg = 0
    weighted_conf_sum = 0.0

    for _, data in sub_agg.items():
        mentions = data["total_mentions"]
        total_mentions += mentions

        pos = data["sentiment_counts"].get("positive", 0)
        neg = data["sentiment_counts"].get("negative", 0)
        total_pos += pos
        total_neg += neg

        # weighted average: sum(avg_conf * mentions) / total_mentions
        avg_conf = data["avg_confidence"]
        weighted_conf_sum += avg_conf * mentions

    avg_conf_global = (weighted_conf_sum / total_mentions) if total_mentions > 0 else 0.0

    global_stats = {
        "total_rows": len(df),
        "total_mentions": total_mentions,
        "sentiment_counts": {
            "positive": total_pos,
            "negative": total_neg,
        },
        "average_confidence": avg_conf_global,
    }

    # --- Top dimensions (by mentions from dim_agg) ---
    dim_items = []
    for dim, data in dim_agg.items():
        dim_items.append({
            "dimension": dim,
            "mentions": data["total_mentions"],
            "positive": data["sentiment_counts"].get("positive", 0),
            "negative": data["sentiment_counts"].get("negative", 0),
        })
    dim_items.sort(key=lambda x: x["mentions"], reverse=True)
    top_dimensions = dim_items[:10]

    # --- Top subthemes (by mentions from sub_agg) ---
    sub_items = []
    for sub, data in sub_agg.items():
        # infer the most common parent dimension for context
        dims_counter = data["dimensions_counter"]
        if dims_counter:
            top_dim = max(dims_counter.items(), key=lambda x: x[1])[0]
        else:
            top_dim = ""
        sub_items.append({
            "subtheme": sub,
            "dimension": top_dim,
            "mentions": data["total_mentions"],
            "positive": data["sentiment_counts"].get("positive", 0),
            "negative": data["sentiment_counts"].get("negative", 0),
        })
    sub_items.sort(key=lambda x: x["mentions"], reverse=True)
    top_subthemes = sub_items[:10]

    return global_stats, top_dimensions, top_subthemes


def compute_dataset_metadata(df: pd.DataFrame,
                             global_stats: dict,
                             sub_agg: dict,
                             dim_agg: dict) -> dict:
    """
    Compute dataset-level metadata from raw df + aggregations.

    Returns a dict like:
    {
      "time_coverage": {...},
      "volume": {...},
      "structure": {...},
      "sources": {...}
    }
    """
    # ---- Time coverage ----
    # created_time 
    created_series = pd.to_datetime(df["created_time"], errors="coerce")
    created_series = created_series.dropna()
    if len(created_series) > 0:
        start_ts = created_series.min()
        end_ts = created_series.max()
        span_days = (end_ts - start_ts).days
        time_meta = {
            "start": start_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "end": end_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "span_days": int(span_days),
        }
    else:
        time_meta = {
            "start": None,
            "end": None,
            "span_days": None,
        }

    # ---- Sources ----
    source_series = df["source"].fillna("").astype(str).str.strip()
    non_empty = source_series[source_series != ""]
    total_unique_sources = non_empty.nunique()
    vc = non_empty.value_counts()
    top_sources = [
        {"source": src, "rows": int(cnt)}
        for src, cnt in vc.head(10).items()
    ]

    # ---- Structure / volumes ----
    num_subthemes = len(sub_agg)
    num_dimensions = len(dim_agg)

    metadata = {
        "time_coverage": time_meta,
        "volume": {
            "total_rows": global_stats["total_rows"],
            "total_mentions": global_stats["total_mentions"],
            "sentiment_counts": global_stats["sentiment_counts"],
            "average_confidence": global_stats["average_confidence"],
        },
        "structure": {
            "num_subthemes": num_subthemes,
            "num_dimensions": num_dimensions,
        },
        "sources": {
            "total_unique_sources": int(total_unique_sources),
            "top_sources": top_sources,
        },
    }
    return metadata


def main():
    parser = argparse.ArgumentParser(
        description="Generate an overall corporate culture JSON summary from comments.csv."
    )
    parser.add_argument("--csv", required=True, help="Path to comments.csv")
    parser.add_argument("--out", required=True, help="Path to output JSON file")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="LLM model name")
    parser.add_argument(
        "--title",
        default="Corporate Culture — Overall Summary",
        help="Report title to embed in JSON (default: 'Corporate Culture — Overall Summary')",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    out_path = Path(args.out)

    print(f"[cfg] CSV   = {csv_path}")
    print(f"[cfg] OUT   = {out_path}")
    print(f"[cfg] MODEL = {args.model}")
    print(f"[cfg] TITLE = {args.title}")

    # 1. Load data
    df = load_df(csv_path)
    print(f"[info] Loaded {len(df)} rows from {csv_path}")

    # 2. Aggregate by subtheme and dimension
    sub_agg = aggregate_by_subtheme(df)
    print(f"[info] Subthemes with data: {len(sub_agg)}")

    dim_agg = aggregate_dimensions_from_sub_agg(sub_agg)
    print(f"[info] Dimensions with data: {len(dim_agg)}")

    # 3. Compute global stats and top lists
    global_stats, top_dimensions, top_subthemes = compute_global_stats(df, sub_agg, dim_agg)

    print("[info] Global sentiment stats:",
          f"pos={global_stats['sentiment_counts']['positive']}, ",
          f"neg={global_stats['sentiment_counts']['negative']}, ",
          f"avg_conf={global_stats['average_confidence']:.3f}")

    # 4. Dataset metadata
    dataset_metadata = compute_dataset_metadata(df, global_stats, sub_agg, dim_agg)

    # 5. Build prompt for LLM
    prompt = build_overall_prompt(
        report_title=args.title,
        global_stats=global_stats,
        top_dimensions=top_dimensions,
        top_subthemes=top_subthemes,
    )

    # 6. Call DeepSeek
    client = build_client()
    try:
        json_obj = call_deepseek_json(client, args.model, prompt)
    except Exception as e:
        print(f"[error] LLM failed to generate overall report: {e}")
        if is_quota_or_ratelimit_error(e):
            print("[fatal] Suspected quota / rate limit issue. Please check your API usage.")
            return

        # Fallback: minimal error JSON
        json_obj = {
            "report_title": args.title,
            "section": {
                "executive_briefing": {
                    "title": "ERROR: LLM call failed.",
                    "key_insights": [],
                    "sentiment_and_confidence": {
                        "overall_sentiment": "negative"
                        if global_stats["sentiment_counts"]["negative"]
                        >= global_stats["sentiment_counts"]["positive"]
                        else "positive",
                        "summary": "ERROR: LLM call failed while generating the overall summary.",
                        "counts": global_stats["sentiment_counts"],
                        "average_confidence": global_stats["average_confidence"],
                    },
                    "risks_and_opportunities": {
                        "risks": [],
                        "opportunities": [],
                    },
                    "actionable_recommendations": [],
                    "note": "Report generation failed due to LLM error.",
                }
            }
        }

    # 7. Inject dataset_metadata 
    json_obj["dataset_metadata"] = dataset_metadata

    # 8. Write output JSON
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(json_obj, f, ensure_ascii=False, indent=2)

    print(f"[done] Wrote overall report JSON -> {out_path}")


if __name__ == "__main__":
    main()

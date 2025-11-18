# subthe_dimen_sr.py
# Generate JSON summaries for subthemes (and optionally dimensions)
# using DeepSeek via OpenRouter.
#
# Input: comments.csv with columns:
#   [tag,text,author,score,comment_count,content,created_time,
#    dimensions,subthemes,subs_sentiment,confidence,subs_evidences,source]
#
# Outputs:
#   Subthemes:  <outdir>/subtheme_<slug>.json
#   Dimensions: <dim-outdir>/dimension_<slug>.json
#
# Usage (subthemes only):
#   python subthe_dimen_sr.py --csv comments.csv --outdir subthemes_sr --max-examples 10
#
# Usage (subthemes + dimensions):
#   python subthe_dimen_sr.py --csv comments.csv --outdir subthemes_sr --dim-outdir dimensions_sr
#
# Overwrite examples:
#   python subthe_dimen_sr.py --csv comments.csv --outdir subthemes_sr --dim-outdir dimensions_sr --overwrite
#   python subthe_dimen_sr.py --csv comments.csv --outdir subthemes_sr --dim-outdir dimensions_sr --overwrite all
#   python subthe_dimen_sr.py --csv comments.csv --outdir subthemes_sr --dim-outdir dimensions_sr \
#       --overwrite "Accountability,Digital"

from __future__ import annotations

import argparse
from typing import List

from subthe_dimen_llm import (
    DEFAULT_MODEL,
    build_client as _build_client_impl,
    call_deepseek_json as _call_deepseek_impl,
    is_quota_or_ratelimit_error as _quota_impl,
)
from subthe_dimen_core import (
    aggregate_by_subtheme,
    aggregate_dimensions_from_sub_agg,
    load_df,
    run_pipeline,
)


def build_client():
    # Thin wrapper so tests can monkeypatch this name.
    return _build_client_impl()


def call_deepseek_json(client, model: str, prompt: str):
    # Thin wrapper so tests can monkeypatch this name.
    return _call_deepseek_impl(client, model, prompt)


def is_quota_or_ratelimit_error(err: Exception) -> bool:
    # Thin wrapper so tests can monkeypatch this name if needed.
    return _quota_impl(err)


def main(argv: List[str] | None = None) -> None:
    # Parse CLI args and call core pipeline.
    parser = argparse.ArgumentParser(
        description=(
            "Generate JSON summaries for subthemes (and optionally dimensions), "
            "positive/negative only, with selective overwrite."
        )
    )
    parser.add_argument("--csv", required=True, help="Path to comments.csv")
    parser.add_argument(
        "--outdir",
        required=True,
        help="Output directory for subtheme JSON files",
    )
    parser.add_argument(
        "--dim-outdir",
        help="Optional output directory for dimension JSON files",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="LLM model name",
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=5,
        help="Maximum examples per label (subtheme/dimension)",
    )
    parser.add_argument(
        "--limit-subthemes",
        type=int,
        default=0,
        help="Limit N subthemes for debug (0 = all)",
    )
    parser.add_argument(
        "--overwrite",
        nargs="?",
        const="all",
        default="none",
        help=(
            "Overwrite behaviour for subthemes and dimensions:\n"
            "  --overwrite           → overwrite all existing files\n"
            "  --overwrite all       → overwrite all existing files\n"
            "  --overwrite 'A,B,C'   → only overwrite labels whose names contain A or B or C\n"
            "  (default: 'none' → existing files are skipped)"
        ),
    )

    args = parser.parse_args(argv)

    run_pipeline(
        args,
        build_client_fn=build_client,
        call_llm_fn=call_deepseek_json,
        quota_check_fn=is_quota_or_ratelimit_error,
    )


if __name__ == "__main__":
    main()

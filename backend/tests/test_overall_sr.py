# Tests for overall_sr functions and main()
# Features:
# - Test compute_global_stats and compute_dataset_metadata with small fake data
# - Test overall_sr.main end-to-end with patched I/O and fake LLM calls
# - Ensure JSON summary is created and has the expected structure
#
# Usage:
#   pytest tests/test_overall_sr.py -q

import json
from pathlib import Path
import pandas as pd
import overall_sr

# Basic check for compute_global_stats and compute_dataset_metadata
def test_compute_global_stats_and_metadata():
    # Fake df with two rows
    df = pd.DataFrame(
        {
            "created_time": ["2024-01-01 10:00:00", "2024-01-10 12:00:00"],
            "source": ["reddit", "news"],
        }
    )

    # Fake sub_agg: two subthemes
    sub_agg = {
        "Theme A": {
            "total_mentions": 3,
            "sentiment_counts": {"positive": 2, "negative": 1},
            "avg_confidence": 0.9,
            "dimensions_counter": {"Accountability": 3},
        },
        "Theme B": {
            "total_mentions": 1,
            "sentiment_counts": {"positive": 0, "negative": 1},
            "avg_confidence": 0.7,
            "dimensions_counter": {"Respect": 1},
        },
    }

    # Fake dim_agg: two dimensions
    dim_agg = {
        "Accountability": {
            "total_mentions": 3,
            "sentiment_counts": {"positive": 2, "negative": 1},
        },
        "Respect": {
            "total_mentions": 1,
            "sentiment_counts": {"positive": 0, "negative": 1},
        },
    }

    global_stats, top_dims, top_subs = overall_sr.compute_global_stats(
        df, sub_agg, dim_agg
    )

    # Global stats
    assert global_stats["total_rows"] == 2
    assert global_stats["total_mentions"] == 4
    assert global_stats["sentiment_counts"]["positive"] == 2
    assert global_stats["sentiment_counts"]["negative"] == 2
    assert 0.0 < global_stats["average_confidence"] <= 1.0

    # Top dimensions sorted by mentions
    assert top_dims[0]["dimension"] == "Accountability"
    assert top_dims[0]["mentions"] == 3

    # Top subthemes sorted by mentions
    assert top_subs[0]["subtheme"] == "Theme A"
    assert top_subs[0]["mentions"] == 3

    # Dataset metadata
    meta = overall_sr.compute_dataset_metadata(df, global_stats, sub_agg, dim_agg)
    assert "time_coverage" in meta
    assert "volume" in meta
    assert "structure" in meta
    assert "sources" in meta
    assert meta["volume"]["total_rows"] == 2
    assert meta["structure"]["num_subthemes"] == 2
    assert meta["structure"]["num_dimensions"] == 2


# End-to-end style test for overall_sr.main
def test_overall_sr_main_creates_json(tmp_path, monkeypatch):
    # ---- Prepare fake CSV path and output path ----
    csv_path = tmp_path / "comments.csv"
    csv_path.write_text("dummy,header\n1,2\n", encoding="utf-8")  # not really used

    out_path = tmp_path / "overall_summary.json"

    # ---- Fake df ----
    fake_df = pd.DataFrame(
        {
            "created_time": ["2024-01-01 10:00:00"],
            "source": ["reddit"],
        }
    )

    # ---- Fake sub_agg and dim_agg ----
    fake_sub_agg = {
        "Theme A": {
            "total_mentions": 2,
            "sentiment_counts": {"positive": 1, "negative": 1},
            "avg_confidence": 0.8,
            "dimensions_counter": {"Accountability": 2},
            "examples": [],
        }
    }
    fake_dim_agg = {
        "Accountability": {
            "total_mentions": 2,
            "sentiment_counts": {"positive": 1, "negative": 1},
            "avg_confidence": 0.8,
            "subthemes_counter": {"Theme A": 2},
            "examples": [],
        }
    }

    # ---- Patch pure functions ----
    monkeypatch.setattr(overall_sr, "load_df", lambda p: fake_df)
    monkeypatch.setattr(overall_sr, "aggregate_by_subtheme", lambda _df: fake_sub_agg)
    monkeypatch.setattr(
        overall_sr,
        "aggregate_dimensions_from_sub_agg",
        lambda _agg: fake_dim_agg,
    )

    # ---- Patch client + LLM call ----
    def fake_build_client():
        # Client is not used by fake_call_deepseek_json
        return None

    def fake_call_deepseek_json(client, model, prompt):
        # Return a minimal valid structure that matches the expected schema
        return {
            "report_title": "Test Report",
            "section": {
                "executive_briefing": {
                    "title": "Test Briefing",
                    "key_insights": ["a", "b"],
                    "sentiment_and_confidence": {
                        "overall_sentiment": "positive",
                        "summary": "test",
                        "counts": {"positive": 1, "negative": 1},
                        "average_confidence": 0.8,
                    },
                    "risks_and_opportunities": {
                        "risks": [],
                        "opportunities": [],
                    },
                    "actionable_recommendations": [],
                    "note": "test note",
                }
            },
        }

    monkeypatch.setattr(overall_sr, "build_client", fake_build_client)
    monkeypatch.setattr(overall_sr, "call_deepseek_json", fake_call_deepseek_json)

    # ---- Patch argv and run main ----
    import sys

    argv_backup = sys.argv[:]
    sys.argv = [
        "overall_sr.py",
        "--csv",
        str(csv_path),
        "--out",
        str(out_path),
        "--title",
        "Corporate Culture — Overall Summary",
    ]
    try:
        overall_sr.main()
    finally:
        sys.argv = argv_backup

    # ---- Check output JSON ----
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))

    assert "report_title" in data
    assert "section" in data
    assert "dataset_metadata" in data
    assert "time_coverage" in data["dataset_metadata"]
    assert "volume" in data["dataset_metadata"]

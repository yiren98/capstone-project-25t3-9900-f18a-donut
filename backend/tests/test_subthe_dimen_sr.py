# Tests for subthe_dimen_sr aggregation and main()
# Features:
# - Test aggregate_by_subtheme with a minimal single-row DataFrame
# - Test aggregate_dimensions_from_sub_agg using a small fake subtheme aggregation
# - Run subthe_dimen_sr.main end-to-end with fake LLM client and check JSON outputs
#
# Usage:
#   pytest tests/test_subthe_dimen_sr.py -q

import json
from pathlib import Path
import pandas as pd
import subthe_dimen_sr

def test_aggregate_by_subtheme_basic():
    # Check that aggregate_by_subtheme builds counts and examples correctly
    # for a minimal input with one subtheme and one dimension.
    df = pd.DataFrame(
        {
            "content": ["Some text about governance."],
            "text": [""],
            "dimensions": ["Accountability"],
            "subthemes": ["Corporate Governance & Oversight"],
            "subs_sentiment": [
                '{"Corporate Governance & Oversight": "positive"}'
            ],
            "confidence": [0.9],
            "subs_evidences": [
                '{"Corporate Governance & Oversight": "example snippet"}'
            ],
            "author": ["user1"],
            "source": ["reddit"],
            "created_time": ["2024-01-01 10:00:00"],
        }
    )

    agg = subthe_dimen_sr.aggregate_by_subtheme(df)
    assert "Corporate Governance & Oversight" in agg

    item = agg["Corporate Governance & Oversight"]
    assert item["total_mentions"] == 1
    assert item["sentiment_counts"]["positive"] == 1
    assert item["avg_confidence"] == 0.9
    assert item["dimensions_counter"]["Accountability"] == 1
    assert len(item["examples"]) == 1

    ex = item["examples"][0]
    assert ex["sentiment"] == "positive"
    assert ex["dimension"] == "Accountability"
    assert "content" in ex


def test_aggregate_dimensions_from_sub_agg_basic():
    # Check that dimension aggregation is built correctly from subtheme aggregation.
    sub_agg = {
        "Corporate Governance & Oversight": {
            "total_mentions": 2,
            "sentiment_counts": {"positive": 1, "negative": 1},
            "avg_confidence": 0.8,
            "dimensions_counter": {"Accountability": 2},
            "examples": [
                {
                    "subtheme": "Corporate Governance & Oversight",
                    "sentiment": "positive",
                    "dimension": "Accountability",
                    "confidence": 0.9,
                    "created_time": "2024-01-01",
                    "source": "reddit",
                    "evidence": "foo",
                    "content": "bar",
                },
                {
                    "subtheme": "Corporate Governance & Oversight",
                    "sentiment": "negative",
                    "dimension": "Accountability",
                    "confidence": 0.7,
                    "created_time": "2024-01-02",
                    "source": "news",
                    "evidence": "foo2",
                    "content": "bar2",
                },
            ],
        }
    }

    dim_agg = subthe_dimen_sr.aggregate_dimensions_from_sub_agg(sub_agg)
    assert "Accountability" in dim_agg

    item = dim_agg["Accountability"]
    assert item["total_mentions"] == 2
    assert item["sentiment_counts"]["positive"] == 1
    assert item["sentiment_counts"]["negative"] == 1
    assert len(item["examples"]) == 2
    assert item["avg_confidence"] == (0.9 + 0.7) / 2


def test_subthe_dimen_main_creates_files(tmp_path, monkeypatch):
    # End-to-end style test for subthe_dimen_sr.main.
    # It uses:
    #   - a tiny comments.csv with one subtheme and one dimension
    #   - real load_df / aggregation logic
    #   - fake build_client
    #   - fake call_deepseek_json (no real LLM call)

    # ---- Create minimal comments.csv ----
    csv_path = tmp_path / "comments.csv"
    df = pd.DataFrame(
        {
            "content": ["Some text about governance."],
            "text": [""],
            "dimensions": ["Accountability"],
            "subthemes": ["Corporate Governance & Oversight"],
            "subs_sentiment": [
                '{"Corporate Governance & Oversight": "positive"}'
            ],
            "confidence": [0.9],
            "subs_evidences": [
                '{"Corporate Governance & Oversight": "example snippet"}'
            ],
            "author": ["user1"],
            "source": ["reddit"],
            "created_time": ["2024-01-01 10:00:00"],
        }
    )
    df.to_csv(csv_path, index=False, encoding="utf-8")

    sub_outdir = tmp_path / "subthemes_sr"
    dim_outdir = tmp_path / "dimensions_sr"

    # ---- Fake client + fake LLM call ----
    def fake_build_client():
        return None

    def fake_call_deepseek_json(client, model, prompt):
        # Return a very small dict; real shape is not important for this smoke test.
        return {"ok": True, "model": model}

    monkeypatch.setattr(subthe_dimen_sr, "build_client", fake_build_client)
    monkeypatch.setattr(
        subthe_dimen_sr, "call_deepseek_json", fake_call_deepseek_json
    )

    # ---- Patch argv and run main ----
    import sys

    argv_backup = sys.argv[:]
    sys.argv = [
        "subthe_dimen_sr.py",
        "--csv",
        str(csv_path),
        "--outdir",
        str(sub_outdir),
        "--dim-outdir",
        str(dim_outdir),
        "--max-examples",
        "3",
        "--limit-subthemes",
        "1",
        "--overwrite",
        "all",
    ]
    try:
        subthe_dimen_sr.main()
    finally:
        sys.argv = argv_backup

    # ---- Check output dirs and JSON files ----
    assert sub_outdir.exists()
    sub_files = list(sub_outdir.glob("subtheme_*.json"))
    assert len(sub_files) == 1

    assert dim_outdir.exists()
    dim_files = list(dim_outdir.glob("dimension_*.json"))
    assert len(dim_files) == 1

    # ---- Check JSON is valid ----
    sub_data = json.loads(sub_files[0].read_text(encoding="utf-8"))
    assert isinstance(sub_data, dict)
    dim_data = json.loads(dim_files[0].read_text(encoding="utf-8"))
    assert isinstance(dim_data, dict)

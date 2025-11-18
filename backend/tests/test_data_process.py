# Integration test for data_process.main()
# Features:
# - Build a minimal input.csv with Title + Content
# - Patch paths to a temporary folder (no real project files are touched)
# - Mock call_llm so no real LLM / API is called
# - Check that comments.csv and subthemes.csv are generated correctly
#
# Usage:
#   pytest tests/test_data_process.py -q

import json
from pathlib import Path
import pandas as pd
import data_process

def test_data_process_generates_comments_and_subthemes(tmp_path, monkeypatch):
    # ---------- 1) Create a small input.csv in the temporary directory ----------
    input_path = tmp_path / "input.csv"
    df_in = pd.DataFrame(
        {
            "Title": ["Rio Tinto safety record"],
            "Content": [
                "Rio Tinto improved safety culture and innovation in mining operations."
            ],
        }
    )
    df_in.to_csv(input_path, index=False, encoding="utf-8-sig")

    # ---------- 2) Patch paths: ROOT_DIR / CSV_IN / CSV_OUT / SUBS_CSV ----------
    # Point ROOT_DIR to tmp_path so all outputs are written into the temp folder
    monkeypatch.setattr(data_process, "ROOT_DIR", tmp_path)

    # Override input file path
    monkeypatch.setattr(data_process, "CSV_IN", input_path)

    # Override output file paths
    csv_out = tmp_path / "data" / "processed" / "comments.csv"
    subs_csv = tmp_path / "data" / "processed" / "subthemes.csv"
    monkeypatch.setattr(data_process, "CSV_OUT", csv_out)
    monkeypatch.setattr(data_process, "SUBS_CSV", subs_csv)

    # Disable sleep to keep the test fast
    monkeypatch.setattr(data_process, "SLEEP_SECONDS", 0)

    # ---------- 3) Mock call_llm: return a fixed, valid JSON structure ----------
    def fake_call_llm(text: str):
        # evidence must be a substring of text, otherwise validate_subs_against_text will drop it
        return {
            "confidence": 0.9,
            "subthemes_open": [
                {
                    "name": "Safety",
                    "attitude": "positive",
                    "evidence": "improved safety culture",
                    "confidence": 0.9,
                },
                {
                    "name": "Innovation",
                    "attitude": "positive",
                    "evidence": "innovation in mining operations",
                    "confidence": 0.8,
                },
            ],
            "reason": "test stub",
        }

    monkeypatch.setattr(data_process, "call_llm", fake_call_llm)

    # ---------- 4) Run main() to execute the full pipeline ----------
    data_process.main()

    # ---------- 5) Check comments.csv ----------
    assert csv_out.exists(), "comments.csv should be created"

    df_out = pd.read_csv(csv_out, encoding="utf-8-sig")

    # Column order must match the contract
    assert list(df_out.columns) == [
        "ID",
        "text",
        "subthemes",
        "subs_sentiment",
        "confidence",
        "subs_evidences",
    ]

    # Only one row should be processed
    assert len(df_out) == 1
    row = df_out.iloc[0]

    # ID should start from 1
    assert str(row["ID"]) == "1"

    # Text should contain the original content
    assert "Rio Tinto improved safety culture" in row["text"]

    # subthemes should contain both Safety and Innovation
    subs = row["subthemes"].split("|") if isinstance(row["subthemes"], str) else []
    assert set(subs) == {"Safety", "Innovation"}

    # subs_sentiment: JSON keys are subtheme names, values are sentiment labels
    sent_map = json.loads(row["subs_sentiment"])
    assert sent_map["Safety"] == "positive"
    assert sent_map["Innovation"] == "positive"

    # subs_evidences: JSON keys are subtheme names, values are evidence snippets
    evid_map = json.loads(row["subs_evidences"])
    assert "improved safety culture" in evid_map["Safety"]
    assert "innovation in mining operations" in evid_map["Innovation"]

    # ---------- 6) Check subthemes.csv summary ----------
    assert subs_csv.exists(), "subthemes.csv summary should be created"

    df_sum = pd.read_csv(subs_csv, encoding="utf-8")

    expected_cols = [
        "sub_theme",
        "count",
        "attitudes_raw",
        "att_pos",
        "att_neg",
        "att_neu",
        "avg_conf",
        "example",
        "ids",
    ]
    assert list(df_sum.columns) == expected_cols

    # There should be two subthemes: Safety and Innovation
    assert set(df_sum["sub_theme"]) == {"Safety", "Innovation"}

    # Each subtheme count should be 1
    counts = dict(zip(df_sum["sub_theme"], df_sum["count"]))
    assert counts["Safety"] == 1
    assert counts["Innovation"] == 1

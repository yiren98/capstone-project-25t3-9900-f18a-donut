# Test for sentiment_dbcheck main()
# Features:
# - Create a temporary comments.csv with neutral + positive labels
# - Patch CSV_IN and patch infer_binary_sentiment
# - Run sentiment_dbcheck.main()
# - Check updated subsentiment, confidence, and evidences remain unchanged
#
# Usage:
#   pytest tests/test_sentiment_dbcheck.py -q

import json
from pathlib import Path
import pandas as pd
import sentiment_dbcheck

def test_sentiment_dbcheck_updates_neutral_and_confidence(tmp_path, monkeypatch):

    # ----- Build input comments.csv -----
    csv_path = tmp_path / "comments.csv"

    row = {
        "ID": 1,
        "text": "Rio Tinto improved safety culture but some issues remain.",
        "subthemes": "Safety|Innovation",
        "subs_sentiment": json.dumps(
            {"Safety": "neutral", "Innovation": "positive"},
            ensure_ascii=False,
        ),
        "confidence": 0.5,
        "subs_evidences": json.dumps(
            {
                "Safety": "improved safety culture",
                "Innovation": "some innovative projects",
            },
            ensure_ascii=False,
        ),
    }

    df_in = pd.DataFrame([row])
    df_in.to_csv(csv_path, index=False, encoding="utf-8")

    # ----- Patch CSV_IN -----
    monkeypatch.setattr(sentiment_dbcheck, "CSV_IN", csv_path)

    # ----- Patch infer_binary_sentiment -----
    def fake_infer_binary_sentiment(texts):
        labels = []
        confs = []
        for t in texts:
            labels.append("positive")
            confs.append(0.9)
        return labels, confs

    monkeypatch.setattr(
        sentiment_dbcheck,
        "infer_binary_sentiment",
        fake_infer_binary_sentiment,
    )

    # ----- Run main() -----
    sentiment_dbcheck.main()

    # ----- Read output -----
    df_out = pd.read_csv(csv_path, encoding="utf-8")

    # Check required columns
    assert list(df_out.columns) == sentiment_dbcheck.REQUIRED_COLS

    assert len(df_out) == 1
    out_row = df_out.iloc[0]

    # Check updated sentiment map
    new_sent_map = json.loads(out_row["subs_sentiment"])
    assert new_sent_map["Safety"] == "positive"
    assert new_sent_map["Innovation"] == "positive"

    # Confidence updated to >= model confidence
    assert float(out_row["confidence"]) >= 0.9

    # Evidence stays unchanged
    evid_map = json.loads(out_row["subs_evidences"])
    assert evid_map["Safety"] == "improved safety culture"
    assert evid_map["Innovation"] == "some innovative projects"

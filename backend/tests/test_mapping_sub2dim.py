import json
import sys
from pathlib import Path
import pandas as pd
import mapping_sub2dim


def test_mapping_sub2dim_updates_comments(tmp_path, monkeypatch):

    # ---------- input1: dimension_clusters.json ----------
    clusters = {
        "Agility": [
            {
                "representative": "Rep1",
                "members": ["SubA", "SubB"],
            }
        ],
        "Performance": [
            {
                "representative": "Rep2",
                "members": ["SubC"],
            }
        ],
        "Respect": [],
    }

    json_path = tmp_path / "dimension_clusters.json"
    json_path.write_text(json.dumps(clusters, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- input2: comments.csv ----------
    csv_path = tmp_path / "comments.csv"

    rows = [
        {
            "ID": 1,
            "text": "Row 1 text about safety and agility.",
            "subthemes": "SubA|SubB",
            "subs_sentiment": json.dumps(
                {
                    "SubA": "positive",
                    "SubB": "negative",
                },
                ensure_ascii=False,
            ),
            "confidence": 0.5,
            "subs_evidences": json.dumps(
                {
                    "SubA": "evA",
                    "SubB": "evB",
                },
                ensure_ascii=False,
            ),
        },
        {
            "ID": 2,
            "text": "Row 2 text about performance and some unknown theme.",
            "subthemes": "SubC|Unknown",
            "subs_sentiment": json.dumps(
                {
                    "SubC": "neutral",
                    "Unknown": "positive",
                },
                ensure_ascii=False,
            ),
            "confidence": 0.7,
            "subs_evidences": json.dumps(
                {
                    "SubC": "evC",
                    "Unknown": "",
                },
                ensure_ascii=False,
            ),
        },
    ]

    df = pd.DataFrame(rows, columns=[
        "ID",
        "text",
        "subthemes",
        "subs_sentiment",
        "confidence",
        "subs_evidences",
    ])
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # ---------- running main() ----------
    monkeypatch.setattr(
        sys,
        "argv",
        ["mapping_sub2dim.py", str(csv_path), str(json_path)],
        raising=False,
    )

    mapping_sub2dim.main()

    # ---------- reinput comments.csv, check the result ----------
    df_out = pd.read_csv(csv_path, encoding="utf-8-sig")

    assert "Dimensions" in df_out.columns

    # -------- Row 0 checks --------
    row0 = df_out.iloc[0]

    assert row0["subthemes"] == "Rep1"

    assert row0["Dimensions"] == "Agility"

    # sentiment：SubA positive + SubB negative → negative
    sent0 = json.loads(row0["subs_sentiment"])
    assert sent0 == {"Rep1": "negative"}

    evid0 = json.loads(row0["subs_evidences"])
    assert evid0 == {"Rep1": "evA"}

    # -------- Row 1 checks --------
    row1 = df_out.iloc[1]
    
    assert row1["subthemes"] == "Rep2|Unknown"
    
    assert row1["Dimensions"] == "Performance"

    sent1 = json.loads(row1["subs_sentiment"])

    assert sent1 == {"Rep2": "neutral", "Unknown": "positive"}

    evid1 = json.loads(row1["subs_evidences"])
    # Only Rep2 has non-empty evidence
    assert evid1 == {"Rep2": "evC"}

    assert df_out.loc[0, "ID"] == 1
    assert df_out.loc[1, "ID"] == 2
    assert df_out.loc[0, "text"] == "Row 1 text about safety and agility."
    assert df_out.loc[1, "text"] == "Row 2 text about performance and some unknown theme."

import json
from pathlib import Path

import pandas as pd

import data_process


def test_data_process_generates_comments_and_subthemes(tmp_path, monkeypatch):
    """
    集成测试：
    - 构造一个最小 input.csv（Title + Content）
    - monkeypatch 路径到 tmp_path（不会污染真实项目）
    - mock call_llm（不调用 Gemini / OpenRouter）
    - 调用 data_process.main()
    - 检查：
        * comments.csv 是否生成，列是否正确
        * subs_sentiment / subs_evidences JSON 是否可解析
        * subthemes.csv 汇总是否正确
    """

    # ---------- 1) 在临时目录里造一个输入文件 ----------
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

    # ---------- 2) monkeypatch 路径：ROOT_DIR / CSV_IN / CSV_OUT / SUBS_CSV ----------
    # 把 ROOT_DIR 指向 tmp_path，这样所有输出都写到 tmp 里
    monkeypatch.setattr(data_process, "ROOT_DIR", tmp_path)

    # 覆盖输入文件路径
    monkeypatch.setattr(data_process, "CSV_IN", input_path)

    # 覆盖输出文件路径
    csv_out = tmp_path / "data" / "processed" / "comments.csv"
    subs_csv = tmp_path / "data" / "processed" / "subthemes.csv"
    monkeypatch.setattr(data_process, "CSV_OUT", csv_out)
    monkeypatch.setattr(data_process, "SUBS_CSV", subs_csv)

    # 关掉 sleep（不然会很慢）
    monkeypatch.setattr(data_process, "SLEEP_SECONDS", 0)

    # ---------- 3) mock call_llm：返回一个固定的、合法的 JSON 结构 ----------
    def fake_call_llm(text: str):
        # evidence 必须是 text 的子串，否则 validate_subs_against_text 会丢掉
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

    # ---------- 4) 调用 main() 运行完整流程 ----------
    data_process.main()

    # ---------- 5) 检查 comments.csv ----------
    assert csv_out.exists(), "comments.csv should be created"

    df_out = pd.read_csv(csv_out, encoding="utf-8-sig")

    # 列顺序必须符合约定
    assert list(df_out.columns) == [
        "ID",
        "text",
        "subthemes",
        "subs_sentiment",
        "confidence",
        "subs_evidences",
    ]

    # 只处理了 1 行
    assert len(df_out) == 1
    row = df_out.iloc[0]

    # ID 从 1 开始
    assert str(row["ID"]) == "1"

    # 文本应该包含原始内容
    assert "Rio Tinto improved safety culture" in row["text"]

    # subthemes：应该包含 Safety 和 Innovation
    subs = row["subthemes"].split("|") if isinstance(row["subthemes"], str) else []
    assert set(subs) == {"Safety", "Innovation"}

    # subs_sentiment：JSON 中 key 应该是子主题名，值是情感标签
    sent_map = json.loads(row["subs_sentiment"])
    assert sent_map["Safety"] == "positive"
    assert sent_map["Innovation"] == "positive"

    # subs_evidences：JSON 中 key 仍然是子主题名，值是证据子串
    evid_map = json.loads(row["subs_evidences"])
    assert "improved safety culture" in evid_map["Safety"]
    assert "innovation in mining operations" in evid_map["Innovation"]

    # ---------- 6) 检查 subthemes.csv 汇总 ----------
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

    # 应该有两个子主题：Safety 和 Innovation
    assert set(df_sum["sub_theme"]) == {"Safety", "Innovation"}

    # 每个子主题的 count 都是 1
    counts = dict(zip(df_sum["sub_theme"], df_sum["count"]))
    assert counts["Safety"] == 1
    assert counts["Innovation"] == 1

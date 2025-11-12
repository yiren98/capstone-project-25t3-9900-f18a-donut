# -*- coding: utf-8 -*-
"""
从原始 comments.csv 精确清洗为 8 列：
ID, Tag, Author, Content, Score, Time, Depth, Parent_ID

映射：
 Tag     <- Submission_ID
 ID      <- ID
 Author  <- Author
 Content <- Body
 Score   <- Score
 Time    <- Created_Time
 Depth   <- Depth
 Parent_ID <- Parent_ID
"""

import csv
from pathlib import Path

SRC = Path("crawler/reddit-crawler-master/comments.csv")                  # 原始文件
OUT = Path("crawler/reddit-crawler-master/comments_cleaned_keep8.csv")    # 输出文件

required = [
    "ID", "Submission_ID", "Author", "Body", "Score",
    "Created_Time", "Depth", "Parent_ID"
]

with SRC.open("r", encoding="utf-8-sig", newline="") as f_in:
    reader = csv.DictReader(f_in)
    # 标题做 strip 以防不可见空格
    hdr = [h.strip() for h in (reader.fieldnames or [])]
    miss = [c for c in required if c not in hdr]
    if miss:
        raise SystemExit(f"原始 comments.csv 缺少列：{miss}\n实际列：{hdr}")

    with OUT.open("w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(
            f_out,
            fieldnames=["ID","Tag","Author","Content","Score","Time","Depth","Parent_ID"],
            quoting=csv.QUOTE_ALL
        )
        writer.writeheader()

        n = 0
        for row in reader:
            row = { (k.strip() if k else k): v for k, v in row.items() }
            writer.writerow({
                "ID":        row.get("ID",""),
                "Tag":       row.get("Submission_ID",""),
                "Author":    row.get("Author",""),
                "Content":   row.get("Body",""),
                "Score":     row.get("Score",""),
                "Time":      row.get("Created_Time",""),
                "Depth":     row.get("Depth",""),
                "Parent_ID": row.get("Parent_ID",""),
            })
            n += 1

print(f"✅ 已生成：{OUT}（{n} 行）")
print("✅ 列顺序：ID, Tag, Author, Content, Score, Time, Depth, Parent_ID")

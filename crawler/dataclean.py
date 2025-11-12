# -*- coding: utf-8 -*-
import pandas as pd
import re
import csv

SUB = "crawler/reddit-crawler-master/submissions_cleaned.csv"
COM = "crawler/reddit-crawler-master/comments_cleaned.csv"

# 读取（保持字符串）
sub = pd.read_csv(SUB, dtype=str, keep_default_na=False, encoding="utf-8-sig")
com = pd.read_csv(COM, dtype=str, keep_default_na=False, encoding="utf-8-sig")

# 4 个精确关键词（区分大小写，按你要求）
pattern = re.compile(r"(Rio Tinto|RIO TINTO|rio tinto|Rio tinto)")

# 1) 在 posts 里按 Text/Content 筛
for col in ["Text", "Content"]:
    if col not in sub.columns:  # 兜底
        sub[col] = ""
hit = sub["Text"].str.contains(pattern, na=False) | sub["Content"].str.contains(pattern, na=False)
sub_sel = sub[hit].copy()

# 2) 用 Tag 关联评论（comments.Tag ↔ submissions.Tag）
post_tags = set(sub_sel["Tag"])
com_sel  = com[com["Tag"].isin(post_tags)].copy()

# 3) （可选）拼接评论+所属帖子信息，便于分析
merged = com_sel.merge(
    sub_sel, on="Tag", how="left", suffixes=("_comment", "_post")
)

# 4) 导出（不改列名与顺序）
sub_out = "crawler/reddit-crawler-master/submissions_rio.csv"
com_out = "crawler/reddit-crawler-master/comments_rio.csv"
mrg_out = "crawler/reddit-crawler-master/comments_with_posts_rio.csv"

sub_sel.to_csv(sub_out, index=False, encoding="utf-8", quoting=csv.QUOTE_ALL)
com_sel.to_csv(com_out, index=False, encoding="utf-8", quoting=csv.QUOTE_ALL)
merged.to_csv(mrg_out, index=False, encoding="utf-8", quoting=csv.QUOTE_ALL)

print(f"posts matched:  {len(sub_sel)} -> {sub_out}")
print(f"comments kept:  {len(com_sel)} -> {com_out}")
print(f"merged rows:    {len(merged)} -> {mrg_out}")

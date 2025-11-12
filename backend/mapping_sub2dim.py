# 3_mapping_sub2dim.py
# Map subthemes → representative → Dimensions 
# Usage: python mapping_sub2dim.py path/comments.csv path/dimension_clusters.json
# Input: 
# 1.path/comments.csv [ID,text,subthemes,subs_sentiment,confidence,subs_evidences]
# 2.dimension_clusters.json { "Dimension": [ {"representative": "...", "members": ["..."] }, ... ], ... }
# - For each row:
#     * Map every original subtheme to its representative (by member -> representative)
#     * New subthemes = unique representatives (order preserved; keep unmapped as-is)
#     * Dimensions = unique dimensions of those representatives (order preserved)
#     * subs_sentiment: keys become representatives; value = majority of original labels
#                      (tie order: negative > positive > neutral)
#     * subs_evidences: first non-empty evidence per representative wins
# Output: path/comments.csv [ID,text,subthemes,subs_sentiment,confidence,subs_evidences,Dimensions]

import sys, json
from pathlib import Path
import pandas as pd

# fixed columns we need
REQUIRED = ["ID", "text", "subthemes", "subs_sentiment", "confidence", "subs_evidences"]

# tie priority: negative > positive > neutral
SENT_PRI = {"negative": 2, "positive": 1, "neutral": 0}

def load_clusters(json_path: Path):
    """Build two maps:
       member_map: member or representative -> (dimension, representative)
       rep_to_dim: representative -> dimension
    """
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    member_map, rep_to_dim = {}, {}
    for dim, blocks in data.items():
        if isinstance(blocks, dict):
            blocks = [blocks]
        for b in blocks:
            rep = b.get("representative")
            mem = b.get("members", []) or []
            if not rep:
                continue
            rep_to_dim[rep] = dim
            member_map[rep] = (dim, rep)
            for m in mem:
                if m:
                    member_map[m] = (dim, rep)
    return member_map, rep_to_dim

def split_pipes(s: str):
    """Split 'a|b|c' -> ['a','b','c'] (strip spaces)."""
    if not isinstance(s, str) or not s.strip():
        return []
    return [x.strip() for x in s.split("|") if x.strip()]

def parse_dict(s: str):
    """Safe parse dict from string; return {} if bad."""
    if not isinstance(s, str) or not s.strip():
        return {}
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}

def uniq_keep_order(seq):
    """Unique while keeping order."""
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def majority(labels):
    """Majority with tie order: negative > positive > neutral."""
    cnt = {}
    for lb in labels:
        k = (lb or "").strip().lower()
        if k:
            cnt[k] = cnt.get(k, 0) + 1
    if not cnt:
        return "neutral"
    top = max(cnt.values())
    cands = [k for k, v in cnt.items() if v == top]
    cands.sort(key=lambda x: SENT_PRI.get(x, -1), reverse=True)
    return cands[0]

def process_row(row, member_map, rep_to_dim):
    # read original fields
    raw_subs = split_pipes(row.get("subthemes"))
    subs_sent = parse_dict(row.get("subs_sentiment"))
    subs_evi  = parse_dict(row.get("subs_evidences"))

    reps = []                  # representatives list
    rep_sent_bucket = {}       # rep -> [labels]
    rep_evi = {}               # rep -> evidence (first non-empty)

    for st in raw_subs:
        hit = member_map.get(st)
        if hit is None:
            # allow direct representative name
            if st in rep_to_dim:
                rep = st
                reps.append(rep)
                if st in subs_sent:
                    rep_sent_bucket.setdefault(rep, []).append(str(subs_sent[st]))
                if st in subs_evi:
                    val = str(subs_evi[st]).strip()
                    if val and rep not in rep_evi:
                        rep_evi[rep] = val
            else:
                # keep unmapped as-is
                reps.append(st)
                if st in subs_sent:
                    rep_sent_bucket.setdefault(st, []).append(str(subs_sent[st]))
                if st in subs_evi:
                    val = str(subs_evi[st]).strip()
                    if val and st not in rep_evi:
                        rep_evi[st] = val
            continue

        dim, rep = hit
        reps.append(rep)
        if st in subs_sent:
            rep_sent_bucket.setdefault(rep, []).append(str(subs_sent[st]))
        if st in subs_evi and rep not in rep_evi:
            val = str(subs_evi[st]).strip()
            if val:
                rep_evi[rep] = val

    reps = uniq_keep_order(reps)

    # Dimensions from representatives
    dims = uniq_keep_order([rep_to_dim[r] for r in reps if r in rep_to_dim])

    # collapse sentiment per representative
    new_sent = {r: majority(rep_sent_bucket.get(r, [])) for r in reps}

    # evidences: only reps that have evidence
    new_evi = {r: rep_evi[r] for r in reps if r in rep_evi}

    # write back to row
    row["subthemes"] = "|".join(reps) if reps else ""
    row["Dimensions"] = "|".join(dims) if dims else ""
    row["subs_sentiment"] = json.dumps(new_sent, ensure_ascii=False)
    row["subs_evidences"] = json.dumps(new_evi, ensure_ascii=False)
    return row

def main():
    if len(sys.argv) < 3:
        print("Usage: python mapping_sub2dim.py <comments.csv> <dimension_clusters.json>")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    json_path = Path(sys.argv[2])

    if not csv_path.exists():
        print(f"[fatal] CSV not found: {csv_path}")
        sys.exit(2)
    if not json_path.exists():
        print(f"[fatal] JSON not found: {json_path}")
        sys.exit(2)

    member_map, rep_to_dim = load_clusters(json_path)

    # read CSV; strip BOM from headers if any
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df = df.rename(columns={c: c.lstrip("\ufeff") for c in df.columns})

    # schema check (fixed format only)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing columns: {missing}. Expected {REQUIRED}")

    # process rows
    df = df.apply(lambda r: process_row(r, member_map, rep_to_dim), axis=1)

    # write back to same file (no backup)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"[ok] updated: {csv_path}")

if __name__ == "__main__":
    main()

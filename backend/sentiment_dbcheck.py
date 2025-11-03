# 1_sentiment_dbcheck.py
# Re-evaluate subthemes whose sentiment == "neutral"
# Usage: python sentiment_dbcheck.py path/comments.csv
# Input: path/comments.csv [ID,text,subthemes,subs_sentiment,confidence,subs_evidences]
# Double check sentiment using three models (majority voting):
# 1. VADER (NLTK)
# 2. Twitter-RoBERTa (CardiffNLP)
# 3. SST-2 DistilBERT (HuggingFace)
# Confidence = max(old_conf, mean(updated_subtheme_conf)).
# Output: path/comments.csv [ID,text,subthemes,subs_sentiment,confidence,subs_evidences]

import os, sys, json, math, nltk, torch
import numpy as np
import pandas as pd
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from nltk.sentiment import SentimentIntensityAnalyzer

# ------------------------- CLI & Paths -------------------------
if len(sys.argv) < 2:
    print("Usage: python sentiment_neutral_fix.py <comments.csv>")
    sys.exit(1)

CSV_IN = Path(sys.argv[1]).resolve()
if not CSV_IN.exists():
    print(f"Error: CSV file not found: {CSV_IN}")
    sys.exit(1)

ROOT_DIR   = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT_DIR / "backend" / "models"
NLTK_DIR   = MODELS_DIR / "nltk_data"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
NLTK_DIR.mkdir(parents=True, exist_ok=True)
nltk.data.path.insert(0, str(NLTK_DIR))

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

REQUIRED_COLS = ["ID", "text", "subthemes", "subs_sentiment", "confidence", "subs_evidences"]

# ------------------------- Utils -------------------------
def round_conf(v: float, ndigits=3) -> float:
    v = max(0.0, min(1.0, float(v)))
    return round(v, ndigits)

def safe_json_loads(s, default):
    try:
        if s is None or (isinstance(s, float) and math.isnan(s)):
            return default
        return json.loads(str(s))
    except Exception:
        return default

def check_columns(df: pd.DataFrame):
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

# ------------------------- 1) VADER -------------------------
def ensure_vader():
    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        nltk.download("vader_lexicon", download_dir=str(NLTK_DIR))

ensure_vader()
_VADER = SentimentIntensityAnalyzer()

def pred_vader(texts):
    labels, pos_probs = [], []
    for t in texts:
        t = t or ""
        s = _VADER.polarity_scores(t)
        comp = float(s.get("compound", 0.0))
        pos_p = (comp + 1.0) / 2.0  # [-1,1] -> [0,1]
        lab = "positive" if comp >= 0 else "negative"
        labels.append(lab)
        pos_probs.append(pos_p)
    return labels, pos_probs

# ------------------------- 2) Twitter-RoBERTa -------------------------
_RO_REPO = "cardiffnlp/twitter-roberta-base-sentiment-latest"
_ro_tok  = AutoTokenizer.from_pretrained(_RO_REPO, cache_dir=str(MODELS_DIR))
_ro_mdl  = AutoModelForSequenceClassification.from_pretrained(_RO_REPO, cache_dir=str(MODELS_DIR)).to(DEVICE).eval()
_ro_id2label = _ro_mdl.config.id2label
_ro_pos_id = next(i for i, n in _ro_id2label.items() if n.lower().startswith("pos"))
_ro_neg_id = next(i for i, n in _ro_id2label.items() if n.lower().startswith("neg"))

def pred_roberta(texts, max_len=256, bs=64):
    labels, pos_probs = [], []
    for i in range(0, len(texts), bs):
        batch = [x if isinstance(x, str) else "" for x in texts[i:i+bs]]
        enc = _ro_tok(batch, return_tensors="pt", padding=True, truncation=True, max_length=max_len).to(DEVICE)
        with torch.no_grad():
            prob = torch.softmax(_ro_mdl(**enc).logits, dim=-1).cpu().numpy()
        for j in range(len(batch)):
            p_pos, p_neg = float(prob[j, _ro_pos_id]), float(prob[j, _ro_neg_id])
            labels.append("positive" if p_pos >= p_neg else "negative")
            pos_probs.append(p_pos)
    return labels, pos_probs

# ------------------------- 3) SST-2 DistilBERT -------------------------
_SST_REPO = "distilbert-base-uncased-finetuned-sst-2-english"
_sst_tok  = AutoTokenizer.from_pretrained(_SST_REPO, cache_dir=str(MODELS_DIR))
_sst_mdl  = AutoModelForSequenceClassification.from_pretrained(_SST_REPO, cache_dir=str(MODELS_DIR)).to(DEVICE).eval()

def pred_sst2(texts, max_len=256, bs=64):
    labels, pos_probs = [], []
    for i in range(0, len(texts), bs):
        batch = [x if isinstance(x, str) else "" for x in texts[i:i+bs]]
        enc = _sst_tok(batch, return_tensors="pt", padding=True, truncation=True, max_length=max_len).to(DEVICE)
        with torch.no_grad():
            prob = torch.softmax(_sst_mdl(**enc).logits, dim=-1).cpu().numpy()
        for j in range(len(batch)):
            pos_p = float(prob[j, 1])  # id=1 is "POSITIVE"
            lab = "positive" if np.argmax(prob[j]) == 1 else "negative"
            labels.append(lab)
            pos_probs.append(pos_p)
    return labels, pos_probs

# ------------------------- Voting (binary only) -------------------------
def majority_vote(ro_lab, ro_p, sst_lab, sst_p, vd_lab, vd_p):
    """
    Binary voting (positive/negative).
    Confidence = 0.5 * vote_strength + 0.5 * prob_strength
      where vote_strength = max(#pos,#neg)/3
            prob_strength = max(mean_pos, 1-mean_pos)
    """
    votes = [ro_lab, sst_lab, vd_lab]
    pos_votes, neg_votes = votes.count("positive"), votes.count("negative")

    if pos_votes > neg_votes:
        final_lab = "positive"
    elif neg_votes > pos_votes:
        final_lab = "negative"
    else:
        # tie-break preference order (SST > RoBERTa > VADER)
        final_lab = sst_lab or ro_lab or vd_lab or "negative"

    mean_pos = (ro_p + sst_p + vd_p) / 3.0
    vote_strength = max(pos_votes, neg_votes) / 3.0
    prob_strength = max(mean_pos, 1.0 - mean_pos)
    conf = round_conf((vote_strength + prob_strength) / 2.0)
    return final_lab, conf

def infer_binary_sentiment(texts):
    """Run three models once for a list of texts, return (labels, confs)."""
    ro_lab, ro_p = pred_roberta(texts)
    sst_lab, sst_p = pred_sst2(texts)
    vd_lab, vd_p = pred_vader(texts)

    outs_lab, outs_conf = [], []
    for i in range(len(texts)):
        lab, conf = majority_vote(ro_lab[i], ro_p[i], sst_lab[i], sst_p[i], vd_lab[i], vd_p[i])
        outs_lab.append(lab); outs_conf.append(conf)
    return outs_lab, outs_conf

# ------------------------- Main -------------------------
def main():
    # 1) Read CSV (no extra columns; we will overwrite in-place)
    df = pd.read_csv(CSV_IN, encoding="utf-8")
    check_columns(df)
    df = df.fillna("")
    n = len(df)
    if n == 0:
        print("[Info] Empty file; nothing to do.")
        return

    # 2) Collect neutral targets (per-row per-subtheme)
    #    Build a batch of texts to evaluate (evidence > text fallback)
    eval_items = []   # list of (row_idx, subtheme_name, eval_text)
    for i, row in df.iterrows():
        subs_map  = safe_json_loads(row.get("subs_sentiment", ""), {})
        evid_map  = safe_json_loads(row.get("subs_evidences", ""), {})
        if not isinstance(subs_map, dict) or len(subs_map) == 0:
            continue
        for sub_name, att in subs_map.items():
            if str(att).lower() == "neutral":  # only re-check neutral
                ev = evid_map.get(sub_name, "")
                txt_for_eval = ev if isinstance(ev, str) and len(ev.strip()) > 0 else (row.get("text", "") or "")
                eval_items.append((i, sub_name, txt_for_eval))

    if not eval_items:
        print("[Info] No 'neutral' subthemes found. Nothing to update.")
        return

    # 3) Run models in batch on the evaluation texts
    texts = [t for (_, _, t) in eval_items]
    labs, confs = infer_binary_sentiment(texts)

    # 4) Write back into subs_sentiment (JSON string). Update row 'confidence'.
    #    row confidence := max(old_conf, mean(updated_conf_in_this_row)) [if any updated]
    per_row_new_confs = {}  # row_idx -> [conf, ...]
    for (i, sub_name, _), lab, cf in zip(eval_items, labs, confs):
        # parse current JSON again (row may appear multiple times)
        subs_map = safe_json_loads(df.at[i, "subs_sentiment"], {})
        # force binary
        subs_map[sub_name] = "positive" if lab == "positive" else "negative"
        df.at[i, "subs_sentiment"] = json.dumps(subs_map, ensure_ascii=False)
        per_row_new_confs.setdefault(i, []).append(cf)

    # 5) Update row-level confidence conservatively
    for i, conf_list in per_row_new_confs.items():
        try:
            old_conf = float(df.at[i, "confidence"])
        except Exception:
            old_conf = 0.0
        mean_new = float(np.mean(conf_list)) if conf_list else 0.0
        df.at[i, "confidence"] = round_conf(max(old_conf, mean_new))

    # 6) Overwrite original file (no extra columns)
    df = df[REQUIRED_COLS]  # enforce exact columns order
    df.to_csv(CSV_IN, index=False, encoding="utf-8")
    print(f"[Done] Updated {CSV_IN}")
    print(f"  Re-evaluated neutral subthemes: {len(eval_items)}")
    pos_ct = sum(1 for _, _, _ in eval_items if labs.pop(0) if False)  # (just to show structure; not used)
    return

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[Error] {e}")
        sys.exit(1)

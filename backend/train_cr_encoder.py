# 1.5_train_cr_encoder.py
# Train a binary Cross-Encoder for subtheme→dimension mapping, then evaluate.
# Usage: python train_cr_encoder.py path/subthemes.csv path/gold.csv
# Inputs: 
# subthemes.csv [sub_theme,count,attitudes_raw,att_pos,att_neg,att_neu,avg_conf,example,ids]
# gold.csv must contain columns "subthemes", "dimensions" (multi-label separated by "|")
# Outputs:
# Fine-tuned CE file: models/ce_ft/
# Summary metrics JSON: ROOT_DIR/data/processed/mapping_eval_summary.json

from pathlib import Path
import os, re, json, difflib, random, shutil, sys
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from sentence_transformers import SentenceTransformer, util as st_util, CrossEncoder, InputExample

# ==================== Device & CLI ====================
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print("DEVICE:", DEVICE)

if len(sys.argv) < 3:
    raise SystemExit("Usage: python train_ce_only.py SUBTHEMES_CSV GOLD_CSV")

CSV_SUBTHEMES = Path(sys.argv[1]).resolve()
CSV_GOLD      = Path(sys.argv[2]).resolve()

# Project root = folder of this file
ROOT_DIR   = Path(__file__).resolve().parents[0]
# Final model will be saved here
MODELS_DIR = ROOT_DIR / "models"
CE_FT_DIR  = MODELS_DIR / "ce_ft"
CE_FT_DIR.mkdir(parents=True, exist_ok=True)

# Metrics summary output
OUT_SUMMARY = ROOT_DIR / "data" / "processed" / "mapping_eval_summary.json"
OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)

# ==================== Reproducibility ====================
SEED = 42
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)

# ==================== Dimension Bank ====================
# Keep this list stable. CE sees (subtheme, template(dim+definition))
# so consistent definitions matter.
DIM_DESC = {
  "Agility": "Ability to adapt quickly, learn rapidly, and respond to changing challenges.",
  "Collaboration": "Working effectively with others across teams to achieve shared goals.",
  "Customer Orientation": "Prioritizing customer needs, satisfaction, and long-term relationships.",
  "Diversity": "Valuing and leveraging differences in background, identity, and perspectives.",
  "Execution": "Consistently delivering goals with discipline, efficiency, and accountability.",
  "Innovation": "Encouraging new ideas and implementing improvements to products or processes.",
  "Integrity": "Acting ethically, honestly, and upholding strong moral principles.",
  "Performance": "Rewarding high standards, strong results, and achievement.",
  "Respect": "Ensuring employees feel valued, treated fairly, and recognized for contributions.",
  "Learning": "Continuously gaining knowledge, sharing insights, and applying learning to improve.",
  "Accountability": "Taking ownership of outcomes, admitting mistakes, and acting transparently.",
  "Well-being": "Prioritizing mental, physical, and emotional health for sustainable performance.",
  "Ethical Responsibility": "Embedding ethics, environmental stewardship, and positive social impact into operations.",
  "Digital Empowerment": "Using technology and data to empower employees and process automation, digital fluency, smart decision-making."
}
DIM_KEYS  = list(DIM_DESC.keys())
DESC_LIST = [f"{k}. {v}" for k, v in DIM_DESC.items()]

# ==================== Bi-encoders for Candidate Recall ====================
# Purpose:
#   - Fast semantic retrieval vs. each dimension description.
#   - We fuse two encoders (BGE + SimCSE) to reduce variance.
#   - Their cosine similarities guide candidate filtering before CE rerank.
bi1 = SentenceTransformer("BAAI/bge-base-en-v1.5", device=DEVICE)
bi2 = SentenceTransformer("princeton-nlp/sup-simcse-roberta-base", device=DEVICE)

def encode1(txts):
    return bi1.encode(txts, convert_to_tensor=True, normalize_embeddings=True, batch_size=64)

def encode2(txts):
    return bi2.encode(txts, convert_to_tensor=True, normalize_embeddings=True, batch_size=64)

with torch.no_grad():
    dim_emb1 = encode1(DESC_LIST).to(DEVICE)
    dim_emb2 = encode2(DESC_LIST).to(DEVICE)

# ==================== Cross-Encoder Base & Templates ====================
# CE is binary: "is this subtheme about this dimension?" → yes/no
CE_BASE   = "cross-encoder/ms-marco-MiniLM-L-6-v2"
CE_EPOCHS = 3
CE_BATCH  = 16
CE_LR     = 2e-5
CE_WARMUP = 0.1
USE_AMP   = True

# Short, generic templates to pair (subtheme, dimension+definition).
# Goal: give CE consistent cues without leaking answer words.
CE_TEMPLATES = [
    "This text is about {}. Definition: {}",
    "The topic involves {}. {}",
    "{}: {}. This text relates to this concept."
]

def cr_pos_prob(cr, pairs):
    """
    Predict P(positive) for (subtheme, dimension-template) pairs.
    Returns the probability of the positive class for each pair.
    """
    out = cr.predict(pairs, apply_softmax=True)  # [N, 2]
    if isinstance(out, torch.Tensor):
        out = out.detach().cpu().numpy()
    if out.ndim == 2 and out.shape[1] == 2:
        return out[:, 1]
    return out.squeeze()

# ==================== Text Canonicalization ====================
# Keep names stable: unify minor wording differences to DIM_KEYS.
def _norm_token(s: str) -> str:
    s = str(s).strip().lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

CANON_NORM = {_norm_token(k): k for k in DIM_KEYS}
MANUAL_FIX = {
    "wellbeing":"Well-being","well being":"Well-being","work life balance":"Well-being",
    "customer focus":"Customer Orientation","customer focused":"Customer Orientation","client centric":"Customer Orientation","user focus":"Customer Orientation",
    "esg":"Ethical Responsibility","sustainability":"Ethical Responsibility","csr":"Ethical Responsibility","environmental":"Ethical Responsibility",
    "safety":"Well-being","health":"Well-being",
    "transparency":"Accountability","gov relations":"Accountability","government relations":"Accountability",
    "data driven":"Digital Empowerment","digital tools":"Digital Empowerment","automation":"Digital Empowerment",
    "innovation":"Innovation",
}

def canonize_dim(x: str) -> str | None:
    """
    Map raw dimension token to one of DIM_KEYS.
    - Applies manual shortcuts first (MANUAL_FIX).
    - Then fuzzy match on normalized forms.
    """
    n = _norm_token(x)
    if n in MANUAL_FIX: return MANUAL_FIX[n]
    if n in CANON_NORM: return CANON_NORM[n]
    cand = difflib.get_close_matches(n, list(CANON_NORM.keys()), n=1, cutoff=0.88)
    return CANON_NORM[cand[0]] if cand else None

def split_dims_pipe(s: str):
    """
    Parse multi-label field separated by "|".
    Apply canonicalization + dedup while preserving order.
    """
    if s is None or str(s).strip()=="":
        return []
    parts = [p.strip() for p in str(s).split("|") if p.strip()]
    out, seen = [], set()
    for p in parts:
        c = canonize_dim(p)
        if c and c not in seen:
            seen.add(c); out.append(c)
    return out

# ==================== Build CE Training Data (from GOLD) ====================
# Strategy:
#   - Each subtheme has a gold set of dimensions.
#   - Positives: (subtheme, each gold dimension) with 1-2 templates.
#   - Easy negatives: random dimensions not in gold set.
#   - Hard negatives: top-K nearest (via bi-encoder) excluding gold set.
HOLDOUT_RATIO = 0.20
NEG_EASY_PER_POS  = 3
NEG_HARD_PER_POS  = 3
HARD_K_FROM_BI    = 10

def hard_negatives_for_text(text: str, gold_set: set, k_from_bi=HARD_K_FROM_BI, k_pick=NEG_HARD_PER_POS):
    with torch.no_grad():
        x1 = encode1([text]).to(DEVICE)
        x2 = encode2([text]).to(DEVICE)
        s1 = st_util.cos_sim(x1, dim_emb1).squeeze(0).cpu().numpy()
        s2 = st_util.cos_sim(x2, dim_emb2).squeeze(0).cpu().numpy()
    # Cosine → [0,1] (optional; keeps fusion consistent with downstream logic)
    s1 = (s1 + 1.0) / 2.0
    s2 = (s2 + 1.0) / 2.0
    sims = (s1 + s2) / 2.0
    idx = np.argsort(-sims)[:k_from_bi]
    cands = [DIM_KEYS[i] for i in idx if DIM_KEYS[i] not in gold_set]
    random.shuffle(cands)
    return cands[:k_pick]

def build_train_val_from_gold(gold_csv: Path):
    """
    Load GOLD_CSV, canonicalize labels, aggregate to unique (subtheme → set(dimensions)),
    and split into train/val by subtheme to avoid leakage.
    """
    df = pd.read_csv(gold_csv)
    df.columns = [c.strip().lower() for c in df.columns]

    need = {"subthemes","dimensions"}
    missing = need - set(df.columns)
    if missing:
        raise RuntimeError(f"[GOLD] missing columns: {missing}; expected: subthemes, dimensions")

    df["subthemes"]  = df["subthemes"].astype(str).str.strip()
    df["dimensions"] = df["dimensions"].astype(str).str.strip()

    tmp = df.assign(dim_list=df["dimensions"].apply(split_dims_pipe))
    tmp = tmp.explode("dim_list")
    tmp = tmp[tmp["dim_list"].notna() & (tmp["dim_list"] != "")]
    gold_agg = (
        tmp.groupby("subthemes", as_index=False)["dim_list"]
           .agg(lambda x: sorted(set(x)))
           .rename(columns={"dim_list":"gold_set"})
    )
    gold_agg = gold_agg[gold_agg["gold_set"].map(len) > 0].reset_index(drop=True)

    subs = gold_agg["subthemes"].unique().tolist()
    random.shuffle(subs)
    n_hold = int(len(subs) * HOLDOUT_RATIO)
    val_subs = set(subs[:n_hold]) if n_hold > 0 else set()

    df_train = gold_agg[~gold_agg["subthemes"].isin(val_subs)].copy()
    df_val   = gold_agg[ gold_agg["subthemes"].isin(val_subs)].copy()
    return df_train, df_val

def build_ce_examples(df_part: pd.DataFrame):
    """
    Turn aggregated gold into CE InputExamples.
    For each subtheme:
      - positives: (subtheme, template(dim+desc)) for each gold dim (2 templates)
      - easy negatives: random dims not in gold (1 template)
      - hard negatives: bi-encoder near-misses not in gold (2 templates)
    """
    exs = []
    all_dims = set(DIM_KEYS)
    for _, r in df_part.iterrows():
        st = r["subthemes"]
        gs = set(r["gold_set"])

        # positives
        for d in gs:
            for t in CE_TEMPLATES[:2]:
                exs.append(InputExample(texts=[st, t.format(d, DIM_DESC[d])], label=1))

        # easy negatives
        neg_easy_pool = list(all_dims - gs)
        random.shuffle(neg_easy_pool)
        for d in neg_easy_pool[:NEG_EASY_PER_POS]:
            for t in CE_TEMPLATES[:1]:
                exs.append(InputExample(texts=[st, t.format(d, DIM_DESC[d])], label=0))

        # hard negatives
        hn = hard_negatives_for_text(st, gs)
        for d in hn:
            for t in CE_TEMPLATES[:2]:
                exs.append(InputExample(texts=[st, t.format(d, DIM_DESC[d])], label=0))
    random.shuffle(exs)
    return exs

# ==================== Train CE ====================
def train_cross_encoder(df_train: pd.DataFrame, df_val: pd.DataFrame):
    """
    Fine-tune CE on generated positives/negatives.
    Saves to CE_FT_DIR and reloads to ensure a clean on-disk model.
    """
    train_ex = build_ce_examples(df_train)
    print(f"[CE] train examples: {len(train_ex)}")
    val_ex = build_ce_examples(df_val) if len(df_val) > 0 else None
    if val_ex is not None:
        print(f"[CE] val examples: {len(val_ex)}")

    if CE_FT_DIR.exists():
        shutil.rmtree(CE_FT_DIR)
    CE_FT_DIR.mkdir(parents=True, exist_ok=True)

    cr = CrossEncoder(CE_BASE, device=DEVICE)
    dl_train = DataLoader(train_ex, shuffle=True, batch_size=CE_BATCH)
    cr.fit(
        train_dataloader=dl_train,
        epochs=CE_EPOCHS,
        warmup_steps=int(len(dl_train) * CE_EPOCHS * CE_WARMUP),
        optimizer_params={'lr': CE_LR},
        use_amp=USE_AMP,
        output_path=str(CE_FT_DIR)
    )
    cr.save(str(CE_FT_DIR))
    print(f"[CE] fine-tuned & saved → {CE_FT_DIR}")
    return CrossEncoder(str(CE_FT_DIR), device=DEVICE)

# ==================== Inference (Multi-label) ====================
# Bi-encoder + CE fusion:
#   - bi-encoder: candidate shortlist by cosine similarity to each dimension
#   - CE: binary relevance scoring with templates
#   - final: keep up to MAX_DIM that pass adaptive thresholds
BI_TOP_M       = 6
BI_SIM_TH      = 0.55
CR_ENT_TH_BASE = 0.85
ADAPT_DELTA    = 0.04
ALPHA          = 0.85
MAX_DIM        = 3

def dynamic_threshold(sims_row: np.ndarray) -> float:
    """
    Lower CE gate a bit if overall similarity is weak, keep stricter when strong.
    """
    mean_sim = float(np.mean(sims_row))
    return CR_ENT_TH_BASE - (ADAPT_DELTA if mean_sim < 0.45 else 0.0)

def map_one_multi(text: str, cr: CrossEncoder):
    """
    Multi-label mapping for a single subtheme:
      1) shortlist via bi-encoder similarity
      2) score with CE across templates
      3) keep candidates passing CE gate and similarity floor
      4) return up to MAX_DIM by fused score
    """
    with torch.no_grad():
        x1 = encode1([text]).to(DEVICE)
        x2 = encode2([text]).to(DEVICE)
        s1 = st_util.cos_sim(x1, dim_emb1).squeeze(0).cpu().numpy()
        s2 = st_util.cos_sim(x2, dim_emb2).squeeze(0).cpu().numpy()
    s1 = (s1 + 1.0) / 2.0
    s2 = (s2 + 1.0) / 2.0
    sims = (s1 + s2) / 2.0

    over  = np.where(sims >= BI_SIM_TH)[0].tolist()
    topm  = np.argsort(-sims)[:BI_TOP_M].tolist()
    cand_idx = set(over + topm)
    if not cand_idx:
        cand_idx = set(topm)
    cand_idx = sorted(cand_idx, key=lambda k: -sims[k])
    cand = [DIM_KEYS[i] for i in cand_idx]

    pairs = []
    for d in cand:
        desc = DIM_DESC[d]
        for t in CE_TEMPLATES:
            pairs.append((text, t.format(d, desc)))
    probs_all = cr_pos_prob(cr, pairs)
    probs = np.max(probs_all.reshape(len(cand), -1), axis=1)

    base_cr = dynamic_threshold(sims[cand_idx])
    keep = []
    for j, i in enumerate(cand_idx):
        d   = cand[j]
        th  = base_cr
        if (probs[j] >= th) and (sims[i] >= BI_SIM_TH * 0.8):
            fused = ALPHA*probs[j] + (1.0-ALPHA)*sims[i]
            keep.append((d, float(probs[j]), float(sims[i]), float(fused)))

    if not keep:
        # Fallback: return best CE candidate to avoid empty label set
        j = int(np.argmax(probs))
        return [cand[j]]

    keep.sort(key=lambda t: -t[3])
    if MAX_DIM and MAX_DIM > 0:
        keep = keep[:MAX_DIM]
    return [d for d, _, _, _ in keep]

# ==================== Multi-label Evaluation ====================
def evaluate_multilabel(gold_sets, pred_sets):
    """
    Report:
      - top1_accuracy: accuracy of the first label (sanity check)
      - example-based precision/recall/F1 (averaged per example)
      - micro/macro precision/recall/F1 across labels
    """
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support
    from sklearn.preprocessing import MultiLabelBinarizer

    def first_or_none(lst):
        return lst[0] if isinstance(lst, list) and len(lst)>0 else "__NONE__"

    # Top-1 accuracy (optional sanity check)
    golds_top1 = [first_or_none(x) for x in gold_sets]
    preds_top1 = [first_or_none(x) for x in pred_sets]
    mask = [g!="__NONE__" for g in golds_top1]
    golds_top1 = [g for g,m in zip(golds_top1, mask) if m]
    preds_top1 = [p for p,m in zip(preds_top1, mask) if m]
    top1_acc = accuracy_score(golds_top1, preds_top1) if len(golds_top1) else 0.0

    # Example-based metrics
    def example_prf(golds, preds):
        P=R=F=0.0; n=len(golds)
        for y, yhat in zip(golds, preds):
            y=set(y); yhat=set(yhat)
            inter = len(y & yhat)
            p = inter / len(yhat) if len(yhat)>0 else 0.0
            r = inter / len(y)    if len(y)>0    else 0.0
            f = (2*p*r/(p+r)) if (p+r)>0 else 0.0
            P += p; R += r; F += f
        return (P/n if n else 0.0, R/n if n else 0.0, F/n if n else 0.0)

    ex_p, ex_r, ex_f = example_prf(gold_sets, pred_sets)

    # Micro/Macro across labels
    all_labels = sorted(set(sum(gold_sets, [])) | set(sum(pred_sets, [])))
    from sklearn.preprocessing import MultiLabelBinarizer
    mlb = MultiLabelBinarizer(classes=all_labels)
    Y_true = mlb.fit_transform(gold_sets)
    Y_pred = mlb.transform(pred_sets)
    p_micro, r_micro, f1_micro, _ = precision_recall_fscore_support(Y_true, Y_pred, average="micro", zero_division=0)
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(Y_true, Y_pred, average="macro", zero_division=0)

    return {
        "top1_accuracy": float(top1_acc),
        "example_precision": float(ex_p),
        "example_recall": float(ex_r),
        "example_f1": float(ex_f),
        "micro_precision": float(p_micro),
        "micro_recall": float(r_micro),
        "micro_f1": float(f1_micro),
        "macro_precision": float(p_macro),
        "macro_recall": float(r_macro),
        "macro_f1": float(f1_macro),
    }

# ==================== Main ====================
def main():
    # 1) Load GOLD; build train/val splits by subtheme; fine-tune CE.
    df_train, df_val = build_train_val_from_gold(CSV_GOLD)
    print(f"[Split] train: {len(df_train)}  val: {len(df_val)}")
    cr = train_cross_encoder(df_train, df_val)

    # 2) Read subthemes.csv (single required column: sub_theme).
    sub_df = pd.read_csv(CSV_SUBTHEMES, encoding="utf-8-sig")
    if "sub_theme" not in sub_df.columns:
        raise RuntimeError("[SUBTHEMES] required column: sub_theme")

    sub_df["subthemes"] = sub_df["sub_theme"].astype(str).str.strip()
    sub_df = (
        sub_df
        .dropna(subset=["subthemes"])
        .drop_duplicates(subset=["subthemes"])
        .reset_index(drop=True)
    )

    # 3) Multi-label prediction for each subtheme (max 3 labels).
    preds = [map_one_multi(s, cr) for s in sub_df["subthemes"].tolist()]

    # 4) Evaluate on the overlap with GOLD (multi-label metrics only).
    gold_df = pd.read_csv(CSV_GOLD)
    gold_df.columns = [c.strip().lower() for c in gold_df.columns]
    gold_df = gold_df[["subthemes","dimensions"]].copy()
    gold_df["subthemes"] = gold_df["subthemes"].astype(str).str.strip()
    gold_df["gold_set"]  = gold_df["dimensions"].apply(split_dims_pipe)

    sub_tmp = sub_df.copy()
    sub_tmp["pred_set"] = preds

    merged = pd.merge(gold_df[["subthemes","gold_set"]],
                      sub_tmp[["subthemes","pred_set"]],
                      on="subthemes", how="inner")

    gold_sets = merged["gold_set"].tolist()
    pred_sets = merged["pred_set"].tolist()
    metrics = evaluate_multilabel(gold_sets, pred_sets)

    # 5) Coverage on all subthemes.csv rows (did every row get ≥1 label?)
    all_mapped = all(len(x) > 0 for x in preds)
    coverage = sum(1 for x in preds if len(x) > 0) / (len(preds) if len(preds) else 1)

    print("\n== Multi-label Evaluation (on GOLD ∩ SUBTHEMES) ==")
    for k,v in metrics.items():
        print(f"{k}: {v:.4f}")
    print("\n== Coverage on subthemes.csv ==")
    print(f"all_mapped: {all_mapped}  ({coverage*100:.2f}% covered)")

    out_summary = {
        "all_mapped": bool(all_mapped),
        "coverage": float(coverage),
        **metrics
    }
    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        json.dump(out_summary, f, ensure_ascii=False, indent=2)
    print(f"[Summary] saved → {OUT_SUMMARY}")
    print(f"[Model]   saved → {CE_FT_DIR}")

if __name__ == "__main__":
    main()

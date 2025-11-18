# 2_subtheme_classify_cluster.py
# 1.Map subthemes (from subthemes.csv) → Dimensions (BGE+SimCSE retrieval + CE rerank)
# 2.Cluster per dimension to ≤10 reps
# Usage: python subtheme_classify_cluster.py subthemes.csv [out_json]
# Input: subthemes.csv [sub_theme,count,attitudes_raw,att_pos,att_neg,att_neu,avg_conf,example,ids]
# Output default: dimension_clusters.json { "Dimension": [ {"representative": "...", "members": ["..."] }, ... ], ... }

from pathlib import Path
import os, re, json, difflib, random, sys
import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer, util as st_util, CrossEncoder
from sklearn.cluster import KMeans

# ========== Device & Seed ==========
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
SEED = 42
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)

# ========== Fine-tuned CE directory ==========
ROOT_DIR = Path(__file__).resolve().parents[0]
MODELS_DIR = ROOT_DIR / "models"
OUT_DIR = MODELS_DIR / "ce_ft"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ========== Dimensions ==========
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
DESC_LIST = [f"{k}. {DIM_DESC[k]}" for k in DIM_KEYS]

# ========== CE Templates ==========
CE_TEMPLATES = [
    "This text is about {}. Definition: {}",
    "The topic involves {}. {}",
    "{}: {}. This text relates to this concept."
]

# ========== Hyper-params (keep your precision-first logic) ==========
BI_TOP_M       = 6
BI_SIM_TH      = 0.55
CR_ENT_TH_BASE = 0.85
ADAPT_DELTA    = 0.04
MAX_DIM        = 1
ALPHA          = 0.85
MARGIN         = 0.20
PER_LABEL_DELTA = {}  # add per-dimension tweaks here if needed

# ========== Small helpers ==========
def _norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

CANON_NORM = {_norm(k): k for k in DIM_KEYS}

def canonize_dim(x: str) -> str | None:
    n = _norm(x)
    if n in CANON_NORM: return CANON_NORM[n]
    cand = difflib.get_close_matches(n, list(CANON_NORM.keys()), n=1, cutoff=0.88)
    return CANON_NORM[cand[0]] if cand else None

def uniq_keep(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x); out.append(x)
    return out

# alias-based candidate forcing (cheap recall)
ALIAS = {
  "Agility": ["agility","agile","adaptable","adaptability","flexible","flexibility","nimble","rapid learning","change readiness","respond quickly","quick to change"],
  "Collaboration": ["collaboration","collaborate","teamwork","team work","cross functional","partner","partnership","co-create","cooperate","knowledge sharing","break silos"],
  "Customer Orientation": ["customer orientation","customer focused","customer focus","client centric","customer centric","user focus","customer satisfaction","long term customer","voice of customer"],
  "Diversity": ["diversity","diverse","representation","equal opportunity","equity & diversity","demographic diversity","diverse backgrounds"],
  "Execution": ["execution","execute","operational discipline","delivery excellence","follow through","get things done","on time","on budget","delivery focus"],
  "Innovation": ["innovation","innovate","creative","creativity","experimentation","r&d","new ideas","ideation","pilot","prototype","disruptive"],
  "Integrity": ["integrity","honesty","honest","ethical","ethics","trustworthiness","do the right thing","moral principles","code of conduct"],
  "Performance": ["performance","results oriented","high performance","achievement","meet targets","meet goals","kpi","okrs","top performer"],
  "Respect": ["respect","respectful","treated fairly","dignity","civility","valued for contributions","fair treatment"],
  "Learning": ["learning","learn","continuous improvement","kaizen","knowledge sharing","skill growth","upskill","reskill","development mindset","apply lessons"],
  "Accountability": ["accountability","accountable","ownership","own it","responsibility","responsible for outcomes","answerable","transparency","taxation"],
  "Well-being": ["wellbeing","well being","well-being","wellness","mental health","work life balance","work-life balance","stress management","burnout","psychological safety","employee health"],
  "Ethical Responsibility": ["ethics","ethical","ethical responsibility","csr","sustainability","esg","environmental stewardship","social impact","community impact","responsible business","ethics program","compliance program"],
  "Digital Empowerment": ["digital empowerment","technology enablement","digital tools","data driven","data-driven","digitization","digital workplace","collaboration tools","automation","ai tools","tech stack"],
}
_ALIAS_NORM = {k: list({_norm(x) for x in v}) for k, v in ALIAS.items()}

def force_candidates(text_raw: str, cand_idx: set, dim_keys: list) -> set:
    txt = _norm(text_raw)
    for i, name in enumerate(dim_keys):
        name_norms = {_norm(name), _norm(name.replace("-", " "))}
        alias_norms = set(_ALIAS_NORM.get(name, [])) | name_norms
        if any(a and a in txt for a in alias_norms):
            cand_idx.add(i)
    return cand_idx

def dynamic_threshold(sims_row: np.ndarray) -> float:
    mean_sim = float(np.mean(sims_row))
    return CR_ENT_TH_BASE - (ADAPT_DELTA if mean_sim < 0.45 else 0.0)

# ========== Models ==========
def load_models():
    # Bi-encoders
    bi1 = SentenceTransformer("BAAI/bge-base-en-v1.5", device=DEVICE)
    bi2 = SentenceTransformer("princeton-nlp/sup-simcse-roberta-base", device=DEVICE)
    def encode1(txts): return bi1.encode(txts, convert_to_tensor=True, normalize_embeddings=True, batch_size=64)
    def encode2(txts): return bi2.encode(txts, convert_to_tensor=True, normalize_embeddings=True, batch_size=64)
    with torch.no_grad():
        dim_emb1 = encode1(DESC_LIST).to(DEVICE)
        dim_emb2 = encode2(DESC_LIST).to(DEVICE)
    # Cross-encoder (load FT if present)
    CE_BASE = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ft_dir = str(OUT_DIR / "cross_encoder_ft")
    if os.path.isdir(ft_dir) and len(os.listdir(ft_dir)) > 0:
        print("[CE] Loading fine-tuned CE:", ft_dir)
        cr = CrossEncoder(ft_dir, device=DEVICE)
    else:
        print("[CE] Using base CE:", CE_BASE)
        cr = CrossEncoder(CE_BASE, device=DEVICE)
    return encode1, encode2, dim_emb1, dim_emb2, cr

def cr_pos_prob(cr: CrossEncoder, pairs):
    out = cr.predict(pairs, apply_softmax=True)
    if isinstance(out, torch.Tensor):
        out = out.detach().cpu().numpy()
    return out[:, 1] if out.ndim == 2 and out.shape[1] == 2 else out.squeeze()

# ========== Mapping (keep your precision-first flow) ==========
def map_one(text: str, encode1, encode2, dim_emb1, dim_emb2, cr: CrossEncoder):
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
    cand_idx = force_candidates(text, cand_idx, DIM_KEYS)
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
    over_set = set(over + topm)
    alias_only = set(cand_idx) - over_set

    keep = []
    for j, i in enumerate(cand_idx):
        d   = cand[j]
        th  = base_cr
        if i in alias_only:
            th += 0.00
        if d in PER_LABEL_DELTA:
            th += PER_LABEL_DELTA[d]
        if (probs[j] >= th) and (sims[i] >= BI_SIM_TH * 0.8):
            keep.append((d, float(probs[j]), float(sims[i])))

    if not keep:
        j = int(np.argmax(probs))
        return [cand[j]] if len(cand) > 0 else []

    def score(pp, ss): return ALPHA*pp + (1.0-ALPHA)*ss
    keep.sort(key=lambda t: -score(t[1], t[2]))
    keep_dims = [d for d, p, s in keep[:MAX_DIM]] if MAX_DIM > 0 else [d for d, _, _ in keep]
    # canonize
    keep_dims = [canonize_dim(d) or d for d in keep_dims]
    return keep_dims

# ========== Clustering (≤10 reps per dimension) ==========
def embed_texts_for_cluster(texts: list[str], dim_name: str, encode1, encode2, dim_emb1, dim_emb2) -> np.ndarray:
    with torch.no_grad():
        x1 = encode1(texts).to(DEVICE)
        x2 = encode2(texts).to(DEVICE)
        s1 = st_util.cos_sim(x1, dim_emb1).cpu().numpy()
        s2 = st_util.cos_sim(x2, dim_emb2).cpu().numpy()
    s1 = (s1 + 1.0) / 2.0
    s2 = (s2 + 1.0) / 2.0
    sims = (s1 + s2) / 2.0  # [N, 14]
    idx = DIM_KEYS.index(dim_name)
    w = np.full_like(sims, 0.6, dtype=np.float32)
    w[:, idx] = 2.0
    feats = (sims * w).astype(np.float32)
    norms = np.linalg.norm(feats, axis=1, keepdims=True) + 1e-12
    return feats / norms

def pick_representatives(emb: np.ndarray, texts: list[str], labels: np.ndarray):
    clusters = {}
    for i, lbl in enumerate(labels):
        clusters.setdefault(lbl, []).append(i)
    reps = []
    for _, idxs in clusters.items():
        vecs = emb[idxs]
        center = vecs.mean(axis=0, keepdims=True)
        center = center / (np.linalg.norm(center, axis=1, keepdims=True) + 1e-12)
        sims = (vecs @ center.T).reshape(-1)
        best_local = int(np.argmax(sims))
        rep_idx = idxs[best_local]
        reps.append((texts[rep_idx], [texts[i] for i in idxs]))
    return reps

def cluster_within_dimensions(mapped_rows, encode1, encode2, dim_emb1, dim_emb2, max_k=10):
    # 1) bucket by top-1
    buckets = {d: [] for d in DIM_KEYS}
    for r in mapped_rows:
        st = r["subtheme"]
        dims = [d for d in r["mapped_dimensions"].split("|") if d.strip()]
        if not dims:
            continue
        top1 = dims[0]
        if top1 in buckets:
            buckets[top1].append(st)

    # 2) per-dim KMeans and pick reps
    dim_to_clusters = {}
    for dim, texts in buckets.items():
        if len(texts) == 0:
            dim_to_clusters[dim] = []
            continue
        k = min(max_k, len(texts))
        if k == 1:
            dim_to_clusters[dim] = [{"representative": texts[0], "members": texts}]
            continue
        if k == len(texts):
            dim_to_clusters[dim] = [{"representative": t, "members": [t]} for t in texts]
            continue
        emb = embed_texts_for_cluster(texts, dim_name=dim, encode1=encode1, encode2=encode2, dim_emb1=dim_emb1, dim_emb2=dim_emb2)
        km = KMeans(n_clusters=k, n_init=10, random_state=SEED)
        labels = km.fit_predict(emb)
        reps = pick_representatives(emb, texts, labels)
        reps = sorted(reps, key=lambda x: x[0].lower())
        dim_to_clusters[dim] = [{"representative": rep, "members": members} for rep, members in reps]
    return dim_to_clusters

# ========== Main ==========
def main():
    if len(sys.argv) < 2:
        print("Usage: python map_subthemes_to_clusters.py subthemes.csv [out_json]")
        sys.exit(1)

    csv_in = Path(sys.argv[1]).resolve()
    out_json = Path(sys.argv[2]).resolve() if len(sys.argv) >= 3 else (csv_in.parent / "dimension_clusters.json")

    df = pd.read_csv(csv_in, encoding="utf-8-sig")
    df = df.rename(columns={c: c.lstrip("\ufeff") for c in df.columns})
    if "sub_theme" not in df.columns:
        raise RuntimeError("CSV must contain column: sub_theme")

    # 1) collect unique subthemes
    subthemes = uniq_keep([str(s).strip() for s in df["sub_theme"].tolist() if str(s).strip()])

    # 2) load models/embeddings
    encode1, encode2, dim_emb1, dim_emb2, cr = load_models()

    # 3) map each subtheme to dims (precision-first)
    rows = []
    for st in subthemes:
        dims = map_one(st, encode1, encode2, dim_emb1, dim_emb2, cr)
        rows.append({"subtheme": st, "mapped_dimensions": "|".join(dims)})

    # 4) cluster within each dimension to ≤10 reps
    clusters = cluster_within_dimensions(rows, encode1, encode2, dim_emb1, dim_emb2, max_k=10)

    # 5) write ONLY clusters JSON
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(clusters, f, ensure_ascii=False, indent=2)
    print("[ok] saved:", out_json)

if __name__ == "__main__":
    main()

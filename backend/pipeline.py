import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from pathlib import Path
from sentence_transformers import SentenceTransformer, util as st_util
import numpy as np

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_CSV  = ROOT_DIR / "data" / "raw" / "reviews.csv"
NLTK_DIR  = ROOT_DIR / "backend" / "models" / "nltk_data"
MODELS_DIR = ROOT_DIR / "backend" / "models"
ANN_CSV = ROOT_DIR / "data" / "processed" / "annotated.csv"

def load_raw_csv(path) -> pd.DataFrame :
    df = pd.read_csv(path)                 
    df = df.copy()
    df.insert(0, "id", range(1, len(df)+1)) 
    return df

# TODO: def add_senti_labels(df) -> DataFrame

# 1 vader
def pred_vader(texts):
    nltk.data.path.insert(0, str(NLTK_DIR))
    nltk.data.find('sentiment/vader_lexicon.zip')
    vader_mdl=SentimentIntensityAnalyzer()
    return ["positive" if vader_mdl.polarity_scores(t or "")["compound"] >= 0 else "negative" for t in texts]

# 2.1 roberta_twitter
def pred_roberta(texts, max_len=256, bs=64):
    RO_REPO = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    ro_tok = AutoTokenizer.from_pretrained(RO_REPO, cache_dir=str(MODELS_DIR))
    ro_mdl = AutoModelForSequenceClassification.from_pretrained(RO_REPO, cache_dir=str(MODELS_DIR)).to(DEVICE).eval()
    ro_id2label = ro_mdl.config.id2label
    RO_POS = next(i for i,n in ro_id2label.items() if n.lower().startswith("pos"))
    RO_NEG = next(i for i,n in ro_id2label.items() if n.lower().startswith("neg"))
    out = []
    for i in range(0, len(texts), bs):
        batch = texts[i:i+bs]
        enc = ro_tok(batch, return_tensors="pt", padding=True, truncation=True, max_length=max_len).to(DEVICE)
        with torch.no_grad():
            probs = torch.softmax(ro_mdl(**enc).logits, dim=-1).cpu()
        for j in range(len(batch)):
            out.append("positive" if float(probs[j, RO_POS]) >= float(probs[j, RO_NEG]) else "negative")
    return out

# 2.2 sst2_distilbert
def pred_sst2(texts, max_len=256, bs=64):
    SST_REPO = "distilbert-base-uncased-finetuned-sst-2-english"
    sst_tok = AutoTokenizer.from_pretrained(SST_REPO, cache_dir=str(MODELS_DIR))
    sst_mdl = AutoModelForSequenceClassification.from_pretrained(SST_REPO, cache_dir=str(MODELS_DIR)).to(DEVICE).eval()
    sst_id2label = sst_mdl.config.id2label
    out = []
    for i in range(0, len(texts), bs):
        batch = texts[i:i+bs]
        enc = sst_tok(batch, return_tensors="pt", padding=True, truncation=True, max_length=max_len).to(DEVICE)
        with torch.no_grad():
            probs = torch.softmax(sst_mdl(**enc).logits, dim=-1).cpu()
        for j in range(len(batch)):
            top = int(torch.argmax(probs[j]).item())
            lab = sst_id2label[top].lower()
            out.append("positive" if "pos" in lab else "negative")
    return out

# majority voting to three models
def majority_voting(ro, sst, vd):
    votes = [ro, sst, vd]
    if votes.count("positive") > votes.count("negative"): return "positive"
    if votes.count("negative") > votes.count("positive"): return "negative"
    return sst or ro or vd

def add_senti_labels(df) -> pd.DataFrame :
    texts = df["text"].tolist()
    ro = pred_roberta(texts)
    sst = pred_sst2(texts)
    vd = pred_vader(texts)
    df = df.copy()
    df["roberta_twitter"]   = ro
    df["sst2_distilbert"]   = sst
    df["vader"]             = vd
    df["sentiment"] = [majority_voting(r, s, v) for r, s, v in zip(ro, sst, vd)]
    return df

# TODO: def add_dimen_labels(df) -> DataFrame
LABEL_DESCRIPTIONS = {
    "Collaboration": "teamwork, cooperation and working well together",
    "Diversity":     "diversity and representation of different backgrounds with equal opportunity",
    "Inclusion":     "inclusion where every employee is included and heard with psychological safety and participation",
    "Belonging":     "feeling accepted and part of the team",
    "Innovation":    "innovation, experimentation, trying new ideas, continuous improvement",
    "Leadership":    "leadership and management quality from top to lower management including decision making and direction",
    "Recognition":   "recognition, rewards, bonuses, appreciation of contributions, fair pay, salary and compensation",
    "Respect":       "respectful and civil workplace, fair treatment, safety from harassment and bullying"
}
DIM_KEYS  = list(LABEL_DESCRIPTIONS.keys())
DESC_LIST = [LABEL_DESCRIPTIONS[k] for k in DIM_KEYS]
CONTEXT_PREFIX = "This comment is about workplace culture: "

# 1 Bi-encoder
bi_mdl = SentenceTransformer(
    "sentence-transformers/all-mpnet-base-v2",
    device=DEVICE,
    cache_folder=str(MODELS_DIR),)
dim_emb = bi_mdl.encode(DESC_LIST, normalize_embeddings=True, convert_to_tensor=True)

# 2 Cross-encoder
cr_mdl = pipeline("zero-shot-classification",
    model="facebook/bart-large-mnli",
    device=DEVICE,
    cache_folder=str(MODELS_DIR),)

# - hyperparams
RECALL_THRESHOLD = 0.30  # Bi-encoder similarity threshold to keep a label candidate
RECALL_TOP_M     = 3     # Always keep at least Top-M candidates by Bi similarity
CROSS_THRESHOLD  = 0.68  # Cross-encoder (BART-MNLI) confidence threshold
BI_MIN_SIM       = 0.35  # Extra safety: keep only labels whose Bi-sim >= this

# 3 classify dimensions
def dimen_class(text):
    if not isinstance(text, str) or not text.strip():
        return ""

    dims_out = []
    sents = nltk.sent_tokenize(text) or [""]

    for s in sents:
        # 1) Build a short context and get Bi-encoder similarity to each label description
        ctx = f"Workplace culture comment: {s}"
        txt_emb = bi_mdl.encode([ctx], normalize_embeddings=True, convert_to_tensor=True)
        sims = st_util.cos_sim(txt_emb, dim_emb).cpu().numpy()[0]  # shape: [8]

        # 2) candidates = (over threshold) ∪ (Top-M by sim)
        over_th = np.where(sims >= RECALL_THRESHOLD)[0].tolist()
        top_m   = np.argsort(-sims)[:RECALL_TOP_M].tolist()
        cand_ix = sorted(set(over_th + top_m), key=lambda k: -sims[k])
        cand_desc = [DESC_LIST[j] for j in cand_ix]

        # 3) Cross-encoder scores candidates only
        res = cr_mdl(
            CONTEXT_PREFIX + s,
            candidate_labels=cand_desc,
            multi_label=True,
            hypothesis_template="The statement is about {}."
        )
        labels = res["labels"]
        scores = np.array(res["scores"], dtype=float)

        # Map back to fixed label indices
        back_ix = [DESC_LIST.index(lbl) for lbl in labels]
        bi_scores_cand = np.array([sims[j] for j in back_ix], dtype=float)

        # 4) Keep labels passing BOTH thresholds
        passed = [
            (j, float(sc))
            for j, sc, bs in zip(back_ix, scores, bi_scores_cand)
            if (sc >= CROSS_THRESHOLD) and (bs >= BI_MIN_SIM)
        ]
        passed.sort(key=lambda x: -x[1])

        # 5) Fallback: if none passed, take the best Cross label (top-1)
        if not passed and len(scores) > 0:
            top1 = int(np.argmax(scores))
            passed = [(back_ix[top1], float(scores[top1]))]

        # Collect dimension names for this sentence
        dims_out.extend([DIM_KEYS[j] for j, _ in passed])

    # 6) Deduplicate while preserving order (sentence → doc)
    seen, merged = set(), []
    for d in dims_out:
        if d not in seen:
            seen.add(d)
            merged.append(d)
    return "|".join(merged)

def add_dimen_labels(df) -> pd.DataFrame :
    df = df.copy()
    df["dimensions"] = [ dimen_class(t or "") for t in df["text"].astype(str).tolist() ]
    return df

if __name__ == "__main__":
    df = load_raw_csv(RAW_CSV)
    df = add_senti_labels(df)
    df = add_dimen_labels(df)
    df_out = df[["id", "region", "year", "text", "sentiment", "dimensions"]]
    df_out.to_csv(ANN_CSV, index=False, encoding="utf-8")
    
    
# ......

# TODO: def run_pipeline()
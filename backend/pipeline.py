import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from pathlib import Path

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

# TODO: def add_labels(df) -> DataFrame
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def add_labels(df) -> pd.DataFrame :
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

# 1 vader
def pred_vader(texts):
    nltk.data.path.insert(0, str(NLTK_DIR))
    nltk.data.find('sentiment/vader_lexicon.zip')
    m_vader=SentimentIntensityAnalyzer()
    return ["positive" if m_vader.polarity_scores(t or "")["compound"] >= 0 else "negative" for t in texts]

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

def majority_voting(ro, sst, vd):
    votes = [ro, sst, vd]
    if votes.count("positive") > votes.count("negative"): return "positive"
    if votes.count("negative") > votes.count("positive"): return "negative"
    return sst or ro or vd


def senti_ana():
    df = load_raw_csv(RAW_CSV)
    df = add_labels(df)
    #print(df[["id","text","roberta_twitter","sst2_distilbert","vader","sentiment"]].head(20).to_string(index=False))
    #df_out = df[["id", "region", "year", "text", "sentiment"]]
    #df_out.to_csv(ANN_CSV, index=False, encoding="utf-8")
    return df


if __name__ == "__main__":
    senti_ana()
    
# ......

# TODO: def run_pipeline()
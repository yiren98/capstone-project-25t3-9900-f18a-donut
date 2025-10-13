# backend/download_models.py
# 1 download two models from NLTK to ./models/nltk_data
#    - vader_lexicon
#    - punkt
# 2 download four models from HF to ./models
#    - cardiffnlp/twitter-roberta-base-sentiment-latest
#    - distilbert-base-uncased-finetuned-sst-2-english
#    - facebook/bart-large-mnli
#    - sentence-transformers/all-mpnet-base-v2
# python backend/download_models.py

from huggingface_hub import snapshot_download
from pathlib import Path
import nltk
import os

ROOT = Path(__file__).resolve().parents[0]
MODELS_DIR = ROOT / "models"
NLTK_DIR = MODELS_DIR / "nltk_data"

MODELS_DIR.mkdir(parents=True, exist_ok=True)
NLTK_DIR.mkdir(parents=True, exist_ok=True)

# 1 NLTK
nltk.data.path.insert(0, str(NLTK_DIR))
for name, locator in [("vader_lexicon", "sentiment/vader_lexicon.zip"), 
                      ("punkt", "tokenizers/punkt"), 
                      ("punkt_tab", "tokenizers/punkt_tab"),]:
    try:
        nltk.data.find(locator)
        print(f"{name} already exists")
    except LookupError:
        nltk.download(name, download_dir=str(NLTK_DIR))

# 2 HF
hf_models = [
    # sentiment
    "cardiffnlp/twitter-roberta-base-sentiment-latest",  # roberta_twitter_base
    "distilbert-base-uncased-finetuned-sst-2-english",  # sst2_distilbert
    # dimensions
    "facebook/bart-large-mnli", # ZSL Cross-encoder
    "sentence-transformers/all-mpnet-base-v2",  # Bi-encoder
]
for model in hf_models:
    snapshot_download(
        repo_id=model,
        cache_dir=str(MODELS_DIR),   
        local_dir_use_symlinks=False 
    )

print("downloaded")

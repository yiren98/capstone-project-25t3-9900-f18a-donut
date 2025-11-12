# 0.5_download_models.py
# Downloads all required models for current pipeline.
# Usage: python download_models.py
# 1. NLTK → ./backend/models/nltk_data
#    - vader_lexicon
#    - punkt
# 2. Hugging Face → ./backend/models
#    For sentiment + mapping:
#       - cardiffnlp/twitter-roberta-base-sentiment-latest
#       - distilbert-base-uncased-finetuned-sst-2-english
#       - BAAI/bge-base-en-v1.5
#       - princeton-nlp/sup-simcse-roberta-base
#       - cross-encoder/ms-marco-MiniLM-L-6-v2

from pathlib import Path
from huggingface_hub import snapshot_download
import nltk
import os

# ============ Paths ============
ROOT = Path(__file__).resolve().parents[0]   # backend/
MODELS_DIR = ROOT / "models"                 # HF models
NLTK_DIR = MODELS_DIR / "nltk_data"          # nltk data
MODELS_DIR.mkdir(parents=True, exist_ok=True)
NLTK_DIR.mkdir(parents=True, exist_ok=True)

# ============ 1. NLTK ============
nltk.data.path.insert(0, str(NLTK_DIR))
for name, locator in [
    ("vader_lexicon", "sentiment/vader_lexicon.zip"),
    ("punkt", "tokenizers/punkt"),
]:
    try:
        nltk.data.find(locator)
        print(f"[nltk] {name} already exists")
    except LookupError:
        print(f"[nltk] downloading {name} ...")
        nltk.download(name, download_dir=str(NLTK_DIR))

# ============ 2. HuggingFace Models ============
hf_models = [
    # sentiment analysis
    "cardiffnlp/twitter-roberta-base-sentiment-latest",
    "distilbert-base-uncased-finetuned-sst-2-english",
    # retrieval + rerank
    "BAAI/bge-base-en-v1.5",
    "princeton-nlp/sup-simcse-roberta-base",
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
]

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

for repo in hf_models:
    print(f"[hf] downloading {repo} ...")
    snapshot_download(
        repo_id=repo,
        cache_dir=str(MODELS_DIR),
        local_dir_use_symlinks=False
    )

print("[ok] all models downloaded to:", MODELS_DIR)

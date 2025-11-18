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

from __future__ import annotations

from pathlib import Path
import os
import nltk

# Try to import huggingface_hub
# If not installed, we skip HF downloading safely.
try:
    from huggingface_hub import snapshot_download
except ImportError:
    snapshot_download = None


# ====================== Paths =======================
# Folder: backend/
ROOT = Path(__file__).resolve().parents[0]

# HuggingFace models will be saved here
MODELS_DIR = ROOT / "models"

# NLTK data folder
NLTK_DIR = MODELS_DIR / "nltk_data"

# Make sure folders exist
MODELS_DIR.mkdir(parents=True, exist_ok=True)
NLTK_DIR.mkdir(parents=True, exist_ok=True)

# Disable symlink warnings on Windows
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


# ====================== Lists =======================
# NLTK packages we need
NLTK_PACKAGES = [
    ("vader_lexicon", "sentiment/vader_lexicon.zip"),
    ("punkt", "tokenizers/punkt"),
]

# HuggingFace models required by pipeline
HF_MODELS = [
    "cardiffnlp/twitter-roberta-base-sentiment-latest",
    "distilbert-base-uncased-finetuned-sst-2-english",
    "BAAI/bge-base-en-v1.5",
    "princeton-nlp/sup-simcse-roberta-base",
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
]


# ====================== Functions =======================
def download_nltk() -> None:
    """
    Download NLTK resources into NLTK_DIR.
    If the resource already exists, skip it.
    """
    # Add our NLTK_DIR to nltk search path
    if str(NLTK_DIR) not in nltk.data.path:
        nltk.data.path.insert(0, str(NLTK_DIR))

    for name, locator in NLTK_PACKAGES:
        try:
            nltk.data.find(locator)
            print(f"[nltk] {name} already exists.")
        except LookupError:
            print(f"[nltk] Downloading {name} ...")
            nltk.download(name, download_dir=str(NLTK_DIR))


def download_hf_models() -> None:
    """
    Download HuggingFace models into MODELS_DIR.
    - Each model is stored in a separate folder.
    - We use local_dir_use_symlinks=False to avoid Windows permission issues.
    """
    if snapshot_download is None:
        print("[hf] huggingface_hub is not installed. Skip HF models.")
        return

    for repo in HF_MODELS:
        safe_name = repo.replace("/", "--")  # Safe folder name
        local_dir = MODELS_DIR / safe_name

        print(f"[hf] Downloading {repo} ...")

        snapshot_download(
            repo_id=repo,
            local_dir=str(local_dir),
            local_dir_use_symlinks=False,
        )

    print(f"[ok] All HF models stored in {MODELS_DIR}")


# ====================== Main =======================
def main() -> None:
    """
    Main entry point.
    All downloads happen here.
    """
    print(f"[info] Models directory: {MODELS_DIR}")
    print(f"[info] NLTK directory:   {NLTK_DIR}")

    download_nltk()
    download_hf_models()

    print("[ok] All models downloaded successfully.")


if __name__ == "__main__":
    main()
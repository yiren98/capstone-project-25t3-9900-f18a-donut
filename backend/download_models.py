# 1. the vader_lexicon from NLTK to ./nltk_data
# 2. two bert from HF downloaded to ./models
# python download_models.py

from huggingface_hub import snapshot_download
from pathlib import Path
import nltk

# 1
NLTK_DIR = Path("models/nltk_data")
NLTK_DIR.mkdir(parents=True, exist_ok=True)
nltk.data.path.insert(0, str(NLTK_DIR))
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon", download_dir=str(NLTK_DIR))

# 2
MODELS_DIR = Path("models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

models = [
    "cardiffnlp/twitter-roberta-base-sentiment-latest",  # roberta_twitter_base
    "distilbert-base-uncased-finetuned-sst-2-english",  # sst2_distilbert
]
for model in models:
    snapshot_download(
        repo_id=model,
        cache_dir=str(MODELS_DIR),   
        local_dir_use_symlinks=False 
    )

print("downloaded")

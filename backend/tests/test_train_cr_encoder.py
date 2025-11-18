# Test for train_cr_encoder.main()
# Features:
# - Fake sentence_transformers module (SentenceTransformer, CrossEncoder, InputExample, util.cos_sim)
# - Patch paths (ROOT_DIR, MODELS_DIR, CE_FT_DIR, OUT_SUMMARY) into tmp_path
# - Create small subthemes.csv and gold.csv
# - Run train_cr_encoder.main()
# - Check that mapping_eval_summary.json and CE fine-tuned directory are created
#
# Usage:
#   pytest tests/test_train_cr_encoder.py -q

import json
from pathlib import Path
import types
import importlib
import numpy as np
import pandas as pd
import torch

def test_train_cr_encoder_main_creates_summary_and_model(tmp_path, monkeypatch):

    # ---------- Fake sentence_transformers module ----------
    import sys

    class FakeSentenceTransformer:
        def __init__(self, name, device=None):
            self.name = name
            self.device = device

        def encode(self, texts, convert_to_tensor=True, normalize_embeddings=True, batch_size=64):
            # shape: [len(texts), 4]
            arr = torch.zeros(len(texts), 4)
            for i in range(len(texts)):
                arr[i, 0] = float(i + 1)
            return arr

    def fake_cos_sim(x, y):
        # Simple dot-product similarity for test
        return torch.mm(x, y.T)

    class FakeCrossEncoder:
        def __init__(self, model_name_or_path, device=None):
            self.model_name_or_path = model_name_or_path
            self.device = device

        def fit(self, train_dataloader, epochs, warmup_steps, optimizer_params, use_amp, output_path):
            # No real training in tests
            pass

        def save(self, path):
            # Just create the directory to simulate a saved model
            p = Path(path)
            p.mkdir(parents=True, exist_ok=True)

        def predict(self, pairs, apply_softmax=True):
            # Always predict label 1 with high probability
            n = len(pairs)
            probs = np.tile(np.array([[0.2, 0.8]], dtype="float32"), (n, 1))
            return probs

    class FakeInputExample:
        def __init__(self, texts, label):
            self.texts = texts
            self.label = label

    fake_st_module = types.SimpleNamespace(
        SentenceTransformer=FakeSentenceTransformer,
        util=types.SimpleNamespace(cos_sim=fake_cos_sim),
        CrossEncoder=FakeCrossEncoder,
        InputExample=FakeInputExample,
    )

    # Inject fake sentence_transformers into sys.modules
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st_module)

    # ---------- Import and reload train_cr_encoder with fakes ----------
    import train_cr_encoder  # noqa: E402
    importlib.reload(train_cr_encoder)

    # ---------- Redirect ROOT_DIR / MODELS_DIR / CE_FT_DIR / OUT_SUMMARY to tmp_path ----------
    monkeypatch.setattr(train_cr_encoder, "ROOT_DIR", tmp_path, raising=False)

    models_dir = tmp_path / "models"
    ce_dir = models_dir / "ce_ft"
    out_summary = tmp_path / "data" / "processed" / "mapping_eval_summary.json"

    monkeypatch.setattr(train_cr_encoder, "MODELS_DIR", models_dir, raising=False)
    monkeypatch.setattr(train_cr_encoder, "CE_FT_DIR", ce_dir, raising=False)
    monkeypatch.setattr(train_cr_encoder, "OUT_SUMMARY", out_summary, raising=False)

    out_summary.parent.mkdir(parents=True, exist_ok=True)

    # ---------- Create subthemes.csv & gold.csv in tmp_path ----------
    subs_csv = tmp_path / "subthemes.csv"
    gold_csv = tmp_path / "gold.csv"

    df_sub = pd.DataFrame(
        {
            "sub_theme": [
                "Safety Culture",
                "Innovation & Technology",
            ]
        }
    )
    df_sub.to_csv(subs_csv, index=False, encoding="utf-8-sig")

    df_gold = pd.DataFrame(
        {
            "subthemes": ["Safety Culture", "Innovation & Technology"],
            "dimensions": [
                "Well-being|Safety",
                "Innovation|Digital Empowerment",
            ],
        }
    )
    df_gold.to_csv(gold_csv, index=False)

    monkeypatch.setattr(train_cr_encoder, "CSV_SUBTHEMES", subs_csv, raising=False)
    monkeypatch.setattr(train_cr_encoder, "CSV_GOLD", gold_csv, raising=False)

    # ---------- Run main() ----------
    train_cr_encoder.main()

    # ---------- Check summary JSON ----------
    assert out_summary.exists(), "mapping_eval_summary.json should be created"

    data = json.loads(out_summary.read_text(encoding="utf-8"))
    for key in [
        "all_mapped",
        "coverage",
        "micro_f1",
        "macro_f1",
        "example_f1",
        "top1_accuracy",
    ]:
        assert key in data, f"{key} missing in summary json"

    assert isinstance(data["coverage"], float)
    assert 0.0 <= data["micro_f1"] <= 1.0

    # ---------- Check fine-tuned CE directory ----------
    assert ce_dir.exists(), "Fine-tuned CE directory should be created"

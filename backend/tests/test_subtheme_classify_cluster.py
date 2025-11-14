import json
from pathlib import Path
import types
import importlib
import pandas as pd
import numpy as np


def test_subtheme_classify_cluster_main_creates_clusters_json(tmp_path, monkeypatch):

    # ---------- fake sentence_transformers module ----------
    import sys

    class FakeSentenceTransformer:
        def __init__(self, name, device=None):
            self.name = name
            self.device = device

        def encode(self, texts, convert_to_tensor=True, normalize_embeddings=True, batch_size=64):
            return np.zeros((len(texts), 4), dtype="float32")

    class FakeCrossEncoder:
        def __init__(self, model_name_or_path, device=None):
            self.model_name_or_path = model_name_or_path
            self.device = device

        def predict(self, pairs, apply_softmax=True):
            n = len(pairs)
            return np.tile(np.array([[0.5, 0.5]], dtype="float32"), (n, 1))

    def fake_cos_sim(x, y):
        return np.zeros((x.shape[0], y.shape[0]), dtype="float32")

    fake_st_module = types.SimpleNamespace(
        SentenceTransformer=FakeSentenceTransformer,
        CrossEncoder=FakeCrossEncoder,
        util=types.SimpleNamespace(cos_sim=fake_cos_sim),
    )

    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st_module)

    import subtheme_classify_cluster  # noqa: E402
    importlib.reload(subtheme_classify_cluster)

    monkeypatch.setattr(subtheme_classify_cluster, "ROOT_DIR", tmp_path, raising=False)
    models_dir = tmp_path / "models"
    out_dir = models_dir / "ce_ft"
    monkeypatch.setattr(subtheme_classify_cluster, "MODELS_DIR", models_dir, raising=False)
    monkeypatch.setattr(subtheme_classify_cluster, "OUT_DIR", out_dir, raising=False)

    csv_in = tmp_path / "subthemes.csv"
    df_sub = pd.DataFrame(
        {
            "sub_theme": [
                "Safety Culture",
                "Innovation & Technology",
                "Digital Tools & Data",
                "Customer Focus",
            ]
        }
    )
    csv_in.parent.mkdir(parents=True, exist_ok=True)
    df_sub.to_csv(csv_in, index=False, encoding="utf-8-sig")

    def fake_load_models():
        encode1 = object()
        encode2 = object()
        dim_emb1 = object()
        dim_emb2 = object()
        cr = object()
        return encode1, encode2, dim_emb1, dim_emb2, cr

    monkeypatch.setattr(subtheme_classify_cluster, "load_models", fake_load_models, raising=False)

    def fake_map_one(text, encode1, encode2, dim_emb1, dim_emb2, cr):
        text = (text or "").lower()
        if "safety" in text:
            return ["Well-being"]
        if "digital" in text or "data" in text:
            return ["Digital Empowerment"]
        if "customer" in text:
            return ["Customer Orientation"]
        return ["Agility"]

    monkeypatch.setattr(subtheme_classify_cluster, "map_one", fake_map_one, raising=False)

    def fake_cluster_within_dimensions(mapped_rows, encode1, encode2, dim_emb1, dim_emb2, max_k=10):
        buckets = {}
        for r in mapped_rows:
            dims = [d for d in r["mapped_dimensions"].split("|") if d.strip()]
            if not dims:
                continue
            dim = dims[0]
            buckets.setdefault(dim, []).append(r["subtheme"])

        result = {}
        for dim in subtheme_classify_cluster.DIM_KEYS:
            items = buckets.get(dim, [])
            if not items:
                result[dim] = []
            else:
                result[dim] = [
                    {
                        "representative": items[0],
                        "members": items,
                    }
                ]
        return result

    monkeypatch.setattr(
        subtheme_classify_cluster,
        "cluster_within_dimensions",
        fake_cluster_within_dimensions,
        raising=False,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["subtheme_classify_cluster.py", str(csv_in)],
        raising=False,
    )

    subtheme_classify_cluster.main()

    out_json = csv_in.parent / "dimension_clusters.json"
    assert out_json.exists(), "dimension_clusters.json should be created by main()"

    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "Output JSON should be a dict"

    non_empty_dims = [dim for dim, clusters in data.items() if clusters]
    assert len(non_empty_dims) >= 1, "At least one dimension should have non-empty clusters"

    for dim, clusters in data.items():
        assert isinstance(clusters, list)
        for c in clusters:
            assert "representative" in c
            assert "members" in c
            assert isinstance(c["members"], list)
            assert c["representative"] in c["members"]

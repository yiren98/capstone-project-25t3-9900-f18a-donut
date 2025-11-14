from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # backend/
PROJECT_ROOT = ROOT.parent


def test_required_backend_scripts_exist():
    """Check that all key backend scripts exist."""
    required = [
        "data_process.py",
        "download_models.py",
        "sentiment_dbcheck.py",
        "train_cr_encoder.py",
        "subtheme_classify_cluster.py",
        "mapping_sub2dim.py",
        "pipeline.py",
    ]
    for name in required:
        path = ROOT / name
        assert path.exists(), f"Missing backend script: {path}"


def test_data_directories_exist_or_can_be_created():
    """Check that the expected data directory structure exists (or at least roots)."""
    data_dir = PROJECT_ROOT / "data"
    processed_dir = data_dir / "processed"
    raw_dir = data_dir / "raw"
    gold_dir = data_dir / "gold"

    # We don't require files to exist in CI, just the directories.
    # If they don't exist, this indicates the repo layout is different.
    assert data_dir.exists(), f"data directory does not exist: {data_dir}"
    # The others may be created at runtime by run_pipeline; we only check parents.
    assert data_dir.is_dir(), f"data path is not a directory: {data_dir}"
    # processed/raw/gold are optional but nice to have
    for d in (processed_dir, raw_dir, gold_dir):
        if d.exists():
            assert d.is_dir(), f"{d} exists but is not a directory"

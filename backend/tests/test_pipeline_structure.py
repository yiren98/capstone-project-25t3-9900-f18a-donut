# Basic checks for project structure
# Features:
# - Verify key backend scripts exist under backend/
# - Check expected data/ directory structure is present
#
# Usage:
#   pytest tests/test_pipeline_structure.py -q

from pathlib import Path

# Path to backend/
ROOT = Path(__file__).resolve().parents[1]
# Path to project root
PROJECT_ROOT = ROOT.parent


def test_required_backend_scripts_exist():
    # Check that all important backend scripts exist
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
    # Check that the expected data directory structure exists
    data_dir = PROJECT_ROOT / "data"
    processed_dir = data_dir / "processed"
    raw_dir = data_dir / "raw"
    gold_dir = data_dir / "gold"

    # data/ must exist
    assert data_dir.exists(), f"data directory does not exist: {data_dir}"
    assert data_dir.is_dir(), f"data path is not a directory: {data_dir}"

    # processed/, raw/, and gold/ are optional but should be directories if present
    for d in (processed_dir, raw_dir, gold_dir):
        if d.exists():
            assert d.is_dir(), f"{d} exists but is not a directory"

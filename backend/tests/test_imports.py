# testing the backend modules

from importlib import import_module
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def _module_name_for_path(path: Path) -> str:
    """Convert backend/foo.py -> 'foo' for import_module."""
    return path.stem


def test_backend_scripts_importable():
    scripts = [
        "data_process.py",
        "download_models.py",
        "sentiment_dbcheck.py",
        "train_cr_encoder.py",
        "subtheme_classify_cluster.py",
        "mapping_sub2dim.py",
        "pipeline.py",
    ]
    for filename in scripts:
        module_path = BACKEND / filename
        assert module_path.exists(), f"Script not found: {module_path}"
        mod_name = _module_name_for_path(module_path)
        try:
            import_module(mod_name)
        except Exception as e:  # noqa: BLE001
            raise AssertionError(f"Failed to import module '{mod_name}': {e}") from e

# Basic import test for backend scripts
# Features:
# - Check that key backend .py files exist
# - Try importing each file as a module (import_module)
# - Fail clearly if any script cannot be imported
#
# Usage:
#   pytest tests/test_imports.py -q

from importlib import import_module
from pathlib import Path

# Project root/backend directory
BACKEND = Path(__file__).resolve().parents[1]


def _module_name_for_path(path: Path) -> str:
    # Return the module name for a given file path (e.g., backend/foo.py -> 'foo').
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

        # Check that script file exists
        assert module_path.exists(), f"Script not found: {module_path}"

        # Convert to module name, e.g., 'data_process'
        mod_name = _module_name_for_path(module_path)

        # Try import; fail if any error occurs
        try:
            import_module(mod_name)
        except Exception as e:  # noqa: BLE001
            raise AssertionError(
                f"Failed to import module '{mod_name}': {e}"
            ) from e

# tests/test_suggestions.py
# Tests for suggestions.py reporting pipeline.
#
# Features:
# - Build a fake project root under tmp_path with data/processed/comments.csv
# - Monkeypatch subprocess.run so no real scripts are executed
# - Call suggestions.main() with --root and --max-examples
# - Check that two commands are executed:
#   1) overall_sr.py
#   2) subthe_dimen_sr.py
#
# Usage:
#   pytest tests/test_suggestions.py -q

from pathlib import Path
import suggestions


def test_suggestions_runs_overall_and_subtheme(tmp_path, monkeypatch):
    # Fake project root: data/processed/comments.csv
    root_dir = tmp_path
    processed_dir = root_dir / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    comments_csv = processed_dir / "comments.csv"
    comments_csv.write_text("id,text\n1,dummy\n", encoding="utf-8")

    calls = []

    def fake_run(cmd, cwd=None):
        calls.append((cmd, cwd))

        class Result:
            returncode = 0

        return Result()

    # Monkeypatch subprocess.run used inside suggestions.run_cmd
    monkeypatch.setattr(suggestions.subprocess, "run", fake_run, raising=False)

    # Run main with custom root and custom max-examples
    suggestions.main(
        [
            "--root",
            str(root_dir),
            "--max-examples",
            "7",
        ]
    )

    # We expect exactly two commands: overall_sr.py and subthe_dimen_sr.py
    assert len(calls) == 2

    backend_dir = Path(suggestions.__file__).resolve().parent

    # First command: overall_sr.py
    cmd1, cwd1 = calls[0]
    assert cwd1 == str(backend_dir)
    assert Path(cmd1[1]).name == "overall_sr.py"
    assert "--csv" in cmd1
    idx_csv1 = cmd1.index("--csv")
    assert Path(cmd1[idx_csv1 + 1]) == comments_csv
    assert "--out" in cmd1

    # Second command: subthe_dimen_sr.py
    cmd2, cwd2 = calls[1]
    assert cwd2 == str(backend_dir)
    assert Path(cmd2[1]).name == "subthe_dimen_sr.py"
    assert "--csv" in cmd2
    idx_csv2 = cmd2.index("--csv")
    assert Path(cmd2[idx_csv2 + 1]) == comments_csv

    assert "--outdir" in cmd2
    outdir = Path(cmd2[cmd2.index("--outdir") + 1])
    assert outdir == processed_dir / "subthemes_sr"

    assert "--dim-outdir" in cmd2
    dim_outdir = Path(cmd2[cmd2.index("--dim-outdir") + 1])
    assert dim_outdir == processed_dir / "dimensions_sr"

    assert "--max-examples" in cmd2
    max_ex = cmd2[cmd2.index("--max-examples") + 1]
    assert max_ex == "7"

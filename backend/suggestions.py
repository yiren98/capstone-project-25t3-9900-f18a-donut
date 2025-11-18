# suggestions.py
# One-command runner for the reporting pipeline.
#
# This script runs:
#   1) overall_sr.py
#      -> Generate overall_summary.json (overall culture report)
#   2) subthe_dimen_sr.py
#      -> Generate subtheme & dimension JSON summaries
#
# Usage:
#   # Default project layout:
#   #   python suggestions.py
#   #
#   # Use a custom project root:
#   #   python suggestions.py --root ../..
#   #
#   # Change max examples per label for subthe_dimen_sr.py:
#   #   python suggestions.py --max-examples 5

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd, cwd: Path | None = None) -> None:
    # Helper to run a shell command and print its output.
    # If the command exits with a non-zero code, the whole pipeline stops.
    printable = " ".join(str(c) for c in cmd)
    print(f"\n[CMD] {printable}")
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd is not None else None,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"[ERROR] Command failed with exit code {result.returncode}: {printable}"
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run the reporting pipeline (overall_sr + subthe_dimen_sr).",
    )

    # Optional: custom project root (defaults to backend/..)
    parser.add_argument(
        "--root",
        help="Project root path (defaults to parent of this file).",
    )

    # Optional: max examples per label for subthe_dimen_sr.py
    parser.add_argument(
        "--max-examples",
        type=int,
        default=10,
        help="Max examples per label for subthe_dimen_sr.py.",
    )

    args = parser.parse_args(argv)

    # Basic paths (mirrors pipeline.py style)
    backend_dir = Path(__file__).resolve().parent
    root_dir = Path(args.root).resolve() if args.root else backend_dir.parent
    data_dir = root_dir / "data"
    processed_dir = data_dir / "processed"

    processed_dir.mkdir(parents=True, exist_ok=True)

    comments_csv = processed_dir / "comments.csv"
    overall_json = processed_dir / "overall_summary.json"
    subthemes_dir = processed_dir / "subthemes_sr"
    dimensions_dir = processed_dir / "dimensions_sr"

    print("========== Reporting Pipeline ==========")
    print(f"ROOT_DIR:       {root_dir}")
    print(f"BACKEND_DIR:    {backend_dir}")
    print(f"COMMENTS_CSV:   {comments_csv}")
    print(f"OVERALL_JSON:   {overall_json}")
    print(f"SUBTHEMES_DIR:  {subthemes_dir}")
    print(f"DIMENSIONS_DIR: {dimensions_dir}")
    print("----------------------------------------")

    # comments.csv must already exist (produced by pipeline.py / data_process.py)
    if not comments_csv.exists():
        raise SystemExit(f"[ERROR] comments.csv not found: {comments_csv}")

    subthemes_dir.mkdir(parents=True, exist_ok=True)
    dimensions_dir.mkdir(parents=True, exist_ok=True)

    # Step 1. overall_sr.py
    print("[1/2] Running overall_sr.py ...")
    run_cmd(
        [
            sys.executable,
            str(backend_dir / "overall_sr.py"),
            "--csv",
            str(comments_csv),
            "--out",
            str(overall_json),
        ],
        cwd=backend_dir,
    )

    # Step 2. subthe_dimen_sr.py
    print("[2/2] Running subthe_dimen_sr.py ...")
    run_cmd(
        [
            sys.executable,
            str(backend_dir / "subthe_dimen_sr.py"),
            "--csv",
            str(comments_csv),
            "--outdir",
            str(subthemes_dir),
            "--dim-outdir",
            str(dimensions_dir),
            "--max-examples",
            str(args.max_examples),
        ],
        cwd=backend_dir,
    )

    print("Reporting pipeline finished successfully.")
    print(f"Overall JSON: {overall_json}")
    print(f"Subthemes JSON dir: {subthemes_dir}")
    print(f"Dimensions JSON dir: {dimensions_dir}")


if __name__ == "__main__":
    main()

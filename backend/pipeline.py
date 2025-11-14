"""
pipeline.py

One-command runner for the backend NLP pipeline.

Usage:
    # Most common:
    python pipeline.py ../data/raw/data.csv

    # Run and also train the Cross-Encoder:
    python pipeline.py ../data/raw/data.csv --train-ce

    # Skip the neutral sentiment re-check step:
    python pipeline.py ../data/raw/data.csv --skip-neutral

Pipeline steps (mapped to your existing scripts):
    1. data_process.py
       → Generate comments.csv and subthemes.csv
    2. sentiment_dbcheck.py  (optional)
       → Re-check neutral subthemes and refine sentiment
    3. train_cr_encoder.py   (optional)
       → Train Cross-Encoder for subtheme→dimension mapping
    4. subtheme_classify_cluster.py
       → Predict dimension + cluster subthemes, output dimension_clusters.json
    5. mapping_sub2dim.py
       → Write representative subthemes and dimensions back into comments.csv
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd, cwd: Path | None = None) -> None:
    """
    Helper: run a shell command and print its output.
    If the command exits with a non-zero code, stop the whole pipeline.
    """
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
        description="Run the full backend NLP pipeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Required: raw input CSV
    parser.add_argument(
        "raw_csv",
        help="Path to the raw input CSV, containing at least [Title, Content].",
    )

    # Optional: also train Cross-Encoder
    parser.add_argument(
        "--train-ce",
        action="store_true",
        help="Train the Cross-Encoder during this run.",
    )

    # Optional: skip neutral sentiment check
    parser.add_argument(
        "--skip-neutral",
        action="store_true",
        help="Skip sentiment_dbcheck.py (do not re-check neutral subthemes).",
    )

    args = parser.parse_args(argv)

    # Basic paths
    backend_dir = Path(__file__).resolve().parent
    root_dir = backend_dir.parent
    data_dir = root_dir / "data"
    processed_dir = data_dir / "processed"
    gold_dir = data_dir / "gold"

    processed_dir.mkdir(parents=True, exist_ok=True)
    gold_dir.mkdir(parents=True, exist_ok=True)

    # Input raw file
    raw_csv = Path(args.raw_csv).resolve()
    if not raw_csv.exists():
        raise SystemExit(f"[ERROR] Input file does not exist: {raw_csv}")

    # Output files
    comments_csv = processed_dir / "comments.csv"
    subthemes_csv = processed_dir / "subthemes.csv"
    dim_clusters_json = processed_dir / "dimension_clusters.json"
    gold_csv = gold_dir / "gold_labels.csv"

    print("========== Backend NLP Pipeline ==========")
    print(f"ROOT_DIR:       {root_dir}")
    print(f"BACKEND_DIR:    {backend_dir}")
    print(f"RAW_CSV:        {raw_csv}")
    print(f"COMMENTS_CSV:   {comments_csv}")
    print(f"SUBTHEMES_CSV:  {subthemes_csv}")
    print(f"DIM_CLUSTERS:   {dim_clusters_json}")
    print("------------------------------------------")

    # ------------------------------------------------
    # Step 1. data_process.py
    # ------------------------------------------------
    print("[1/5] Running data_process.py ...")
    run_cmd(
        [
            sys.executable,
            str(backend_dir / "data_process.py"),
            str(raw_csv),
        ],
        cwd=backend_dir,
    )

    if not comments_csv.exists():
        raise SystemExit(f"[ERROR] comments.csv not found: {comments_csv}")
    if not subthemes_csv.exists():
        raise SystemExit(f"[ERROR] subthemes.csv not found: {subthemes_csv}")

    # ------------------------------------------------
    # Step 2. sentiment_dbcheck.py (optional)
    # ------------------------------------------------
    if args.skip_neutral:
        print("[2/5] Skipping sentiment_dbcheck.py (per --skip-neutral).")
    else:
        print("[2/5] Running sentiment_dbcheck.py ...")
        run_cmd(
            [
                sys.executable,
                str(backend_dir / "sentiment_dbcheck.py"),
                str(comments_csv),
            ],
            cwd=backend_dir,
        )

    # ------------------------------------------------
    # Step 3. train_cr_encoder.py (optional)
    # ------------------------------------------------
    if args.train_ce:
        print("[3/5] Training Cross-Encoder ...")
        if not gold_csv.exists():
            raise SystemExit(
                f"[ERROR] gold_labels.csv not found at {gold_csv}. "
                f"Create it before using --train-ce."
            )
        run_cmd(
            [
                sys.executable,
                str(backend_dir / "train_cr_encoder.py"),
                str(subthemes_csv),
                str(gold_csv),
            ],
            cwd=backend_dir,
        )
    else:
        print("[3/5] Skipping Cross-Encoder training.")

    # ------------------------------------------------
    # Step 4. subtheme_classify_cluster.py
    # ------------------------------------------------
    print("[4/5] Running subtheme_classify_cluster.py ...")
    run_cmd(
        [
            sys.executable,
            str(backend_dir / "subtheme_classify_cluster.py"),
            str(subthemes_csv),
            str(dim_clusters_json),
        ],
        cwd=backend_dir,
    )

    if not dim_clusters_json.exists():
        raise SystemExit(
            f"[ERROR] dimension_clusters.json not found: {dim_clusters_json}"
        )

    # ------------------------------------------------
    # Step 5. mapping_sub2dim.py
    # ------------------------------------------------
    print("[5/5] Running mapping_sub2dim.py ...")
    run_cmd(
        [
            sys.executable,
            str(backend_dir / "mapping_sub2dim.py"),
            str(comments_csv),
            str(dim_clusters_json),
        ],
        cwd=backend_dir,
    )

    print("\n[OK] Pipeline finished successfully.")
    print(f"     Final comments file: {comments_csv}")
    print("==========================================")


if __name__ == "__main__":
    main()
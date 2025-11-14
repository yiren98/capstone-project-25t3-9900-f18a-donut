"""
suggestions.py

Describe the reporting pipeline for:

1) overall_sr.py
2) subthe_dimen_sr.py

This file does NOT call any LLM.
It only stores simple descriptions and example commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Step:
    """One pipeline step with a name, short text and example command."""
    name: str
    description: str
    command: str


# Project root. Change this if your layout is different.
ROOT_DIR = Path(__file__).resolve().parents[1]


def _default_paths(root: Path | None = None) -> dict:
    """
    Build common default paths used in the pipeline.

    root/data/processed/comments.csv
    root/data/processed/overall_summary.json
    root/data/processed/subthemes_sr/
    root/data/processed/dimensions_sr/
    """
    if root is None:
        root = ROOT_DIR

    root = Path(root)
    return {
        "comments_csv":     root / "data" / "processed" / "comments.csv",
        "overall_json":     root / "data" / "processed" / "overall_summary.json",
        "subthemes_outdir": root / "data" / "processed" / "subthemes_sr",
        "dimensions_outdir": root / "data" / "processed" / "dimensions_sr",
    }


def reporting_steps(root: Path | str | None = None) -> List[Step]:
    """
    Return the two main reporting steps that use:

    - overall_sr.py
    - subthe_dimen_sr.py

    Assumes comments.csv already exists and has:
    [tag,text,author,score,comment_count,content,created_time,
     dimensions,subthemes,subs_sentiment,confidence,subs_evidences,source]
    """
    paths = _default_paths(Path(root) if root is not None else None)
    steps: List[Step] = []

    # ---------------- Step 1: overall_sr.py ----------------
    steps.append(
        Step(
            name="1. Overall culture summary (overall_sr.py)",
            description=(
                "Input: comments.csv.\n"
                "Output: one JSON file with an overall culture report.\n"
                "This step will:\n"
                "- aggregate sentiment by subtheme and dimension\n"
                "- count positive / negative mentions\n"
                "- compute average confidence\n"
                "- create dataset metadata (time, sources, counts)\n"
                "- call DeepSeek to write one executive summary in JSON\n"
                "- attach dataset_metadata into the final JSON\n\n"
                "Main flags (see overall_sr.py):\n"
                "- --csv   : input comments.csv\n"
                "- --out   : output JSON path\n"
                "- --model : LLM model name (default from DEFAULT_MODEL)\n"
                "- --title : report_title in the JSON\n"
            ),
            command=(
                "python overall_sr.py "
                f"--csv {paths['comments_csv']} "
                f"--out {paths['overall_json']}"
            ),
        )
    )

    # ---------------- Step 2: subthe_dimen_sr.py ----------------
    steps.append(
        Step(
            name="2. Subtheme and dimension summaries (subthe_dimen_sr.py)",
            description=(
                "Input: comments.csv.\n"
                "Output:\n"
                "- one JSON per subtheme in <outdir>/subtheme_<slug>.json\n"
                "- one JSON per dimension in <dim-outdir>/dimension_<slug>.json (optional)\n\n"
                "The script will:\n"
                "- group rows by subtheme (positive / negative only)\n"
                "- build simple stats per subtheme\n"
                "- reuse these stats to build stats per dimension\n"
                "- choose up to N examples per label (controlled by --max-examples)\n"
                "- call DeepSeek to write JSON summaries\n"
                "- if the LLM fails (not quota), write an ERROR JSON instead\n\n"
                "Key flags (see subthe_dimen_sr.py):\n"
                "- --csv           : input comments.csv\n"
                "- --outdir        : folder for subtheme JSON files\n"
                "- --dim-outdir    : folder for dimension JSON files (optional)\n"
                "- --model         : LLM model name (default deepseek/deepseek-chat-v3.1:free)\n"
                "- --max-examples  : max examples per label (int, default 5)\n"
                "- --limit-subthemes : only process first N subthemes (0 = all)\n"
                "- --overwrite     : control overwrite behaviour:\n"
                "    * default / 'none' : keep existing files, skip them\n"
                "    * 'all'            : overwrite all existing files\n"
                "    * 'A,B,C'          : only overwrite labels whose name contains A or B or C\n"
            ),
            command=(
                "python subthe_dimen_sr.py "
                f"--csv {paths['comments_csv']} "
                f"--outdir {paths['subthemes_outdir']} "
                f"--dim-outdir {paths['dimensions_outdir']} "
                "--max-examples 10"
            ),
        )
    )

    return steps


def print_reporting_pipeline(root: Path | str | None = None) -> None:
    """
    Print the two reporting steps in a simple checklist format.
    """
    steps = reporting_steps(root)
    for i, step in enumerate(steps, start=1):
        print(f"{i}. {step.name}")
        print("   " + "-" * max(4, len(step.name)))
        for line in step.description.splitlines():
            if line.strip():
                print(f"   {line}")
            else:
                print()
        print(f"   Command: {step.command}")
        print()


if __name__ == "__main__":
    # Example usage: python suggestions.py
    print_reporting_pipeline()
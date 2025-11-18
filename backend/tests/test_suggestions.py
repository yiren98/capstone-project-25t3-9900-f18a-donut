# Tests for suggestions.reporting_steps
# Features:
# - Call reporting_steps with a temporary root path
# - Ensure it returns exactly two steps
# - Check that commands call overall_sr.py and subthe_dimen_sr.py
# - Verify that the commands include the provided root path
#
# Usage:
#   pytest tests/test_suggestions.py -q

from pathlib import Path
from suggestions import reporting_steps

def test_reporting_steps_basic(tmp_path):
    # Call reporting_steps with a temporary root path
    steps = reporting_steps(tmp_path)

    # Should have exactly 2 steps
    assert len(steps) == 2

    step1, step2 = steps

    # Step 1 is overall summary
    assert "overall_sr.py" in step1.command
    # Step 2 is subtheme/dimension summaries
    assert "subthe_dimen_sr.py" in step2.command

    # Commands should use the given root path
    # (we just check the path prefix is there as a string)
    root_str = str(tmp_path)
    assert root_str in step1.command
    assert root_str in step2.command

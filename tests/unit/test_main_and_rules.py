"""Tests for __main__.py entry point and rules package error handling."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_python_m_behave_doctor_version() -> None:
    """`python -m behave_doctor --version` exits 0 and prints the version."""
    result = subprocess.run(
        [sys.executable, "-m", "behave_doctor", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "1.2.0" in result.stdout


def test_python_m_behave_doctor_scan() -> None:
    """`python -m behave_doctor scan` runs and exits with 0 or 1."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "behave_doctor",
            "scan",
            str(FIXTURES / "sample_project"),
            "--no-color",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in (0, 1)
    assert "Scanning" in result.stdout


def test_python_m_behave_doctor_no_args_runs_scan() -> None:
    """`python -m behave_doctor` with no args defaults to scan on cwd."""
    result = subprocess.run(
        [sys.executable, "-m", "behave_doctor"],
        capture_output=True,
        text=True,
        cwd=str(FIXTURES / "sample_project"),
        check=False,
    )
    assert result.returncode in (0, 1)
    assert "Scanning" in result.stdout


def test_rules_package_loads_all_rules() -> None:
    """The rules package loads all rule instances without error."""
    from behave_doctor.rules import get_all_rules

    rules = get_all_rules()
    assert len(rules) >= 10
    # Every rule must have a unique ID.
    ids = [r.id for r in rules]
    assert len(ids) == len(set(ids))


def test_rules_get_rule_returns_none_for_unknown() -> None:
    """get_rule returns None for an unknown rule ID."""
    from behave_doctor.rules import get_rule

    assert get_rule("BD999") is None


def test_rules_get_rule_returns_rule_for_known() -> None:
    """get_rule returns the rule instance for a known rule ID."""
    from behave_doctor.rules import get_rule

    rule = get_rule("BD101")
    assert rule is not None
    assert rule.id == "BD101"

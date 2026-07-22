from __future__ import annotations

from pathlib import Path

from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Category, Severity


def test_diagnostic_defaults() -> None:
    diag = Diagnostic(
        rule_id="BD301",
        rule_name="unused-step-def",
        severity=Severity.WARNING,
        category=Category.COVERAGE,
        message="Unused step definition",
    )
    assert diag.file is None
    assert diag.line is None
    assert diag.suggestion is None
    assert diag.metadata == {}


def test_diagnostic_is_frozen() -> None:
    diag = Diagnostic(
        rule_id="BD301",
        rule_name="unused-step-def",
        severity=Severity.WARNING,
        category=Category.COVERAGE,
        message="Unused step definition",
        file=Path("steps/auth.py"),
        line=10,
    )
    try:
        diag.message = "changed"  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("Diagnostic should be frozen")


def test_diagnostic_metadata_independent() -> None:
    a = Diagnostic(
        rule_id="BD1",
        rule_name="r",
        severity=Severity.INFO,
        category=Category.STRUCTURE,
        message="m",
    )
    b = Diagnostic(
        rule_id="BD2",
        rule_name="r",
        severity=Severity.INFO,
        category=Category.STRUCTURE,
        message="m",
    )
    a.metadata["k"] = "v"
    assert b.metadata == {}

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Category, Severity
from behave_doctor.model.project_report import ProjectReport, ProjectStatistics


def _diag(severity: Severity) -> Diagnostic:
    return Diagnostic(
        rule_id="BD000",
        rule_name="test-rule",
        severity=severity,
        category=Category.STRUCTURE,
        message="msg",
    )


def test_exit_code_zero_without_errors() -> None:
    report = ProjectReport(
        project_path=Path("."),
        diagnostics=[_diag(Severity.WARNING), _diag(Severity.INFO)],
        statistics=ProjectStatistics(),
        scanned_at=datetime.now(),
        scan_duration_ms=0,
    )
    assert report.exit_code == 0
    assert report.has_errors is False


def test_exit_code_one_with_errors() -> None:
    report = ProjectReport(
        project_path=Path("."),
        diagnostics=[_diag(Severity.ERROR), _diag(Severity.WARNING)],
        statistics=ProjectStatistics(),
        scanned_at=datetime.now(),
        scan_duration_ms=0,
    )
    assert report.exit_code == 1
    assert report.has_errors is True


def test_errors_and_warnings_filter_correctly() -> None:
    report = ProjectReport(
        project_path=Path("."),
        diagnostics=[
            _diag(Severity.ERROR),
            _diag(Severity.WARNING),
            _diag(Severity.INFO),
            _diag(Severity.ERROR),
        ],
        statistics=ProjectStatistics(),
        scanned_at=datetime.now(),
        scan_duration_ms=0,
    )
    assert len(report.errors) == 2
    assert len(report.warnings) == 1
    assert all(d.severity is Severity.ERROR for d in report.errors)
    assert all(d.severity is Severity.WARNING for d in report.warnings)

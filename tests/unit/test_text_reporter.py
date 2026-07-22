from __future__ import annotations

from datetime import datetime
from pathlib import Path

from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Category, Severity
from behave_doctor.model.project_report import ProjectReport, ProjectStatistics
from behave_doctor.reporters.text import TextReporter


def _diag(
    severity: Severity,
    rule_id: str = "BD302",
    message: str = "msg",
    suggestion: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        rule_id=rule_id,
        rule_name="test-rule",
        severity=severity,
        category=Category.COVERAGE,
        message=message,
        file=Path("features/login.feature"),
        line=14,
        suggestion=suggestion,
    )


def _report(diagnostics: list[Diagnostic]) -> ProjectReport:
    return ProjectReport(
        project_path=Path("myproject/"),
        diagnostics=diagnostics,
        statistics=ProjectStatistics(features=3, scenarios=12, steps=47, step_definitions=8),
        scanned_at=datetime(2024, 1, 1, 0, 0, 0),
        scan_duration_ms=300,
    )


def test_output_contains_header_and_stats() -> None:
    out = TextReporter(use_color=False).format(_report([]))
    assert "Scanning myproject" in out
    assert "3 features" in out
    assert "12 scenarios" in out


def test_diagnostics_ordered_by_severity() -> None:
    diags = [
        _diag(Severity.WARNING, "BD301", "warn"),
        _diag(Severity.ERROR, "BD302", "err"),
        _diag(Severity.INFO, "BD101", "info"),
    ]
    out = TextReporter(use_color=False).format(_report(diags))
    err_pos = out.index("BD302")
    warn_pos = out.index("BD301")
    info_pos = out.index("BD101")
    assert err_pos < warn_pos < info_pos


def test_color_codes_present_when_enabled() -> None:
    out = TextReporter(use_color=True).format(_report([_diag(Severity.ERROR)]))
    assert "\033[31m" in out
    assert "\033[0m" in out


def test_color_codes_absent_when_disabled() -> None:
    out = TextReporter(use_color=False).format(_report([_diag(Severity.ERROR)]))
    assert "\033[" not in out


def test_quiet_shows_only_errors() -> None:
    diags = [_diag(Severity.ERROR, "BD302", "err"), _diag(Severity.WARNING, "BD301", "warn")]
    out = TextReporter(use_color=False, quiet=True).format(_report(diags))
    assert "BD302" in out
    assert "BD301" not in out


def test_verbose_shows_suggestion() -> None:
    diag = _diag(Severity.WARNING, suggestion="Remove the unused definition")
    out = TextReporter(use_color=False, verbose=True).format(_report([diag]))
    assert "Suggestion: Remove the unused definition" in out


def test_summary_line_present() -> None:
    diags = [_diag(Severity.ERROR), _diag(Severity.WARNING), _diag(Severity.WARNING)]
    out = TextReporter(use_color=False).format(_report(diags))
    assert "1 errors, 2 warnings in 0.3s" in out

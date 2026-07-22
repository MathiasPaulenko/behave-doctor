from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Category, Severity
from behave_doctor.model.project_report import ProjectReport, ProjectStatistics
from behave_doctor.reporters.json_reporter import JsonReporter


def _diag() -> Diagnostic:
    return Diagnostic(
        rule_id="BD301",
        rule_name="unused-step-def",
        severity=Severity.WARNING,
        category=Category.COVERAGE,
        message="Unused step definition",
        file=Path("features/steps/auth.py"),
        line=23,
        suggestion="Remove it",
        metadata={"def_id": "auth.user_logged_in"},
    )


def _report(diagnostics: list[Diagnostic]) -> ProjectReport:
    return ProjectReport(
        project_path=Path("myproject/"),
        diagnostics=diagnostics,
        statistics=ProjectStatistics(
            features=3,
            scenarios=12,
            steps=47,
            step_definitions=8,
            tags=5,
            total_tag_usages=10,
            average_steps_per_scenario=3.9,
            unused_step_definitions=1,
            undefined_steps=0,
        ),
        scanned_at=datetime(2024, 1, 1, 12, 0, 0),
        scan_duration_ms=300,
    )


def test_output_is_valid_json() -> None:
    out = JsonReporter().format(_report([_diag()]))
    data = json.loads(out)
    assert isinstance(data, dict)


def test_output_has_correct_top_level_keys() -> None:
    out = JsonReporter().format(_report([_diag()]))
    data = json.loads(out)
    assert set(data) == {
        "project_path",
        "scanned_at",
        "scan_duration_ms",
        "statistics",
        "diagnostics",
    }


def test_path_serialized_as_string() -> None:
    out = JsonReporter().format(_report([_diag()]))
    data = json.loads(out)
    assert data["diagnostics"][0]["file"] == "features/steps/auth.py"


def test_datetime_serialized_as_iso8601() -> None:
    out = JsonReporter().format(_report([]))
    data = json.loads(out)
    assert data["scanned_at"] == "2024-01-01T12:00:00"


def test_severity_and_category_as_value_strings() -> None:
    out = JsonReporter().format(_report([_diag()]))
    data = json.loads(out)
    diag = data["diagnostics"][0]
    assert diag["severity"] == "warning"
    assert diag["category"] == "coverage"


def test_keys_are_sorted() -> None:
    out = JsonReporter().format(_report([_diag()]))
    # Verify keys appear in sorted order by checking the raw string positions.
    assert out.index("diagnostics") < out.index("project_path") < out.index("scanned_at")


def test_empty_diagnostics_produces_valid_output() -> None:
    out = JsonReporter().format(_report([]))
    data = json.loads(out)
    assert data["diagnostics"] == []

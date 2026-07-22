from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Category, Severity
from behave_doctor.model.project_report import ProjectReport, ProjectStatistics
from behave_doctor.reporters.sarif import SarifReporter


def _diag(severity: Severity = Severity.WARNING) -> Diagnostic:
    return Diagnostic(
        rule_id="BD301",
        rule_name="unused-step-def",
        severity=severity,
        category=Category.COVERAGE,
        message="Unused step definition",
        file=Path("myproject/features/steps/auth.py"),
        line=23,
    )


def _report(diagnostics: list[Diagnostic]) -> ProjectReport:
    return ProjectReport(
        project_path=Path("myproject/"),
        diagnostics=diagnostics,
        statistics=ProjectStatistics(),
        scanned_at=datetime(2024, 1, 1),
        scan_duration_ms=300,
    )


def test_output_is_valid_sarif() -> None:
    out = SarifReporter().format(_report([_diag()]))
    data = json.loads(out)
    assert data["version"] == "2.1.0"
    assert data["$schema"].endswith("sarif-schema-2.1.0.json")


def test_rules_in_tool_driver() -> None:
    out = SarifReporter().format(_report([_diag()]))
    data = json.loads(out)
    rules = data["runs"][0]["tool"]["driver"]["rules"]
    assert isinstance(rules, list)
    assert any(r["id"] == "BD101" for r in rules)


def test_results_in_runs() -> None:
    out = SarifReporter().format(_report([_diag()]))
    data = json.loads(out)
    results = data["runs"][0]["results"]
    assert len(results) == 1
    assert results[0]["ruleId"] == "BD301"


def test_severity_mapping() -> None:
    out = SarifReporter().format(_report([_diag(Severity.ERROR)]))
    data = json.loads(out)
    assert data["runs"][0]["results"][0]["level"] == "error"

    out = SarifReporter().format(_report([_diag(Severity.INFO)]))
    data = json.loads(out)
    assert data["runs"][0]["results"][0]["level"] == "note"


def test_locations_use_relative_paths() -> None:
    out = SarifReporter().format(_report([_diag()]))
    data = json.loads(out)
    uri = data["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"][
        "uri"
    ]
    assert uri == "features/steps/auth.py"


def test_empty_diagnostics_produces_valid_sarif() -> None:
    out = SarifReporter().format(_report([]))
    data = json.loads(out)
    assert data["runs"][0]["results"] == []

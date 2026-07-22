from __future__ import annotations

from pathlib import Path

import behave_doctor
from behave_doctor import DoctorConfig, ProjectReport, scan_project

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_public_scan_project_returns_report() -> None:
    report = scan_project(FIXTURES / "sample_project")
    assert isinstance(report, ProjectReport)
    assert report.statistics.features == 2
    assert report.exit_code in (0, 1)


def test_public_scan_project_with_custom_config() -> None:
    config = DoctorConfig(rules={"BD101": {"enabled": False}})
    report = scan_project(FIXTURES / "sample_project", config=config)
    rule_ids = {d.rule_id for d in report.diagnostics}
    assert "BD101" not in rule_ids


def test_public_api_surface() -> None:
    for name in [
        "scan_project",
        "ProjectReport",
        "ProjectStatistics",
        "Diagnostic",
        "DoctorConfig",
        "Severity",
        "Category",
        "Rule",
        "StepDefinition",
        "StepMatch",
        "DependencyGraph",
    ]:
        assert name in behave_doctor.__all__
        assert hasattr(behave_doctor, name)


def test_report_attributes_accessible() -> None:
    report = scan_project(FIXTURES / "undefined_steps_project")
    assert report.diagnostics is not None
    assert report.statistics is not None
    assert isinstance(report.exit_code, int)

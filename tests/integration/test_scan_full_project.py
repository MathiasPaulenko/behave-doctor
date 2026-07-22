from __future__ import annotations

from pathlib import Path

from behave_doctor.core import build_report
from behave_doctor.model.config import DoctorConfig

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_scan_sample_project_returns_report() -> None:
    report = build_report(FIXTURES / "sample_project", DoctorConfig())
    assert report.statistics.features == 2
    assert report.statistics.scenarios == 5
    assert report.statistics.steps > 0
    assert report.exit_code in (0, 1)


def test_scan_undefined_steps_project_reports_bd302() -> None:
    report = build_report(FIXTURES / "undefined_steps_project", DoctorConfig())
    rule_ids = {d.rule_id for d in report.diagnostics}
    assert "BD302" in rule_ids
    assert report.exit_code == 1


def test_scan_unused_steps_project_reports_bd301() -> None:
    report = build_report(FIXTURES / "unused_steps_project", DoctorConfig())
    rule_ids = {d.rule_id for d in report.diagnostics}
    assert "BD301" in rule_ids


def test_scan_duplicate_defs_project_reports_bd201() -> None:
    report = build_report(FIXTURES / "duplicate_defs_project", DoctorConfig())
    rule_ids = {d.rule_id for d in report.diagnostics}
    assert "BD201" in rule_ids
    assert report.exit_code == 1


def test_scan_circular_deps_project_reports_bd501() -> None:
    report = build_report(FIXTURES / "circular_deps_project", DoctorConfig())
    rule_ids = {d.rule_id for d in report.diagnostics}
    assert "BD501" in rule_ids

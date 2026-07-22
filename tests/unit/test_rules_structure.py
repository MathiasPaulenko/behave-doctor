from __future__ import annotations

from pathlib import Path

from behave_doctor.model.config import DoctorConfig
from behave_doctor.model.dependency_graph import DependencyGraph
from behave_doctor.model.enums import Category, Severity
from behave_doctor.rules import clear_registry, get_rule
from behave_doctor.rules.base import RuleContext
from behave_doctor.rules.structure import (
    FeatureCount,
    ScenarioCount,
    StepCount,
    TagCoverage,
)
from behave_doctor.scanner import scan_features

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _context() -> RuleContext:
    project = scan_features(FIXTURES / "sample_project", DoctorConfig())
    return RuleContext(
        project=project,
        step_definitions=[],
        dependency_graph=DependencyGraph(),
        config=DoctorConfig(),
    )


def _check(rule_cls, expected_id: str) -> None:
    clear_registry()
    rule = rule_cls()
    diagnostics = rule.check(_context())
    assert len(diagnostics) == 1
    diag = diagnostics[0]
    assert diag.rule_id == expected_id
    assert diag.severity is Severity.INFO
    assert diag.category is Category.STRUCTURE


def test_bd101_feature_count() -> None:
    _check(FeatureCount, "BD101")
    assert "features found" in FeatureCount().check(_context())[0].message


def test_bd102_scenario_count() -> None:
    _check(ScenarioCount, "BD102")


def test_bd103_step_count() -> None:
    _check(StepCount, "BD103")


def test_bd104_tag_coverage() -> None:
    _check(TagCoverage, "BD104")
    diag = TagCoverage().check(_context())[0]
    assert "unique tags" in diag.message
    assert "total tag usages" in diag.message


def test_all_four_rules_registered() -> None:
    # Re-import the package to repopulate the registry after clear.
    import behave_doctor.rules  # noqa: F401

    behave_doctor.rules._discover_rules()  # type: ignore[attr-defined]
    for rule_id in ("BD101", "BD102", "BD103", "BD104"):
        assert get_rule(rule_id) is not None

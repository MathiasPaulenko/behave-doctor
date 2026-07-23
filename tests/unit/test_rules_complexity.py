from __future__ import annotations

from pathlib import Path

from behave_model import Feature, Location, Project

from behave_doctor.model.config import DoctorConfig
from behave_doctor.model.dependency_graph import DependencyGraph
from behave_doctor.model.enums import Category, Severity
from behave_doctor.rules.base import RuleContext
from behave_doctor.rules.complexity import (
    FeatureTooLarge,
    ScenarioTooManySteps,
    StepTooManyParams,
)
from behave_doctor.scanner import scan_features, scan_steps

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _ctx(
    project_dir: str,
    *,
    config: DoctorConfig | None = None,
    with_steps: bool = False,
) -> RuleContext:
    root = FIXTURES / project_dir
    project = scan_features(root, DoctorConfig())
    steps = scan_steps(root / "features" / "steps", DoctorConfig()) if with_steps else []
    return RuleContext(
        project=project,
        step_definitions=steps,
        dependency_graph=DependencyGraph(),
        config=config or DoctorConfig(),
    )


def test_bd401_detects_scenario_with_too_many_steps() -> None:
    root = FIXTURES / "oversized_project"
    features = root / "features"
    features.mkdir(parents=True, exist_ok=True)
    feature_file = features / "big.feature"
    lines = ["Feature: Big", ""]
    lines.append("  Scenario: Big scenario")
    for i in range(12):
        lines.append(f"    Given step {i}")
    feature_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        ctx = _ctx("oversized_project")
        diagnostics = ScenarioTooManySteps().check(ctx)
        assert len(diagnostics) == 1
        diag = diagnostics[0]
        assert diag.rule_id == "BD401"
        assert diag.severity is Severity.WARNING
        assert diag.category is Category.COMPLEXITY
        assert "12 steps" in diag.message
    finally:
        feature_file.unlink()


def test_bd401_ignores_non_dict_override() -> None:
    root = FIXTURES / "oversized_project"
    features = root / "features"
    features.mkdir(parents=True, exist_ok=True)
    feature_file = features / "big.feature"
    lines = ["Feature: Big", ""]
    lines.append("  Scenario: Big scenario")
    for i in range(12):
        lines.append(f"    Given step {i}")
    feature_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        ctx = _ctx(
            "oversized_project",
            config=DoctorConfig(rules={"BD401": [1, 2, 3]}),
        )
        diagnostics = ScenarioTooManySteps().check(ctx)
        # The non-dict override is ignored, so the default threshold (10) applies.
        assert len(diagnostics) == 1
        assert "12 steps" in diagnostics[0].message
    finally:
        feature_file.unlink()


def test_bd401_respects_custom_max_steps() -> None:
    root = FIXTURES / "oversized_project"
    features = root / "features"
    features.mkdir(parents=True, exist_ok=True)
    feature_file = features / "big.feature"
    lines = ["Feature: Big", "", "  Scenario: Small scenario"]
    for i in range(5):
        lines.append(f"    Given step {i}")
    feature_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        ctx = _ctx(
            "oversized_project",
            config=DoctorConfig(rules={"BD401": {"max_steps": 3}}),
        )
        diagnostics = ScenarioTooManySteps().check(ctx)
        assert len(diagnostics) == 1
        assert "max 3" in diagnostics[0].message
    finally:
        feature_file.unlink()


def test_bd402_detects_step_with_too_many_params() -> None:
    ctx = _ctx("oversized_project", with_steps=True)
    diagnostics = StepTooManyParams().check(ctx)
    assert len(diagnostics) == 1
    diag = diagnostics[0]
    assert diag.rule_id == "BD402"
    assert diag.severity is Severity.WARNING
    assert "6 parameters" in diag.message


def test_bd402_respects_custom_max_params() -> None:
    ctx = _ctx(
        "oversized_project",
        with_steps=True,
        config=DoctorConfig(rules={"BD402": {"max_params": 2}}),
    )
    diagnostics = StepTooManyParams().check(ctx)
    assert len(diagnostics) == 1
    assert "max 2" in diagnostics[0].message


def test_bd403_detects_oversized_feature_file() -> None:
    root = FIXTURES / "oversized_project"
    features = root / "features"
    features.mkdir(parents=True, exist_ok=True)
    feature_file = features / "big.feature"
    lines = ["Feature: Big", ""]
    for i in range(30):
        lines.append(f"  Scenario: Scenario {i}")
        lines.append("    Given a step")
        lines.append("")  # pad to exceed 50 lines
    feature_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        ctx = _ctx(
            "oversized_project",
            config=DoctorConfig(rules={"BD403": {"max_lines": 50}}),
        )
        diagnostics = FeatureTooLarge().check(ctx)
        assert len(diagnostics) == 1
        diag = diagnostics[0]
        assert diag.rule_id == "BD403"
        assert diag.severity is Severity.WARNING
        assert "lines" in diag.message
    finally:
        feature_file.unlink()


def test_bd403_skips_unreadable_feature_file(tmp_path: Path) -> None:
    """FeatureTooLarge must not crash when a feature file cannot be read."""
    bad = tmp_path / "bad.feature"
    bad.write_bytes(b"\xff\xfe")
    feature = Feature(name="Bad", location=Location(filename=str(bad), line=1))
    project = Project(features=[feature], global_tags=[], metadata=None)
    ctx = RuleContext(
        project=project,
        step_definitions=[],
        dependency_graph=DependencyGraph(),
        config=DoctorConfig(rules={"BD403": {"max_lines": 1}}),
    )
    diagnostics = FeatureTooLarge().check(ctx)
    assert diagnostics == []

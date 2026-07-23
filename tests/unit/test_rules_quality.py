from __future__ import annotations

from pathlib import Path

from behave_model import Project

from behave_doctor.model.config import DoctorConfig
from behave_doctor.model.dependency_graph import DependencyGraph
from behave_doctor.model.enums import Category, Severity
from behave_doctor.rules.base import RuleContext
from behave_doctor.rules.quality import (
    DuplicateStepDefs,
    FeatureTooManyScenarios,
    InconsistentTagCasing,
    ScenarioNoTags,
)
from behave_doctor.scanner import scan_features, scan_steps

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _ctx(project_dir: str, *, config: DoctorConfig | None = None) -> RuleContext:
    root = FIXTURES / project_dir
    project = scan_features(root, DoctorConfig())
    steps = scan_steps(root / "features" / "steps", DoctorConfig())
    return RuleContext(
        project=project,
        step_definitions=steps,
        dependency_graph=DependencyGraph(),
        config=config or DoctorConfig(),
    )


def test_bd201_detects_duplicate_step_patterns() -> None:
    ctx = _ctx("duplicate_defs_project")
    diagnostics = DuplicateStepDefs().check(ctx)
    assert len(diagnostics) == 1
    diag = diagnostics[0]
    assert diag.rule_id == "BD201"
    assert diag.severity is Severity.ERROR
    assert diag.category is Category.QUALITY
    assert "Duplicate step definition" in diag.message


def test_bd201_distinguishes_keywords(tmp_path: Path) -> None:
    """Same pattern with different keywords is not a duplicate; same keyword is."""
    steps_dir = tmp_path / "steps"
    steps_dir.mkdir()
    (steps_dir / "steps.py").write_text(
        "from behave import given, when, step\n"
        '@given("a thing")\n'
        "def g(): pass\n"
        '@when("a thing")\n'
        "def w(): pass\n"
        '@step("a thing")\n'
        "def s(): pass\n"
        '@given("a thing")\n'
        "def g2(): pass\n",
        encoding="utf-8",
    )
    step_defs = scan_steps(steps_dir, DoctorConfig())
    ctx = RuleContext(
        project=Project(features=[], global_tags=[], metadata=None),
        step_definitions=step_defs,
        dependency_graph=DependencyGraph(),
        config=DoctorConfig(),
    )
    diagnostics = DuplicateStepDefs().check(ctx)
    assert len(diagnostics) == 1
    assert "a thing" in diagnostics[0].message


def test_bd202_detects_untagged_scenarios() -> None:
    ctx = _ctx("untagged_scenarios_project")
    diagnostics = ScenarioNoTags().check(ctx)
    assert len(diagnostics) == 2
    assert all(d.severity is Severity.WARNING for d in diagnostics)
    assert all(d.rule_id == "BD202" for d in diagnostics)


def test_bd203_detects_oversized_feature_default_threshold(tmp_path: Path) -> None:
    features = tmp_path / "features"
    features.mkdir()
    feature_file = features / "big.feature"
    lines = ["Feature: Big", ""]
    for i in range(25):
        lines.append(f"  Scenario: Scenario {i}")
        lines.append("    Given a step")
    feature_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    project = scan_features(tmp_path, DoctorConfig())
    ctx = RuleContext(
        project=project,
        step_definitions=[],
        dependency_graph=DependencyGraph(),
        config=DoctorConfig(),
    )
    diagnostics = FeatureTooManyScenarios().check(ctx)
    assert len(diagnostics) == 1
    assert diagnostics[0].severity is Severity.WARNING
    assert "25 scenarios" in diagnostics[0].message


def test_bd203_respects_custom_max_scenarios(tmp_path: Path) -> None:
    features = tmp_path / "features"
    features.mkdir()
    feature_file = features / "big.feature"
    lines = ["Feature: Big", ""]
    for i in range(5):
        lines.append(f"  Scenario: Scenario {i}")
        lines.append("    Given a step")
    feature_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    project = scan_features(tmp_path, DoctorConfig())
    ctx = RuleContext(
        project=project,
        step_definitions=[],
        dependency_graph=DependencyGraph(),
        config=DoctorConfig(rules={"BD203": {"max_scenarios": 3}}),
    )
    diagnostics = FeatureTooManyScenarios().check(ctx)
    assert len(diagnostics) == 1
    assert "max 3" in diagnostics[0].message


def test_bd204_detects_inconsistent_tag_casing() -> None:
    ctx = _ctx("tag_casing_project")
    diagnostics = InconsistentTagCasing().check(ctx)
    assert len(diagnostics) == 1
    diag = diagnostics[0]
    assert diag.rule_id == "BD204"
    assert diag.severity is Severity.WARNING
    variants = diag.metadata["variants"]
    assert "@SmokeTest" in variants
    assert "@smoke_test" in variants

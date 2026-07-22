from __future__ import annotations

from pathlib import Path

from behave_doctor.graph.builder import build_graph
from behave_doctor.model.config import DoctorConfig
from behave_doctor.model.enums import Category, Severity
from behave_doctor.rules.base import RuleContext
from behave_doctor.rules.coverage import (
    OrphanScenario,
    UndefinedStep,
    UnusedStepDef,
    UnusedTag,
)
from behave_doctor.scanner import scan_features, scan_steps

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _ctx(project_dir: str, *, config: DoctorConfig | None = None) -> RuleContext:
    root = FIXTURES / project_dir
    project = scan_features(root, DoctorConfig())
    steps = scan_steps(root / "features" / "steps", DoctorConfig())
    graph = build_graph(project, steps)
    return RuleContext(
        project=project,
        step_definitions=steps,
        dependency_graph=graph,
        config=config or DoctorConfig(),
    )


def test_bd301_detects_unused_step_definitions() -> None:
    ctx = _ctx("unused_steps_project")
    diagnostics = UnusedStepDef().check(ctx)
    assert len(diagnostics) == 1
    diag = diagnostics[0]
    assert diag.rule_id == "BD301"
    assert diag.severity is Severity.WARNING
    assert diag.category is Category.COVERAGE
    assert "unused" in diag.message.lower()


def test_bd302_detects_undefined_steps() -> None:
    ctx = _ctx("undefined_steps_project")
    diagnostics = UndefinedStep().check(ctx)
    assert len(diagnostics) == 1
    diag = diagnostics[0]
    assert diag.rule_id == "BD302"
    assert diag.severity is Severity.ERROR
    assert "Undefined step" in diag.message


def test_bd303_detects_tags_used_once() -> None:
    ctx = _ctx("orphan_project")
    diagnostics = UnusedTag().check(ctx)
    # @shared used twice (not reported), @uniqueonly used once (reported)
    tags = {d.metadata["tag"] for d in diagnostics}
    assert "@uniqueonly" in tags
    assert "@shared" not in tags
    assert all(d.severity is Severity.INFO for d in diagnostics)


def test_bd303_excludes_config_exclude_tags() -> None:
    ctx = _ctx(
        "orphan_project",
        config=DoctorConfig(exclude_tags=["@shared"]),
    )
    diagnostics = UnusedTag().check(ctx)
    tags = {d.metadata["tag"] for d in diagnostics}
    assert "@shared" not in tags


def test_bd304_detects_orphan_scenarios() -> None:
    ctx = _ctx("orphan_project")
    diagnostics = OrphanScenario().check(ctx)
    assert len(diagnostics) == 1
    diag = diagnostics[0]
    assert diag.rule_id == "BD304"
    assert diag.severity is Severity.WARNING
    assert "Unique tag scenario" in diag.message

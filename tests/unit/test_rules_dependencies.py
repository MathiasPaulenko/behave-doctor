from __future__ import annotations

from pathlib import Path

from behave_doctor.graph.builder import build_graph
from behave_doctor.model.config import DoctorConfig
from behave_doctor.model.dependency_graph import DependencyGraph
from behave_doctor.model.enums import Category, Severity
from behave_doctor.rules.base import RuleContext
from behave_doctor.rules.dependencies import (
    CircularDependency,
    MissingStepModule,
    UnusedImport,
)
from behave_doctor.scanner import scan_features, scan_steps

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _ctx(project_dir: str) -> RuleContext:
    root = FIXTURES / project_dir
    project = scan_features(root, DoctorConfig())
    steps = scan_steps(root / "features" / "steps", DoctorConfig())
    graph = build_graph(project, steps)
    return RuleContext(
        project=project,
        step_definitions=steps,
        dependency_graph=graph,
        config=DoctorConfig(),
    )


def test_bd501_detects_circular_dependency() -> None:
    ctx = _ctx("circular_deps_project")
    diagnostics = CircularDependency().check(ctx)
    assert len(diagnostics) >= 1
    diag = diagnostics[0]
    assert diag.rule_id == "BD501"
    assert diag.severity is Severity.ERROR
    assert diag.category is Category.DEPENDENCY
    assert "Circular dependency" in diag.message


def test_bd502_detects_unused_imports() -> None:
    ctx = _ctx("circular_deps_project")
    diagnostics = UnusedImport().check(ctx)
    # `behave` is used via decorators; helper imports are used. Expect none
    # in the clean circular fixture, but the rule must run without error.
    assert all(d.rule_id == "BD502" for d in diagnostics)
    assert all(d.severity is Severity.WARNING for d in diagnostics)


def test_bd502_detects_unused_import_in_fixture(tmp_path: Path) -> None:
    steps = tmp_path / "features" / "steps"
    steps.mkdir(parents=True)
    (steps / "unused.py").write_text(
        'import os\nfrom behave import given\n\n\n@given("a step")\ndef step():\n    pass\n',
        encoding="utf-8",
    )
    project = scan_features(tmp_path, DoctorConfig())
    step_defs = scan_steps(steps, DoctorConfig())
    ctx = RuleContext(
        project=project,
        step_definitions=step_defs,
        dependency_graph=DependencyGraph(),
        config=DoctorConfig(),
    )
    diagnostics = UnusedImport().check(ctx)
    assert any(d.metadata["import"] == "os" for d in diagnostics)


def test_bd503_no_step_definitions_reports_missing_directory() -> None:
    root = FIXTURES / "undefined_steps_project"
    project = scan_features(root, DoctorConfig())
    # Use empty steps to simulate missing modules.
    graph = build_graph(project, [])
    ctx = RuleContext(
        project=project,
        step_definitions=[],
        dependency_graph=graph,
        config=DoctorConfig(),
    )
    diagnostics = MissingStepModule().check(ctx)
    assert len(diagnostics) == 1
    assert diagnostics[0].severity is Severity.ERROR
    assert "no step definitions" in diagnostics[0].message


def test_bd503_with_some_definitions_does_not_duplicate_bd302() -> None:
    """When step definitions exist, BD503 must not report undefined steps.

    BD302 already reports undefined steps when definitions exist. BD503 only
    fires when there are zero step definitions (the "missing module" case).
    """
    ctx = _ctx("undefined_steps_project")
    diagnostics = MissingStepModule().check(ctx)
    assert diagnostics == []

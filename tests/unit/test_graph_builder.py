from __future__ import annotations

from pathlib import Path

from behave_doctor.graph.builder import build_graph, normalize_step_text
from behave_doctor.model.config import DoctorConfig
from behave_doctor.scanner import scan_features, scan_steps

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
MATCHING = FIXTURES / "matching_project"


def _build() -> object:
    project = scan_features(MATCHING, DoctorConfig())
    steps = scan_steps(MATCHING / "features" / "steps", DoctorConfig())
    return build_graph(project, steps)


def test_normalize_step_text_strips_keyword() -> None:
    assert normalize_step_text("Given the user is logged in") == "the user is logged in"
    assert normalize_step_text("  And   multiple   spaces ") == "multiple spaces"


def test_exact_match() -> None:
    graph = _build()
    matches = [m for m in graph.step_matches if m.step_definition is not None and not m.ambiguous]
    texts = {m.step.name for m in matches}
    assert "the user is logged in" in texts


def test_no_match_for_undefined_step() -> None:
    graph = _build()
    undefined = [m for m in graph.step_matches if m.step_definition is None]
    assert any(m.step.name == "an undefined step here" for m in undefined)


def test_ambiguous_match() -> None:
    graph = _build()
    ambiguous = [m for m in graph.step_matches if m.ambiguous]
    assert any(m.step.name == "the user should be logged in" for m in ambiguous)


def test_feature_steps_mapping() -> None:
    graph = _build()
    assert "Login" in graph.feature_steps
    assert len(graph.feature_steps["Login"]) >= 1


def test_step_usage_mapping() -> None:
    graph = _build()
    assert any("login_steps" in def_id for def_id in graph.step_usage)


def test_step_matches_count_equals_total_steps() -> None:
    project = scan_features(MATCHING, DoctorConfig())
    graph = _build()
    assert len(graph.step_matches) == len(project.all_steps())


def test_module_imports_extracted() -> None:
    graph = _build()
    assert "login_steps" in graph.module_imports
    assert "behave" in graph.module_imports["login_steps"]

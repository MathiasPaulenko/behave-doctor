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


def test_extract_relative_imports(tmp_path: Path) -> None:
    """_extract_module_imports should resolve relative imports to dotted names."""
    from behave_doctor.graph.builder import _extract_module_imports

    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "x.py").write_text(
        "from . import y\nfrom .. import login_steps\nfrom .z import helper\n",
        encoding="utf-8",
    )
    imports = _extract_module_imports(sub / "x.py", "sub.x")
    assert "sub.y" in imports
    assert "login_steps" in imports
    assert "sub.z" in imports


def test_scenario_outline_steps_expanded_by_examples(tmp_path: Path) -> None:
    """Scenario Outline steps with <placeholder> must be expanded against example rows."""
    steps_dir = tmp_path / "features" / "steps"
    steps_dir.mkdir(parents=True)
    (steps_dir / "steps.py").write_text(
        'from behave import given\n@given("a {thing}")\ndef step(thing): pass\n',
        encoding="utf-8",
    )
    (tmp_path / "features" / "outline.feature").write_text(
        "Feature: outline\n\n"
        "  Scenario Outline: example\n"
        "    Given a <thing>\n\n"
        "    Examples:\n"
        "      | thing |\n"
        "      | apple |\n"
        "      | pear  |\n",
        encoding="utf-8",
    )
    project = scan_features(tmp_path, DoctorConfig())
    steps = scan_steps(steps_dir, DoctorConfig())
    graph = build_graph(project, steps)
    assert len(graph.step_matches) == 2
    assert not any(m.step_definition is None for m in graph.step_matches)
    assert graph.step_usage


def test_keyword_aware_step_matching(tmp_path: Path) -> None:
    """Steps with the same text but different keywords must match distinct definitions."""
    steps_dir = tmp_path / "features" / "steps"
    steps_dir.mkdir(parents=True)
    (steps_dir / "steps.py").write_text(
        "from behave import given, when, then\n"
        '@given("a thing")\n'
        "def step_given(): pass\n"
        '@when("a thing")\n'
        "def step_when(): pass\n"
        '@then("a thing")\n'
        "def step_then(): pass\n",
        encoding="utf-8",
    )
    (tmp_path / "features" / "feature.feature").write_text(
        "Feature: keyword matching\n\n"
        "  Scenario: S\n"
        "    Given a thing\n"
        "    When a thing\n"
        "    Then a thing\n",
        encoding="utf-8",
    )
    project = scan_features(tmp_path, DoctorConfig())
    steps = scan_steps(steps_dir, DoctorConfig())
    graph = build_graph(project, steps)
    assert len(graph.step_matches) == 3
    assert not any(m.step_definition is None for m in graph.step_matches)
    assert not any(m.ambiguous for m in graph.step_matches)

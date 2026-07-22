from __future__ import annotations

import re
from pathlib import Path

from behave_doctor.model.dependency_graph import DependencyGraph
from behave_doctor.model.step_definition import StepDefinition
from behave_doctor.model.step_match import StepMatch


def _make_def(function_name: str = "user_logged_in") -> StepDefinition:
    return StepDefinition(
        keyword="given",
        pattern="the user is logged in",
        pattern_compiled=re.compile("the user is logged in"),
        matcher_type="parse",
        file=Path("steps/auth.py"),
        line=10,
        function_name=function_name,
        module="auth",
        parameters=[],
    )


def test_dependency_graph_defaults_empty() -> None:
    graph = DependencyGraph()
    assert graph.feature_steps == {}
    assert graph.step_usage == {}
    assert graph.module_imports == {}
    assert graph.step_matches == []


def test_add_step_match_appends_match() -> None:
    graph = DependencyGraph()
    match = StepMatch(step=object(), step_definition=None)
    graph.add_step_match(match, feature_name="Login")
    assert graph.step_matches == [match]


def test_add_step_match_updates_maps_when_definition_present() -> None:
    graph = DependencyGraph()
    definition = _make_def()
    match = StepMatch(step=object(), step_definition=definition)
    graph.add_step_match(match, feature_name="Login")
    assert graph.feature_steps == {"Login": {"auth.user_logged_in"}}
    assert graph.step_usage == {"auth.user_logged_in": {"Login"}}


def test_add_step_match_without_feature_name_skips_maps() -> None:
    graph = DependencyGraph()
    definition = _make_def()
    match = StepMatch(step=object(), step_definition=definition)
    graph.add_step_match(match)
    assert graph.step_matches == [match]
    assert graph.feature_steps == {}
    assert graph.step_usage == {}

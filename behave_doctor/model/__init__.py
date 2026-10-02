"""Internal model package — re-exports all public model types."""

from __future__ import annotations

from typing import Any

from behave_model import Project, ScenarioOutline

from behave_doctor.model.config import DoctorConfig
from behave_doctor.model.dependency_graph import DependencyGraph
from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Category, Severity
from behave_doctor.model.location import location_line, location_path
from behave_doctor.model.project_report import ProjectReport, ProjectStatistics
from behave_doctor.model.step_definition import StepDefinition
from behave_doctor.model.step_match import StepMatch


def tag_name(tag: Any) -> str:
    """Return a normalized tag name string, ensuring it starts with ``@``.

    Accepts behave-model ``Tag`` objects, plain strings, and string subclasses.
    """
    name = getattr(tag, "name", tag)
    if not isinstance(name, str):
        name = str(name)
    if not name.startswith("@"):
        name = "@" + name
    return name


def all_project_tags(project: Project) -> list[Any]:
    """Return every tag in ``project``, including tags on Scenario Outline Examples blocks."""
    tags: list[Any] = list(getattr(project, "global_tags", []))
    for feature in project.features:
        tags.extend(feature.all_tags())
        for scenario in feature.all_scenarios():
            if isinstance(scenario, ScenarioOutline):
                for example in getattr(scenario, "examples", []):
                    tags.extend(example.tags)
    return tags


def scenario_tags(scenario: Any) -> list[Any]:
    """Return the effective tags for a scenario, including tags on its Examples blocks."""
    tags = list(scenario.tags)
    if isinstance(scenario, ScenarioOutline):
        for example in getattr(scenario, "examples", []):
            tags.extend(example.tags)
    return tags


def scenario_tag_sets(scenario: Any) -> list[list[Any]]:
    """Return one list of tags per generated scenario.

    For a ``ScenarioOutline`` this yields one entry for each example row, combining
    the outline's tags with the tags of the ``Examples`` block that produced the row.
    """
    base = list(scenario.tags)
    if isinstance(scenario, ScenarioOutline):
        sets: list[list[Any]] = []
        for example in getattr(scenario, "examples", []):
            combined = base + list(example.tags)
            for _ in example.table:
                sets.append(combined)
        return sets or [base]
    return [base]


def iter_feature_scenarios(feature: Any) -> Any:
    """Yield ``(scenario, rule)`` pairs for every scenario in ``feature``.

    ``rule`` is the behave-model ``Rule`` the scenario belongs to, or ``None``
    for scenarios directly under the feature. Scenarios inside ``Rule:``
    blocks (Gherkin v6, behave 1.3) inherit the rule's tags and backgrounds,
    so callers that need effective tags or steps must know the container.
    """
    for scenario in getattr(feature, "scenarios", []) or []:
        yield scenario, None
    for rule in getattr(feature, "rules", []) or []:
        for scenario in getattr(rule, "scenarios", []) or []:
            yield scenario, rule


def _scenario_count(scenario: Any) -> int:
    """Return the number of generated scenarios for a source scenario.

    A ``ScenarioOutline`` contributes one generated scenario per example row.
    Outlines without examples still count as a single source scenario.
    """
    if isinstance(scenario, ScenarioOutline):
        examples = getattr(scenario, "examples", [])
        count = sum(sum(1 for _ in ex.table) for ex in examples)
        return max(count, 1)
    return 1


def feature_scenario_count(feature: Any) -> int:
    """Return the number of generated scenarios in ``feature``.

    ``ScenarioOutline`` examples are expanded so each generated scenario is counted.
    """
    return sum(_scenario_count(scenario) for scenario in feature.all_scenarios())


def project_scenario_count(project: Project) -> int:
    """Return the total number of generated scenarios in ``project``."""
    return sum(feature_scenario_count(feature) for feature in project.features)


def feature_step_count(feature: Any) -> int:
    """Return the number of generated steps in ``feature``.

    Each generated scenario (including those from ``ScenarioOutline`` example
    rows) contributes its own steps plus the applicable background steps: the
    feature Background applies to every scenario, and a Rule's Background
    additionally applies to scenarios inside that rule — matching Behave's
    runtime execution model.
    """
    background_steps = len(feature.background.steps) if feature.background else 0
    total = 0
    for scenario, rule in iter_feature_scenarios(feature):
        rule_bg = len(rule.background.steps) if rule is not None and rule.background else 0
        count = _scenario_count(scenario)
        total += count * (len(scenario.steps) + background_steps + rule_bg)
    return total


def project_step_count(project: Project) -> int:
    """Return the total number of generated steps in ``project``."""
    return sum(feature_step_count(feature) for feature in project.features)


__all__ = [
    "Category",
    "DependencyGraph",
    "Diagnostic",
    "DoctorConfig",
    "ProjectReport",
    "ProjectStatistics",
    "Severity",
    "StepDefinition",
    "StepMatch",
    "all_project_tags",
    "feature_scenario_count",
    "feature_step_count",
    "iter_feature_scenarios",
    "location_line",
    "location_path",
    "project_scenario_count",
    "project_step_count",
    "scenario_tag_sets",
    "scenario_tags",
    "tag_name",
]

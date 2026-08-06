"""Quality rules (BD201-205) — suite quality issues."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from behave_doctor.model import (
    all_project_tags,
    feature_scenario_count,
    scenario_tags,
    tag_name,
)
from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Category, Severity
from behave_doctor.model.location import location_line, location_path
from behave_doctor.model.step_definition import StepDefinition
from behave_doctor.rules import register
from behave_doctor.rules.base import Rule, RuleContext, _get_int_override


@register
class DuplicateStepDefs(Rule):
    """BD201: find step definitions sharing the same pattern (case-insensitive).

    Definitions with the same pattern but different Gherkin keywords (e.g.
    ``@given("x")`` and ``@when("x")``) are not duplicates, because Behave keeps
    separate registries per keyword. ``@step`` is a universal registry, so it
    conflicts with any keyword-specific definition with the same pattern.
    """

    id = "BD201"
    name = "duplicate-step-defs"
    severity = Severity.ERROR
    category = Category.QUALITY
    description = "Same pattern registered multiple times."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        groups: dict[str, list[StepDefinition]] = defaultdict(list)
        for definition in context.step_definitions:
            groups[definition.pattern.lower()].append(definition)

        def _conflict(a: StepDefinition, b: StepDefinition) -> bool:
            if a.keyword == "step" or b.keyword == "step":
                return True
            return a.keyword == b.keyword

        diagnostics: list[Diagnostic] = []
        for pattern, defs in groups.items():
            if len(defs) < 2:
                continue
            has_conflict = any(
                _conflict(defs[i], defs[j])
                for i in range(len(defs))
                for j in range(i + 1, len(defs))
            )
            if not has_conflict:
                continue
            locations = ", ".join(f"{d.file}:{d.line}" for d in defs)
            diagnostics.append(
                Diagnostic(
                    rule_id=self.id,
                    rule_name=self.name,
                    severity=self.severity,
                    category=self.category,
                    message=(f"Duplicate step definition for pattern {pattern!r} in: {locations}"),
                    file=defs[0].file,
                    line=defs[0].line,
                    metadata={"pattern": pattern, "locations": locations},
                )
            )
        return diagnostics


@register
class ScenarioNoTags(Rule):
    """BD202: find scenarios with zero tags."""

    id = "BD202"
    name = "scenario-no-tags"
    severity = Severity.WARNING
    category = Category.QUALITY
    description = "Scenario has no tags."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for scenario in context.project.all_scenarios():
            if not scenario_tags(scenario):
                location = scenario.location
                diagnostics.append(
                    Diagnostic(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=self.severity,
                        category=self.category,
                        message=f'Scenario "{scenario.name}" has no tags',
                        file=location_path(location),
                        line=location_line(location),
                        metadata={"scenario": scenario.name},
                    )
                )
        return diagnostics


@register
class FeatureTooManyScenarios(Rule):
    """BD203: find features with more than ``max_scenarios`` scenarios."""

    id = "BD203"
    name = "feature-too-many-scenarios"
    severity = Severity.WARNING
    category = Category.QUALITY
    description = "Feature has more than N scenarios (default 20)."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        overrides = context.config.rules.get(self.id, {})
        max_scenarios = _get_int_override(overrides, "max_scenarios", 20)

        diagnostics: list[Diagnostic] = []
        for feature in context.project.features:
            count = feature_scenario_count(feature)
            if count > max_scenarios:
                location = feature.location
                diagnostics.append(
                    Diagnostic(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=self.severity,
                        category=self.category,
                        message=(
                            f'Feature "{feature.name}" has {count} scenarios (max {max_scenarios})'
                        ),
                        file=location_path(location),
                        line=location_line(location),
                        metadata={
                            "feature": feature.name,
                            "count": count,
                            "max_scenarios": max_scenarios,
                        },
                    )
                )
        return diagnostics


@register
class InconsistentTagCasing(Rule):
    """BD204: find tags that appear with inconsistent casing across the project."""

    id = "BD204"
    name = "inconsistent-tag-casing"
    severity = Severity.WARNING
    category = Category.QUALITY
    description = "Tags with inconsistent casing (e.g. @SmokeTest vs @smoke_test)."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        casings: dict[str, set[str]] = defaultdict(set)
        for tag in all_project_tags(context.project):
            name = tag_name(tag)
            normalized = _normalize_tag(name)
            casings[normalized].add(name)

        diagnostics: list[Diagnostic] = []
        for normalized, variants in casings.items():
            if len(variants) < 2:
                continue
            diagnostics.append(
                Diagnostic(
                    rule_id=self.id,
                    rule_name=self.name,
                    severity=self.severity,
                    category=self.category,
                    message=(f"Inconsistent tag casing for {normalized!r}: {sorted(variants)}"),
                    metadata={"variants": sorted(variants)},
                )
            )
        return diagnostics


@register
class AmbiguousStepMatch(Rule):
    """BD205: feature steps that match multiple step definitions.

    Behave raises ``AmbiguousStepError`` at runtime when a step text matches
    more than one definition. This rule detects the conflict statically so it
    can be fixed before running the suite.
    """

    id = "BD205"
    name = "ambiguous-step-match"
    severity = Severity.ERROR
    category = Category.QUALITY
    description = "Step matches multiple definitions (AmbiguousStepError at runtime)."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for match in context.dependency_graph.step_matches:
            if not match.ambiguous:
                continue
            step: Any = match.step
            location = step.location
            diagnostics.append(
                Diagnostic(
                    rule_id=self.id,
                    rule_name=self.name,
                    severity=self.severity,
                    category=self.category,
                    message=f'Ambiguous step match: "{step.full_text}"',
                    file=location_path(location),
                    line=location_line(location),
                    metadata={"step": step.name},
                )
            )
        return diagnostics


def _normalize_tag(name: str) -> str:
    """Normalize a tag name for casing comparison.

    Strips the leading ``@`` and any underscore/hyphen separators, then
    lowercases, so ``@SmokeTest`` and ``@smoke_test`` collapse to ``smoketest``.
    """
    cleaned = name.lstrip("@").replace("_", "").replace("-", "")
    return cleaned.lower()

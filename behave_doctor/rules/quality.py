"""Quality rules (BD201-204) — suite quality issues."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Category, Severity
from behave_doctor.rules import register
from behave_doctor.rules.base import Rule, RuleContext


@register
class DuplicateStepDefs(Rule):
    """BD201: find step definitions sharing the same pattern (case-insensitive)."""

    id = "BD201"
    name = "duplicate-step-defs"
    severity = Severity.ERROR
    category = Category.QUALITY
    description = "Same pattern registered multiple times."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        groups: dict[str, list[Any]] = defaultdict(list)
        for definition in context.step_definitions:
            groups[definition.pattern.lower()].append(definition)

        diagnostics: list[Diagnostic] = []
        for pattern, defs in groups.items():
            if len(defs) < 2:
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
            if not scenario.tags:
                location = scenario.location
                diagnostics.append(
                    Diagnostic(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=self.severity,
                        category=self.category,
                        message=f'Scenario "{scenario.name}" has no tags',
                        file=_location_path(location),
                        line=location.line or None,
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
        max_scenarios = int(overrides.get("max_scenarios", 20))

        diagnostics: list[Diagnostic] = []
        for feature in context.project.features:
            count = len(feature.all_scenarios())
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
                        file=_location_path(location),
                        line=location.line or None,
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
        for tag in context.project.all_tags():
            normalized = _normalize_tag(tag.name)
            casings[normalized].add(tag.name)

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


def _location_path(location: Any) -> Path | None:
    """Return a Path for a behave-model location, or ``None``."""
    filename = getattr(location, "filename", "") or ""
    return Path(filename) if filename else None


def _normalize_tag(name: str) -> str:
    """Normalize a tag name for casing comparison.

    Strips the leading ``@`` and any underscore/hyphen separators, then
    lowercases, so ``@SmokeTest`` and ``@smoke_test`` collapse to ``smoketest``.
    """
    cleaned = name.lstrip("@").replace("_", "").replace("-", "")
    return cleaned.lower()

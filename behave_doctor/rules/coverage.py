"""Coverage rules (BD301-304) — unused / undefined detection."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Category, Severity
from behave_doctor.rules import register
from behave_doctor.rules.base import Rule, RuleContext


@register
class UnusedStepDef(Rule):
    """BD301: step definitions never matched by any feature step."""

    id = "BD301"
    name = "unused-step-def"
    severity = Severity.WARNING
    category = Category.COVERAGE
    description = "Step definition never matched by any feature step."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        used_ids = set(context.dependency_graph.step_usage.keys())
        diagnostics: list[Diagnostic] = []
        for definition in context.step_definitions:
            if definition.def_id in used_ids:
                continue
            diagnostics.append(
                Diagnostic(
                    rule_id=self.id,
                    rule_name=self.name,
                    severity=self.severity,
                    category=self.category,
                    message=(f'Unused step definition: "{definition.pattern}"'),
                    file=definition.file,
                    line=definition.line,
                    metadata={"def_id": definition.def_id, "pattern": definition.pattern},
                )
            )
        return diagnostics


@register
class UndefinedStep(Rule):
    """BD302: feature steps with no matching step definition."""

    id = "BD302"
    name = "undefined-step"
    severity = Severity.ERROR
    category = Category.COVERAGE
    description = "Step in feature has no matching definition."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for match in context.dependency_graph.step_matches:
            if match.step_definition is not None:
                continue
            step: Any = match.step
            location = step.location
            diagnostics.append(
                Diagnostic(
                    rule_id=self.id,
                    rule_name=self.name,
                    severity=self.severity,
                    category=self.category,
                    message=f'Undefined step: "{step.full_text}"',
                    file=_location_path(location),
                    line=location.line or None,
                    metadata={"step": step.name},
                )
            )
        return diagnostics


@register
class UnusedTag(Rule):
    """BD303: tags that appear only once in the entire project."""

    id = "BD303"
    name = "unused-tag"
    severity = Severity.INFO
    category = Category.COVERAGE
    description = "Tag defined but never used in CI filters."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        excluded = {t.lstrip("@") for t in context.config.exclude_tags}
        excluded_normalized = {t.lower() for t in excluded}
        counts: Counter[str] = Counter()
        for tag in context.project.all_tags():
            counts[tag.name] += 1

        diagnostics: list[Diagnostic] = []
        for name, count in counts.items():
            if name.lstrip("@").lower() in excluded_normalized:
                continue
            if count <= 1:
                diagnostics.append(
                    Diagnostic(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=self.severity,
                        category=self.category,
                        message=f'Tag "{name}" is used only once',
                        metadata={"tag": name, "count": count},
                    )
                )
        return diagnostics


@register
class OrphanScenario(Rule):
    """BD304: scenarios whose tags are all unique to that scenario."""

    id = "BD304"
    name = "orphan-scenario"
    severity = Severity.WARNING
    category = Category.COVERAGE
    description = "Scenario never selected by any tag filter (all tags unique)."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        # Count how many scenarios use each tag.
        tag_to_scenarios: Counter[str] = Counter()
        for scenario in context.project.all_scenarios():
            for tag in scenario.tags:
                tag_to_scenarios[tag.name] += 1

        diagnostics: list[Diagnostic] = []
        for scenario in context.project.all_scenarios():
            if not scenario.tags:
                continue
            if all(tag_to_scenarios[tag.name] <= 1 for tag in scenario.tags):
                location = scenario.location
                diagnostics.append(
                    Diagnostic(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=self.severity,
                        category=self.category,
                        message=(
                            f'Scenario "{scenario.name}" has only unique tags '
                            f"{[t.name for t in scenario.tags]}"
                        ),
                        file=_location_path(location),
                        line=location.line or None,
                        metadata={"scenario": scenario.name},
                    )
                )
        return diagnostics


def _location_path(location: Any) -> Path | None:
    """Return a Path for a behave-model location, or ``None``."""
    filename = getattr(location, "filename", "") or ""
    return Path(filename) if filename else None

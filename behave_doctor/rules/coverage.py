"""Coverage rules (BD301-304) — unused / undefined detection."""

from __future__ import annotations

from collections import Counter
from typing import Any

from behave_doctor.model import all_project_tags, scenario_tag_sets, tag_name
from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Category, Severity
from behave_doctor.model.location import location_line, location_path
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
                    file=location_path(location),
                    line=location_line(location),
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
        for tag in all_project_tags(context.project):
            counts[tag_name(tag)] += 1

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
        # Build effective tag sets for each generated scenario. Feature-level tags are
        # inherited by every generated scenario in Behave tag filters. Scenario Outlines
        # are expanded into one entry per example row so tag usage is counted correctly.
        entries: list[tuple[Any, list[set[str]]]] = []
        for feature in context.project.features:
            featuretag_names = {tag_name(t) for t in feature.tags}
            for scenario in feature.all_scenarios():
                tag_sets = [
                    {tag_name(t) for t in tag_set} | featuretag_names
                    for tag_set in scenario_tag_sets(scenario)
                ]
                entries.append((scenario, tag_sets))

        # Count how many generated scenarios use each tag.
        tag_to_scenarios: Counter[str] = Counter()
        for _, tag_sets in entries:
            for names in tag_sets:
                for name in names:
                    tag_to_scenarios[name] += 1

        diagnostics: list[Diagnostic] = []
        for scenario, tag_sets in entries:
            all_names: set[str] = set()
            for names in tag_sets:
                all_names.update(names)
            if not all_names:
                continue
            if all(tag_to_scenarios[name] <= 1 for name in all_names):
                location = scenario.location
                diagnostics.append(
                    Diagnostic(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=self.severity,
                        category=self.category,
                        message=(
                            f'Scenario "{scenario.name}" has only unique tags {sorted(all_names)}'
                        ),
                        file=location_path(location),
                        line=location_line(location),
                        metadata={"scenario": scenario.name, "tags": sorted(all_names)},
                    )
                )
        return diagnostics

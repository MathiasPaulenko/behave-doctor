"""Structure rules (BD101-104) — informational metrics."""

from __future__ import annotations

from behave_doctor.model import (
    all_project_tags,
    project_scenario_count,
    project_step_count,
    tag_name,
)
from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Category, Severity
from behave_doctor.rules import register
from behave_doctor.rules.base import Rule, RuleContext


@register
class FeatureCount(Rule):
    """BD101: report the total number of features in the project."""

    id = "BD101"
    name = "feature-count"
    severity = Severity.INFO
    category = Category.STRUCTURE
    description = "Report total feature count."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        count = len(context.project.features)
        return [
            Diagnostic(
                rule_id=self.id,
                rule_name=self.name,
                severity=self.severity,
                category=self.category,
                message=f"{count} features found",
                metadata={"count": count},
            )
        ]


@register
class ScenarioCount(Rule):
    """BD102: report the total number of scenarios in the project."""

    id = "BD102"
    name = "scenario-count"
    severity = Severity.INFO
    category = Category.STRUCTURE
    description = "Report total scenario count."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        count = project_scenario_count(context.project)
        return [
            Diagnostic(
                rule_id=self.id,
                rule_name=self.name,
                severity=self.severity,
                category=self.category,
                message=f"{count} scenarios found",
                metadata={"count": count},
            )
        ]


@register
class StepCount(Rule):
    """BD103: report the total number of steps across all scenarios."""

    id = "BD103"
    name = "step-count"
    severity = Severity.INFO
    category = Category.STRUCTURE
    description = "Report total step count."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        count = project_step_count(context.project)
        return [
            Diagnostic(
                rule_id=self.id,
                rule_name=self.name,
                severity=self.severity,
                category=self.category,
                message=f"{count} steps found",
                metadata={"count": count},
            )
        ]


@register
class TagCoverage(Rule):
    """BD104: report tag usage distribution across the project."""

    id = "BD104"
    name = "tag-coverage"
    severity = Severity.INFO
    category = Category.STRUCTURE
    description = "Report tag usage distribution."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        tags = all_project_tags(context.project)
        unique = {tag_name(t) for t in tags}
        total = len(tags)
        return [
            Diagnostic(
                rule_id=self.id,
                rule_name=self.name,
                severity=self.severity,
                category=self.category,
                message=(f"{len(unique)} unique tags, {total} total tag usages"),
                metadata={"unique_tags": len(unique), "total_tag_usages": total},
            )
        ]

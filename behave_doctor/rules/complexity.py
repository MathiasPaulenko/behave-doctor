"""Complexity rules (BD401-403) — size and complexity limits."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Category, Severity
from behave_doctor.rules import register
from behave_doctor.rules.base import Rule, RuleContext


@register
class ScenarioTooManySteps(Rule):
    """BD401: scenarios with more than ``max_steps`` steps."""

    id = "BD401"
    name = "scenario-too-many-steps"
    severity = Severity.WARNING
    category = Category.COMPLEXITY
    description = "Scenario has more than N steps (default 10)."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        overrides = context.config.rules.get(self.id, {})
        max_steps = int(overrides.get("max_steps", 10))

        diagnostics: list[Diagnostic] = []
        for scenario in context.project.all_scenarios():
            count = len(scenario.steps)
            if count > max_steps:
                location = scenario.location
                diagnostics.append(
                    Diagnostic(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=self.severity,
                        category=self.category,
                        message=(f'Scenario "{scenario.name}" has {count} steps (max {max_steps})'),
                        file=_location_path(location),
                        line=location.line or None,
                        metadata={
                            "scenario": scenario.name,
                            "count": count,
                            "max_steps": max_steps,
                        },
                    )
                )
        return diagnostics


@register
class StepTooManyParams(Rule):
    """BD402: step definitions with more than ``max_params`` parameters."""

    id = "BD402"
    name = "step-too-many-params"
    severity = Severity.WARNING
    category = Category.COMPLEXITY
    description = "Step pattern has more than N parameters (default 5)."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        overrides = context.config.rules.get(self.id, {})
        max_params = int(overrides.get("max_params", 5))

        diagnostics: list[Diagnostic] = []
        for definition in context.step_definitions:
            count = len(definition.parameters)
            if count > max_params:
                diagnostics.append(
                    Diagnostic(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=self.severity,
                        category=self.category,
                        message=(
                            f'Step definition "{definition.pattern}" has '
                            f"{count} parameters (max {max_params})"
                        ),
                        file=definition.file,
                        line=definition.line,
                        metadata={
                            "def_id": definition.def_id,
                            "count": count,
                            "max_params": max_params,
                        },
                    )
                )
        return diagnostics


@register
class FeatureTooLarge(Rule):
    """BD403: feature files with more than ``max_lines`` lines."""

    id = "BD403"
    name = "feature-too-large"
    severity = Severity.WARNING
    category = Category.COMPLEXITY
    description = "Feature file has more than N lines (default 300)."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        overrides = context.config.rules.get(self.id, {})
        max_lines = int(overrides.get("max_lines", 300))

        diagnostics: list[Diagnostic] = []
        for feature in context.project.features:
            location = feature.location
            file = _location_path(location)
            if file is None or not file.exists():
                continue
            line_count = sum(1 for _ in file.read_text(encoding="utf-8").splitlines())
            if line_count > max_lines:
                diagnostics.append(
                    Diagnostic(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=self.severity,
                        category=self.category,
                        message=(
                            f'Feature file "{file.name}" has {line_count} lines (max {max_lines})'
                        ),
                        file=file,
                        line=location.line or None,
                        metadata={
                            "feature": feature.name,
                            "line_count": line_count,
                            "max_lines": max_lines,
                        },
                    )
                )
        return diagnostics


def _location_path(location: Any) -> Path | None:
    """Return a Path for a behave-model location, or ``None``."""
    filename = getattr(location, "filename", "") or ""
    return Path(filename) if filename else None

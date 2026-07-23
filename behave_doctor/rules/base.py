"""Rule engine — abstract Rule base class, RuleContext, and rule runner."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from behave_model import Project

from behave_doctor.model.config import DoctorConfig
from behave_doctor.model.dependency_graph import DependencyGraph
from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Category, Severity
from behave_doctor.model.step_definition import StepDefinition

__all__ = [
    "Category",
    "Diagnostic",
    "Rule",
    "RuleContext",
    "Severity",
    "run_rules",
]


class Rule(ABC):
    """Abstract base class for all diagnostic rules.

    Subclasses must define class attributes ``id``, ``name``, ``severity``,
    ``category`` and ``description``, and implement :meth:`check`.
    """

    id: str = ""
    name: str = ""
    severity: Severity = Severity.INFO
    category: Category = Category.STRUCTURE
    description: str = ""

    @abstractmethod
    def check(self, context: RuleContext) -> list[Diagnostic]:
        """Run the rule against the context and return diagnostics."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<Rule {self.id} {self.name}>"


@dataclass(frozen=True)
class RuleContext:
    """Context passed to each rule during a scan.

    Attributes:
        project: The behave-model ``Project``.
        step_definitions: All discovered step definitions.
        dependency_graph: The built dependency graph.
        config: The active ``DoctorConfig``.
    """

    project: Project
    step_definitions: list[StepDefinition]
    dependency_graph: DependencyGraph
    config: DoctorConfig


def _rule_enabled(rule: Rule, config: DoctorConfig) -> bool:
    """Return ``True`` if the rule is enabled in the config."""
    overrides = config.rules.get(rule.id)
    if overrides is None:
        return True
    if isinstance(overrides, bool):
        return overrides
    if not isinstance(overrides, dict):
        return True
    return bool(overrides.get("enabled", True))


def _get_int_override(
    overrides: dict[str, Any],
    key: str,
    default: int,
) -> int:
    """Safely extract an integer override from a rule config dict.

    Args:
        overrides: The rule's override dict from ``config.rules``.
        key: The override key (e.g. ``"max_steps"``).
        default: Fallback value if the key is missing or invalid.

    Returns:
        The integer value, or ``default`` if the value cannot be converted.
    """
    if not isinstance(overrides, dict):
        return default
    raw = overrides.get(key, default)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def run_rules(
    context: RuleContext,
    rules: list[Rule],
    *,
    rule_ids: list[str] | None = None,
    exclude_ids: list[str] | None = None,
) -> list[Diagnostic]:
    """Run a collection of rules against a context and concatenate diagnostics.

    Args:
        context: The rule context to check against.
        rules: The rule instances to run.
        rule_ids: Optional allowlist of rule IDs to run. If provided, only
            rules whose ID is in this list are run.
        exclude_ids: Optional blocklist of rule IDs to skip.

    Returns:
        All diagnostics produced by the enabled, non-excluded rules.
    """
    exclude = set(exclude_ids or [])
    allow = set(rule_ids) if rule_ids is not None else None
    diagnostics: list[Diagnostic] = []
    for rule in rules:
        if rule.id in exclude:
            continue
        if allow is not None and rule.id not in allow:
            continue
        if not _rule_enabled(rule, context.config):
            continue
        diagnostics.extend(rule.check(context))
    return diagnostics

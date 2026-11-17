"""Rule engine — abstract Rule base class, RuleContext, and rule runner."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
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
        scan_errors: ``(file, message)`` pairs for feature files that could
            not be parsed or adapted during the scan.
        step_scan_errors: ``(file, message)`` pairs for Python step files
            that could not be parsed during the scan.
    """

    project: Project
    step_definitions: list[StepDefinition]
    dependency_graph: DependencyGraph
    config: DoctorConfig
    scan_errors: list[tuple[Path, str]] = field(default_factory=list)
    step_scan_errors: list[tuple[Path, str]] = field(default_factory=list)


def _rule_overrides(rule_id: str, config: DoctorConfig) -> Any:
    """Return the config overrides for ``rule_id``, matching case-insensitively.

    ``from_pyproject`` normalises keys to upper-case, but a ``DoctorConfig``
    built by hand may use lower-case keys (``rules={"bd401": {...}}``).
    """
    overrides = config.rules.get(rule_id)
    if overrides is None:
        overrides = next(
            (v for k, v in config.rules.items() if k.upper() == rule_id.upper()),
            None,
        )
    return overrides


def _rule_enabled(rule: Rule, config: DoctorConfig) -> bool:
    """Return ``True`` if the rule is enabled in the config."""
    overrides = _rule_overrides(rule.id, config)
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
    # Rule IDs match case-insensitively (``bd301`` selects ``BD301``).
    exclude = {rule_id.upper() for rule_id in exclude_ids or []}
    # An empty allowlist is treated like no allowlist — otherwise it would
    # silently disable every rule and report a vacuously clean project.
    allow = {rule_id.upper() for rule_id in rule_ids} if rule_ids else None
    diagnostics: list[Diagnostic] = []
    for rule in rules:
        if rule.id.upper() in exclude:
            continue
        if allow is not None and rule.id.upper() not in allow:
            continue
        if not _rule_enabled(rule, context.config):
            continue
        diagnostics.extend(rule.check(context))
    return diagnostics

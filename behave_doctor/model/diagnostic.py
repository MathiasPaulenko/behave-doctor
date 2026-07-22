"""The Diagnostic dataclass — a single finding produced by a rule."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from behave_doctor.model.enums import Category, Severity


@dataclass(frozen=True)
class Diagnostic:
    """A single finding produced by a diagnostic rule.

    Attributes:
        rule_id: Stable rule identifier (e.g. ``"BD301"``).
        rule_name: Human-readable rule name (e.g. ``"unused-step-def"``).
        severity: Severity of the finding.
        category: Category the rule belongs to.
        message: Human-readable description of the finding.
        file: File where the issue was found, if applicable.
        line: 1-indexed line number, if applicable.
        suggestion: Optional fix suggestion.
        metadata: Extra context for reporters.
    """

    rule_id: str
    rule_name: str
    severity: Severity
    category: Category
    message: str
    file: Path | None = None
    line: int | None = None
    suggestion: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

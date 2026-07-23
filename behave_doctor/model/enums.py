"""Enumerations shared across the behave-doctor model and rules."""

from __future__ import annotations

from enum import Enum


class Severity(Enum):
    """Diagnostic severity levels, ordered from most to least severe."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


class Category(Enum):
    """Diagnostic category, grouping rules by concern."""

    STRUCTURE = "structure"
    QUALITY = "quality"
    COVERAGE = "coverage"
    COMPLEXITY = "complexity"
    DEPENDENCY = "dependency"


SEVERITY_ORDER: dict[Severity, int] = {
    Severity.ERROR: 0,
    Severity.WARNING: 1,
    Severity.INFO: 2,
    Severity.HINT: 3,
}
"""Numeric ordering of severities, lowest = most severe. Used for filtering
and sorting diagnostics across reporters and the core engine."""

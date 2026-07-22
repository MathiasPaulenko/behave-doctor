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

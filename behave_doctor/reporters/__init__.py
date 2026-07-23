"""Reporters package — text, JSON, and SARIF output."""

from __future__ import annotations

from typing import Protocol

from behave_doctor.model.project_report import ProjectReport
from behave_doctor.reporters.text import TextReporter


class Reporter(Protocol):
    """Protocol implemented by all reporters."""

    def format(self, report: ProjectReport) -> str:
        """Format a ``ProjectReport`` as a string."""
        ...


__all__ = ["Reporter", "TextReporter"]

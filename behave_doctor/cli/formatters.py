"""Output format dispatch for the CLI."""

from __future__ import annotations

from behave_doctor.model.project_report import ProjectReport
from behave_doctor.reporters.json_reporter import JsonReporter
from behave_doctor.reporters.sarif import SarifReporter
from behave_doctor.reporters.text import TextReporter


def format_report(
    report: ProjectReport,
    fmt: str = "text",
    *,
    use_color: bool = True,
    quiet: bool = False,
    verbose: bool = False,
) -> str:
    """Format a report with the selected reporter.

    Args:
        report: The project report to format.
        fmt: One of ``"text"``, ``"json"``, ``"sarif"``.
        use_color: Whether to use ANSI colors (text only).
        quiet: Only show errors (text only).
        verbose: Show extra context (text only).

    Returns:
        The formatted report as a string.

    Raises:
        ValueError: If ``fmt`` is not a supported format.
    """
    if fmt == "text":
        return TextReporter(use_color=use_color, quiet=quiet, verbose=verbose).format(report)
    if fmt == "json":
        return JsonReporter().format(report)
    if fmt == "sarif":
        return SarifReporter().format(report)
    raise ValueError(f"Unknown format: {fmt!r}. Use text, json, or sarif.")

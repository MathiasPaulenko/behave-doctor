"""Text reporter — human-readable colored console output."""

from __future__ import annotations

from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import SEVERITY_ORDER, Severity
from behave_doctor.model.project_report import ProjectReport

# ANSI color codes.
_RED = "\033[31m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_RESET = "\033[0m"

_SEVERITY_COLOR: dict[Severity, str] = {
    Severity.ERROR: _RED,
    Severity.WARNING: _YELLOW,
    Severity.INFO: _CYAN,
    Severity.HINT: _CYAN,
}

_SEVERITY_LABEL: dict[Severity, str] = {
    Severity.ERROR: "ERROR",
    Severity.WARNING: "WARNING",
    Severity.INFO: "INFO",
    Severity.HINT: "HINT",
}


class TextReporter:
    """Human-readable console reporter.

    Args:
        use_color: Whether to emit ANSI color codes.
        quiet: Only show errors.
        verbose: Show suggestions and metadata for each diagnostic.
    """

    def __init__(self, use_color: bool = True, quiet: bool = False, verbose: bool = False) -> None:
        self.use_color = use_color
        self.quiet = quiet
        self.verbose = verbose

    def format(self, report: ProjectReport) -> str:
        """Format a ``ProjectReport`` as a human-readable string."""
        lines: list[str] = []

        lines.append(f"Scanning {report.project_path}...")
        stats = report.statistics
        lines.append(
            f"Found {stats.features} features, {stats.scenarios} scenarios, "
            f"{stats.steps} steps, {stats.step_definitions} step definitions."
        )

        diagnostics = self._filter(report.diagnostics)
        diagnostics = sorted(diagnostics, key=lambda d: (SEVERITY_ORDER[d.severity], d.rule_id))

        if diagnostics:
            lines.append("")
        for diag in diagnostics:
            lines.append(self._format_diagnostic(diag))

        lines.append("")
        seconds = report.scan_duration_ms / 1000.0
        error_count = sum(1 for d in diagnostics if d.severity is Severity.ERROR)
        warning_count = sum(1 for d in diagnostics if d.severity is Severity.WARNING)
        lines.append(f"{error_count} errors, {warning_count} warnings in {seconds}s")
        return "\n".join(lines)

    def _filter(self, diagnostics: list[Diagnostic]) -> list[Diagnostic]:
        if self.quiet:
            return [d for d in diagnostics if d.severity is Severity.ERROR]
        return list(diagnostics)

    def _format_diagnostic(self, diag: Diagnostic) -> str:
        label = _SEVERITY_LABEL[diag.severity]
        location = self._format_location(diag)
        line = f"{diag.rule_id}  {label}   {diag.message}  ({location})"

        if self.verbose:
            extras: list[str] = []
            if diag.suggestion:
                extras.append(f"Suggestion: {diag.suggestion}")
            if diag.metadata:
                extras.append(f"Metadata: {diag.metadata}")
            if extras:
                line = "\n".join([line, *extras])

        if self.use_color:
            color = _SEVERITY_COLOR[diag.severity]
            line = f"{color}{line}{_RESET}"
        return line

    @staticmethod
    def _format_location(diag: Diagnostic) -> str:
        if diag.file is None and diag.line is None:
            return "<unknown>"
        file_part = str(diag.file) if diag.file is not None else "<unknown>"
        if diag.line is None:
            return file_part
        return f"{file_part}:{diag.line}"

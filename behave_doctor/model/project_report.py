"""ProjectReport and ProjectStatistics dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Severity


@dataclass(frozen=True)
class ProjectStatistics:
    """Aggregate metrics for a scanned project.

    Attributes:
        features: Total number of features.
        scenarios: Total number of scenarios.
        steps: Total number of steps.
        step_definitions: Total number of step definitions.
        tags: Number of unique tags.
        total_tag_usages: Total tag usages across the project.
        average_steps_per_scenario: Mean steps per scenario.
        unused_step_definitions: Count of unused step definitions.
        undefined_steps: Count of undefined feature steps.
    """

    features: int = 0
    scenarios: int = 0
    steps: int = 0
    step_definitions: int = 0
    tags: int = 0
    total_tag_usages: int = 0
    average_steps_per_scenario: float = 0.0
    unused_step_definitions: int = 0
    undefined_steps: int = 0


@dataclass
class ProjectReport:
    """The full diagnostic report for a scanned project.

    Attributes:
        project_path: Root path of the scanned project.
        diagnostics: All diagnostics produced by the rule engine.
        statistics: Aggregate project statistics.
        scanned_at: Timestamp of the scan.
        scan_duration_ms: Scan duration in milliseconds.
    """

    project_path: Path
    diagnostics: list[Diagnostic] = field(default_factory=list)
    statistics: ProjectStatistics = field(default_factory=ProjectStatistics)
    scanned_at: datetime = field(default_factory=datetime.now)
    scan_duration_ms: int = 0

    @property
    def errors(self) -> list[Diagnostic]:
        """Diagnostics with severity ``ERROR``."""
        return [d for d in self.diagnostics if d.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Diagnostic]:
        """Diagnostics with severity ``WARNING``."""
        return [d for d in self.diagnostics if d.severity is Severity.WARNING]

    @property
    def has_errors(self) -> bool:
        """``True`` if the report contains at least one error."""
        return bool(self.errors)

    @property
    def has_warnings(self) -> bool:
        """``True`` if the report contains at least one warning."""
        return any(d.severity is Severity.WARNING for d in self.diagnostics)

    @property
    def exit_code(self) -> int:
        """Exit code: ``0`` if clean, ``1`` if any errors or warnings were found."""
        return 1 if (self.has_errors or self.has_warnings) else 0

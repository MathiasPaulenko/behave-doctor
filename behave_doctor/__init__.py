"""behave-doctor: static analysis and diagnostics for Behave BDD suites.

Public API:

    from behave_doctor import scan_project, ProjectReport, Diagnostic

    report = scan_project("path/to/project")
    for d in report.diagnostics:
        print(f"{d.rule_id}: {d.message} at {d.file}:{d.line}")
"""

from __future__ import annotations

from pathlib import Path

from behave_doctor.core import build_report
from behave_doctor.model.config import DoctorConfig
from behave_doctor.model.dependency_graph import DependencyGraph
from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Category, Severity
from behave_doctor.model.project_report import ProjectReport, ProjectStatistics
from behave_doctor.model.step_definition import StepDefinition
from behave_doctor.model.step_match import StepMatch
from behave_doctor.rules.base import Rule

__version__ = "1.2.0"


def scan_project(
    path: str | Path,
    config: DoctorConfig | None = None,
) -> ProjectReport:
    """Scan a Behave project and return a diagnostic report.

    This is the high-level orchestrator: it loads configuration, scans
    features and step definitions, builds the dependency graph, runs all
    enabled rules, and returns a :class:`ProjectReport`.

    Args:
        path: Root directory of the Behave project.
        config: Optional configuration. When ``None``, configuration is
            loaded from ``pyproject.toml`` in ``path`` if present, otherwise
            defaults are used.

    Returns:
        A :class:`ProjectReport` with diagnostics, statistics, and exit code.

    Raises:
        TypeError: If ``path`` is ``None``.
        FileNotFoundError: If ``path`` does not exist.
        ScanError: If ``path`` exists but is not a directory or cannot be scanned.
    """
    if path is None:
        msg = "scan_project() requires a path argument, got None."
        raise TypeError(msg)
    project_path = Path(path).resolve()
    if not project_path.exists():
        raise FileNotFoundError(f"Project path does not exist: {project_path}")
    if config is None:
        pyproject = project_path / "pyproject.toml"
        config = DoctorConfig.from_pyproject(pyproject) if pyproject.exists() else DoctorConfig()
    return build_report(project_path, config)


__all__ = [
    "Category",
    "DependencyGraph",
    "Diagnostic",
    "DoctorConfig",
    "ProjectReport",
    "ProjectStatistics",
    "Rule",
    "Severity",
    "StepDefinition",
    "StepMatch",
    "__version__",
    "scan_project",
]

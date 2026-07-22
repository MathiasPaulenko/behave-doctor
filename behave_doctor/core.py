"""Core orchestration — runs all scan phases and builds a ProjectReport."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from behave_model import Project

from behave_doctor.graph.builder import build_graph
from behave_doctor.model.config import DoctorConfig
from behave_doctor.model.dependency_graph import DependencyGraph
from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Severity
from behave_doctor.model.project_report import ProjectReport, ProjectStatistics
from behave_doctor.model.step_definition import StepDefinition
from behave_doctor.rules import get_all_rules
from behave_doctor.rules.base import RuleContext, run_rules
from behave_doctor.scanner.project_scanner import scan_features
from behave_doctor.scanner.step_scanner import scan_steps


def build_statistics(
    project: Project,
    step_definitions: list[StepDefinition],
    graph: DependencyGraph,
) -> ProjectStatistics:
    """Build ``ProjectStatistics`` from a project, step defs and dependency graph."""
    stats = project.statistics()
    used_ids = set(graph.step_usage.keys())
    unused = sum(1 for d in step_definitions if d.def_id not in used_ids)
    undefined = sum(1 for m in graph.step_matches if m.step_definition is None)
    return ProjectStatistics(
        features=stats.get("features", 0),
        scenarios=stats.get("scenarios", 0),
        steps=stats.get("steps", 0),
        step_definitions=len(step_definitions),
        tags=stats.get("tags", 0),
        total_tag_usages=stats.get("total_tag_usages", 0),
        average_steps_per_scenario=float(stats.get("average_steps_per_scenario", 0.0)),
        unused_step_definitions=unused,
        undefined_steps=undefined,
    )


def build_report(
    project_path: Path,
    config: DoctorConfig,
    *,
    rule_ids: list[str] | None = None,
    exclude_ids: list[str] | None = None,
    min_severity: Severity | None = None,
) -> ProjectReport:
    """Run the full scan pipeline and return a ``ProjectReport``.

    Args:
        project_path: Root directory of the Behave project.
        config: Configuration for the scan.
        rule_ids: Optional allowlist of rule IDs to run.
        exclude_ids: Optional blocklist of rule IDs to skip.
        min_severity: Optional minimum severity; diagnostics below this are
            filtered out. Defaults to ``config.min_severity``.

    Returns:
        A ``ProjectReport``. Raises ``ScanError`` if the project cannot be scanned.
    """
    start = time.perf_counter()
    project = scan_features(project_path, config)
    step_definitions = scan_steps((project_path / config.steps_dir).resolve(), config)
    graph = build_graph(project, step_definitions)

    context = RuleContext(
        project=project,
        step_definitions=step_definitions,
        dependency_graph=graph,
        config=config,
    )
    rules = get_all_rules()
    diagnostics = run_rules(context, rules, rule_ids=rule_ids, exclude_ids=exclude_ids)

    severity = min_severity if min_severity is not None else config.min_severity
    diagnostics = _filter_by_severity(diagnostics, severity)

    statistics = build_statistics(project, step_definitions, graph)
    duration_ms = int((time.perf_counter() - start) * 1000)

    return ProjectReport(
        project_path=project_path,
        diagnostics=diagnostics,
        statistics=statistics,
        scanned_at=datetime.now(),
        scan_duration_ms=duration_ms,
    )


def _filter_by_severity(
    diagnostics: list[Diagnostic],
    min_severity: Severity,
) -> list[Diagnostic]:
    """Return only diagnostics with severity at or above ``min_severity``."""
    order = {
        Severity.ERROR: 0,
        Severity.WARNING: 1,
        Severity.INFO: 2,
        Severity.HINT: 3,
    }
    threshold = order[min_severity]
    return [d for d in diagnostics if order[d.severity] <= threshold]

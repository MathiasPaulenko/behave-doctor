"""Impact analysis — determine which scenarios are affected by changed files.

Given a set of changed files (``.py`` step definitions or ``.feature`` files),
this module identifies which scenarios in the project are impacted by those
changes.  It reuses the existing AST scanner, matcher, and dependency graph
components — no new scanning logic is introduced.

Public API::

    from behave_doctor import impact_analysis, ImpactResult

    result = impact_analysis(".", changed_files=["src/auth.py"])
    for scenario in result.affected_scenarios:
        print(f"{scenario.feature_path}:{scenario.line} -> {scenario.name}")
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from behave_model import Project

from behave_doctor.graph.builder import _attach_step_types, _match_step
from behave_doctor.model.config import DoctorConfig
from behave_doctor.model.location import location_line, location_path
from behave_doctor.model.step_definition import StepDefinition
from behave_doctor.scanner.project_scanner import scan_features
from behave_doctor.scanner.step_scanner import scan_steps

logger = logging.getLogger(__name__)

__all__ = [
    "AffectedScenario",
    "ChangedFile",
    "ImpactResult",
    "ImpactSummary",
    "impact_analysis",
    "format_impact",
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AffectedScenario:
    """A scenario impacted by at least one changed file.

    Attributes:
        feature_path: Relative or absolute path of the feature file.
        line: 1-indexed line number of the scenario in the feature file.
        name: Scenario name (suitable for ``behave --name``).
        matched_steps: Step definition patterns that matched steps in this
            scenario.  Empty when the scenario is affected because its
            containing ``.feature`` file changed directly.
    """

    feature_path: str
    line: int
    name: str
    matched_steps: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ChangedFile:
    """A file passed to impact analysis.

    Attributes:
        path: Resolved path of the changed file.
        step_definitions: Number of step definitions found in this file.
            Zero for ``.feature`` files or ``.py`` files without step defs.
    """

    path: str
    step_definitions: int


@dataclass(frozen=True)
class ImpactSummary:
    """Aggregate counts for an impact analysis result."""

    changed_files: int
    step_definitions_affected: int
    scenarios_affected: int
    features_affected: int


@dataclass(frozen=True)
class ImpactResult:
    """The complete result of an impact analysis.

    Attributes:
        changed_files: One entry per changed file (including files with 0
            step definitions).
        affected_scenarios: Deduplicated, sorted by (feature_path, line).
        affected_features: Sorted unique feature file paths.
        summary: Aggregate counts.
    """

    changed_files: list[ChangedFile]
    affected_scenarios: list[AffectedScenario]
    affected_features: list[str]
    summary: ImpactSummary

    @property
    def scenario_names(self) -> list[str]:
        """Scenario names suitable for ``behave --name``."""
        return [s.name for s in self.affected_scenarios]


# ---------------------------------------------------------------------------
# Core algorithm
# ---------------------------------------------------------------------------


def _feature_file_path(feature: Any) -> str:
    """Return the file path string of a behave-model feature."""
    loc = getattr(feature, "location", None)
    path = location_path(loc) if loc else None
    return str(path) if path else ""


def _scenario_line(scenario: Any) -> int:
    """Return the 1-indexed line number of a scenario, or 0 if unknown."""
    loc = getattr(scenario, "location", None)
    line = location_line(loc) if loc else None
    return line if line is not None else 0


def _resolve_changed_files(
    changed_files: Sequence[str | Path],
    project_path: Path,
) -> tuple[list[Path], list[Path]]:
    """Resolve changed file paths and separate into ``.py`` and ``.feature``.

    Returns ``(py_files, feature_files)``, both lists of resolved absolute
    ``Path`` objects.  Files that do not exist raise ``FileNotFoundError``.
    Files outside ``project_path`` emit a warning and are skipped.
    Relative paths are resolved against ``project_path``, not the current
    working directory.
    """
    py_files: list[Path] = []
    feature_files: list[Path] = []
    seen: set[Path] = set()
    for raw in changed_files:
        p = Path(raw)
        if not p.is_absolute():
            p = project_path / p
        p = p.resolve()
        if p in seen:
            continue
        seen.add(p)
        if not p.exists():
            raise FileNotFoundError(f"Changed file does not exist: {p}")
        # Warn if the file is outside the project, but still process it —
        # the step definitions might still match if paths coincide.
        try:
            p.relative_to(project_path)
        except ValueError:
            logger.warning("%s is outside the project root, skipping.", p)
            continue
        if p.suffix == ".py":
            py_files.append(p)
        elif p.suffix == ".feature":
            feature_files.append(p)
        else:
            # Non .py / .feature files are ignored with a warning.
            logger.warning("%s is not a .py or .feature file, skipping.", p)
    return py_files, feature_files


def _find_affected_definitions(
    step_definitions: list[StepDefinition],
    changed_py: list[Path],
) -> set[str]:
    """Return the set of ``def_id``s whose source file is in ``changed_py``."""
    changed_set = set(changed_py)
    return {d.def_id for d in step_definitions if d.file in changed_set}


def _build_scenario_index(
    project: Project,
    step_definitions: list[StepDefinition],
) -> list[tuple[str, int, str, list[str]]]:
    """Build an index of (feature_path, line, scenario_name, matched_patterns).

    For each scenario in the project, matches every step against the
    definitions and records which patterns matched.  Scenario Outlines are
    matched using their template steps (not expanded rows) since the scenario
    name is what matters for ``behave --name``.
    """
    index: list[tuple[str, int, str, list[str]]] = []
    for feature in project.features:
        fpath = _feature_file_path(feature)

        # Match background steps once per feature — they are the same for
        # every scenario and don't need to be re-matched per scenario.
        bg_matched_patterns: list[str] = []
        if feature.background:
            bg_steps = _attach_step_types(list(feature.background.steps))
            for step in bg_steps:
                match = _match_step(step, step_definitions)
                if match.step_definition is not None:
                    bg_matched_patterns.append(match.step_definition.pattern)

        for scenario in feature.all_scenarios():
            name = getattr(scenario, "name", "") or ""
            line = _scenario_line(scenario)
            matched_patterns: list[str] = list(bg_matched_patterns)

            # Collect steps for this scenario (not expanded — we want the
            # template steps for Scenario Outlines).
            raw_steps = list(getattr(scenario, "steps", []))
            steps = _attach_step_types(raw_steps)
            for step in steps:
                match = _match_step(step, step_definitions)
                if match.step_definition is not None:
                    matched_patterns.append(match.step_definition.pattern)

            index.append((fpath, line, name, matched_patterns))
    return index


def impact_analysis(
    project_path: str | Path,
    changed_files: Sequence[str | Path],
    config: DoctorConfig | None = None,
) -> ImpactResult:
    """Analyse which scenarios are affected by a set of changed files.

    Args:
        project_path: Root directory of the Behave project.
        changed_files: List of paths to changed ``.py`` or ``.feature`` files.
        config: Optional configuration.  When ``None``, configuration is
            loaded from ``pyproject.toml`` in ``project_path`` if present.

    Returns:
        An :class:`ImpactResult` with affected scenarios, features, and
        summary counts.

    Raises:
        FileNotFoundError: If ``project_path`` or any changed file does not
            exist.
        ScanError: If the project cannot be scanned.
    """
    root = Path(project_path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Project path does not exist: {root}")

    if config is None:
        pyproject = root / "pyproject.toml"
        config = DoctorConfig.from_pyproject(pyproject) if pyproject.exists() else DoctorConfig()

    # Handle empty input — return an empty result.
    if not changed_files:
        return ImpactResult(
            changed_files=[],
            affected_scenarios=[],
            affected_features=[],
            summary=ImpactSummary(0, 0, 0, 0),
        )

    # Scan the project (reuse existing components).
    project = scan_features(root, config)
    steps_path = (root / config.steps_dir).resolve()
    step_definitions = scan_steps(steps_path, config)

    # Resolve and classify changed files.
    changed_py, changed_feature = _resolve_changed_files(changed_files, root)

    # Build ChangedFile entries for all valid changed files.
    changed_file_entries: list[ChangedFile] = []
    all_changed = changed_py + changed_feature
    for f in all_changed:
        count = sum(1 for d in step_definitions if d.file == f)
        changed_file_entries.append(ChangedFile(path=str(f), step_definitions=count))

    # Find affected step definition IDs from changed .py files.
    affected_def_ids = _find_affected_definitions(step_definitions, changed_py)

    # Build the scenario index.
    scenario_index = _build_scenario_index(project, step_definitions)

    # Determine affected scenarios.
    # Key: (feature_path, line, name) -> set of matched patterns
    affected: dict[tuple[str, int, str], set[str]] = {}

    # 1. Scenarios affected by changed .py files (via step definitions).
    affected_patterns: set[str] = set()
    if affected_def_ids:
        affected_patterns = {d.pattern for d in step_definitions if d.def_id in affected_def_ids}

    # 2. Scenarios affected by changed .feature files (all scenarios in them).
    changed_feature_set = {f.resolve() for f in changed_feature}

    # Single pass over the scenario index.
    for fpath, line, name, matched_patterns in scenario_index:
        key = (fpath, line, name)
        # Check .py impact via step definition patterns.
        if affected_patterns:
            hits = set(matched_patterns) & affected_patterns
            if hits:
                affected.setdefault(key, set()).update(hits)
        # Check .feature impact — all scenarios in a changed feature file.
        if Path(fpath).resolve() in changed_feature_set:
            affected.setdefault(key, set()).update(matched_patterns)

    # Build sorted, deduplicated AffectedScenario list.
    sorted_keys = sorted(affected.keys(), key=lambda k: (k[0], k[1]))
    affected_scenarios = [
        AffectedScenario(
            feature_path=k[0],
            line=k[1],
            name=k[2],
            matched_steps=sorted(affected[k]),
        )
        for k in sorted_keys
    ]

    # Affected features (sorted, unique).
    affected_features = sorted({s.feature_path for s in affected_scenarios})

    # Summary.
    step_defs_affected = len(affected_def_ids)
    summary = ImpactSummary(
        changed_files=len(changed_file_entries),
        step_definitions_affected=step_defs_affected,
        scenarios_affected=len(affected_scenarios),
        features_affected=len(affected_features),
    )

    return ImpactResult(
        changed_files=changed_file_entries,
        affected_scenarios=affected_scenarios,
        affected_features=affected_features,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def format_impact(result: ImpactResult, fmt: str = "text") -> str:
    """Format an :class:`ImpactResult` as a string.

    Args:
        result: The impact analysis result.
        fmt: One of ``"text"``, ``"json"``, or ``"names"``.

    Returns:
        The formatted output as a string.

    Raises:
        ValueError: If ``fmt`` is not a supported format.
    """
    if not fmt or not fmt.strip():
        raise ValueError("Format must be a non-empty string. Use text, json, or names.")
    fmt = fmt.strip().lower()
    if fmt == "text":
        return _format_text(result)
    if fmt == "json":
        return _format_json(result)
    if fmt == "names":
        return _format_names(result)
    raise ValueError(f"Unknown format: {fmt!r}. Use text, json, or names.")


def _format_text(result: ImpactResult) -> str:
    """Human-readable text output."""
    lines: list[str] = []
    lines.append(f"Impact analysis: {result.summary.changed_files} changed files")
    lines.append("")

    if result.changed_files:
        lines.append("Changed files:")
        for cf in result.changed_files:
            lines.append(f"  - {cf.path} ({cf.step_definitions} step definitions)")
        lines.append("")

    lines.append(f"Affected scenarios ({result.summary.scenarios_affected}):")
    if result.affected_scenarios:
        for s in result.affected_scenarios:
            lines.append(f"  {s.feature_path}:{s.line}  {s.name}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append(f"Affected features ({result.summary.features_affected}):")
    if result.affected_features:
        for fpath in result.affected_features:
            lines.append(f"  {fpath}")
    else:
        lines.append("  (none)")

    return "\n".join(lines)


def _format_json(result: ImpactResult) -> str:
    """Structured JSON output for CI integration."""
    payload: dict[str, Any] = {
        "changed_files": [
            {"path": cf.path, "step_definitions": cf.step_definitions}
            for cf in result.changed_files
        ],
        "affected_scenarios": [
            {
                "feature": s.feature_path,
                "line": s.line,
                "name": s.name,
                "matched_steps": s.matched_steps,
            }
            for s in result.affected_scenarios
        ],
        "affected_features": result.affected_features,
        "summary": {
            "changed_files": result.summary.changed_files,
            "step_definitions_affected": result.summary.step_definitions_affected,
            "scenarios_affected": result.summary.scenarios_affected,
            "features_affected": result.summary.features_affected,
        },
    }
    return json.dumps(payload, sort_keys=True, indent=2)


def _format_names(result: ImpactResult) -> str:
    """One scenario name per line, for ``behave --name``."""
    return "\n".join(result.scenario_names)

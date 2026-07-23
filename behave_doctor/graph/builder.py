"""Graph builder — match feature steps to definitions and build DependencyGraph."""

from __future__ import annotations

import ast
import dataclasses
import re
from pathlib import Path
from typing import Any

from behave_model import Project, ScenarioOutline, Step

from behave_doctor.model.dependency_graph import DependencyGraph
from behave_doctor.model.step_definition import StepDefinition
from behave_doctor.model.step_match import StepMatch

# Keywords that may prefix a step line and must be stripped before matching.
_STEP_KEYWORDS = {"given", "when", "then", "and", "but", "*"}

# Placeholders used in Scenario Outline steps, e.g. ``<name>``.
_OUTLINE_PLACEHOLDER_RE = re.compile(r"<([A-Za-z_][A-Za-z0-9_]*)>")


def _replace_placeholders(text: str, values: dict[str, str]) -> str:
    """Replace every ``<key>`` placeholder in ``text`` with its value from ``values``."""

    def _repl(match: re.Match[str]) -> str:
        return values.get(match.group(1), match.group(0))

    return _OUTLINE_PLACEHOLDER_RE.sub(_repl, text)


def _expand_step(step: Step, values: dict[str, str]) -> Step:
    """Return a copy of ``step`` with placeholders in its name replaced by concrete values."""
    if "<" not in step.name:
        return step
    return dataclasses.replace(step, name=_replace_placeholders(step.name, values))


def _resolve_step_type(keyword: str, previous: str | None) -> str | None:
    """Return the canonical step type for a Gherkin keyword.

    ``And``/``But``/``*`` inherit the type of the previous step in the
    scenario, just as Behave does at runtime. When there is no previous step,
    ``*`` falls back to the universal ``step`` registry. Unknown keywords
    fall back to the previous type so localised Gherkin keywords behave.
    """
    key = keyword.lower()
    if key in {"given", "when", "then"}:
        return key
    if key in {"and", "but", "*"}:
        return previous or "step"
    return previous


def _attach_step_types(steps: list[Step]) -> list[Step]:
    """Set ``step_type`` on each step, resolving ``And``/``But`` from context."""
    previous: str | None = None
    for step in steps:
        step_type = _resolve_step_type(getattr(step, "keyword", ""), previous)
        if step_type:
            step.step_type = step_type
            previous = step_type
    return steps


def _iter_feature_steps(feature: Any) -> list[Step]:
    """Return all concrete steps in a feature, expanding Scenario Outlines by example rows."""
    steps: list[Step] = []
    if feature.background:
        steps.extend(_attach_step_types(list(feature.background.steps)))
    for scenario in feature.all_scenarios():
        if isinstance(scenario, ScenarioOutline) and scenario.examples:
            for row in scenario.expand():
                expanded = [_expand_step(step, row) for step in scenario.steps]
                steps.extend(_attach_step_types(expanded))
        else:
            steps.extend(_attach_step_types(list(getattr(scenario, "steps", []))))
    return steps


def normalize_step_text(text: str) -> str:
    """Normalize step text for matching: strip keyword, collapse whitespace."""
    stripped = text.strip()
    # Strip a leading keyword (case-insensitive) if present.
    # Use split(maxsplit=1) to handle any whitespace (space, tab, etc.).
    parts = stripped.split(maxsplit=1)
    if parts and parts[0].lower() in _STEP_KEYWORDS:
        stripped = parts[1] if len(parts) > 1 else ""
    return re.sub(r"\s+", " ", stripped).strip()


def _match_step(
    step: Any,
    definitions: list[StepDefinition],
) -> StepMatch:
    """Match a single step against all definitions.

    A step only matches definitions registered for its keyword type (``given``,
    ``when`` or ``then``) or universal ``step`` definitions. This mirrors Behave's
    step registry behaviour and avoids false positives when the same pattern is
    reused across keywords.
    """
    text = normalize_step_text(getattr(step, "name", "") or getattr(step, "text", ""))
    step_type = getattr(step, "step_type", "")
    matches = [
        d
        for d in definitions
        if d.keyword == step_type or d.keyword == "step"
        if d.pattern_compiled.fullmatch(text)
    ]
    if not matches:
        return StepMatch(step=step, step_definition=None, ambiguous=False)
    if len(matches) == 1:
        return StepMatch(step=step, step_definition=matches[0], ambiguous=False)
    return StepMatch(step=step, step_definition=matches[0], ambiguous=True)


def _relative_import_target(level: int, module: str | None, current_module: str) -> str | None:
    """Resolve the dotted target of a relative ``ImportFrom``.

    ``current_module`` is the dotted name of the file containing the import,
    relative to the steps directory. Returns ``None`` when the import goes
    above the steps directory.
    """
    parts = current_module.split(".")
    if level > len(parts):
        return None
    package = ".".join(parts[:-level]) if level < len(parts) else ""
    if module:
        return f"{package}.{module}" if package else module
    # `from . import a` – the module is in the alias name, resolved below.
    return package


def _extract_module_imports(file: Path, current_module: str = "") -> set[str]:
    """Parse a Python file and return the set of modules it imports."""
    imports: set[str] = set()
    try:
        tree = ast.parse(file.read_text(encoding="utf-8-sig"), filename=str(file))
    except (SyntaxError, OSError, UnicodeError):
        return imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                continue
            if node.level:
                base = _relative_import_target(node.level, node.module, current_module)
                if base is None:
                    continue
                if node.module:
                    imports.add(base)
                else:
                    for alias in node.names:
                        if alias.name == "*":
                            continue
                        imports.add(f"{base}.{alias.name}" if base else alias.name)
            elif node.module:
                imports.add(node.module)
    return imports


def build_graph(
    project: Project,
    step_definitions: list[StepDefinition],
) -> DependencyGraph:
    """Build a ``DependencyGraph`` from a project and its step definitions.

    Args:
        project: The behave-model ``Project`` containing features/scenarios/steps.
        step_definitions: All discovered step definitions.

    Returns:
        A ``DependencyGraph`` with one ``StepMatch`` per step, plus
        ``feature_steps``, ``step_usage`` and ``module_imports`` mappings.
    """
    graph = DependencyGraph()

    for feature in project.features:
        feature_name = feature.name or ""
        if not feature_name:
            feature_location = getattr(feature, "location", None)
            feature_name = getattr(feature_location, "filename", "") or ""
        if not feature_name:
            feature_name = "<unnamed>"
        for step in _iter_feature_steps(feature):
            match = _match_step(step, step_definitions)
            graph.add_step_match(match, feature_name=feature_name)

    # Build module_imports from each step definition's source file.
    seen_files: dict[Path, str] = {}
    for definition in step_definitions:
        if definition.file in seen_files:
            continue
        module_name = definition.module
        seen_files[definition.file] = module_name
        graph.module_imports[module_name] = _extract_module_imports(definition.file, module_name)

    return graph

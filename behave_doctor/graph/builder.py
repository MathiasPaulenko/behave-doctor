"""Graph builder — match feature steps to definitions and build DependencyGraph."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from behave_model import Project

from behave_doctor.model.dependency_graph import DependencyGraph
from behave_doctor.model.step_definition import StepDefinition
from behave_doctor.model.step_match import StepMatch

# Keywords that may prefix a step line and must be stripped before matching.
_STEP_KEYWORDS = {"given", "when", "then", "and", "but", "*"}


def normalize_step_text(text: str) -> str:
    """Normalize step text for matching: strip keyword, collapse whitespace."""
    stripped = text.strip()
    # Strip a leading keyword (case-insensitive) if present.
    first, _, rest = stripped.partition(" ")
    if first.lower() in _STEP_KEYWORDS:
        stripped = rest.strip()
    return re.sub(r"\s+", " ", stripped).strip()


def _match_step(
    step: Any,
    definitions: list[StepDefinition],
) -> StepMatch:
    """Match a single step against all definitions."""
    text = normalize_step_text(getattr(step, "name", "") or getattr(step, "text", ""))
    matches = [d for d in definitions if d.pattern_compiled.match(text)]
    if not matches:
        return StepMatch(step=step, step_definition=None, ambiguous=False)
    if len(matches) == 1:
        return StepMatch(step=step, step_definition=matches[0], ambiguous=False)
    return StepMatch(step=step, step_definition=matches[0], ambiguous=True)


def _extract_module_imports(file: Path) -> set[str]:
    """Parse a Python file and return the set of modules it imports."""
    imports: set[str] = set()
    try:
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
    except SyntaxError:
        return imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
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
        feature_name = feature.name or feature.location.filename or "<unnamed>"
        for step in feature.all_steps():
            match = _match_step(step, step_definitions)
            graph.add_step_match(match, feature_name=feature_name)

    # Build module_imports from each step definition's source file.
    seen_files: dict[Path, str] = {}
    for definition in step_definitions:
        if definition.file in seen_files:
            continue
        module_name = definition.module
        seen_files[definition.file] = module_name
        graph.module_imports[module_name] = _extract_module_imports(definition.file)

    return graph

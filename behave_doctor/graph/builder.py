"""Graph builder — match feature steps to definitions and build DependencyGraph."""

from __future__ import annotations

import ast
import dataclasses
import re
import tokenize
from pathlib import Path
from typing import Any

from behave_model import Project, ScenarioOutline, Step

from behave_doctor.model.dependency_graph import DependencyGraph
from behave_doctor.model.step_definition import StepDefinition
from behave_doctor.model.step_match import StepMatch

# Placeholders used in Scenario Outline steps, e.g. ``<name>``.
_OUTLINE_PLACEHOLDER_RE = re.compile(r"<([A-Za-z_][A-Za-z0-9_]*)>")

# Canonical step types that open a step-type chain.
_PRIMARY_TYPES = {"given", "when", "then"}
# Keywords whose steps inherit the type of the preceding step.
_INHERITING_TYPES = {"and", "but"}


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


def _step_keyword_map(language: str | None) -> dict[str, str]:
    """Map normalised Gherkin keywords to canonical step types for ``language``.

    Uses behave's own i18n tables so localised keywords (``Dado``, ``Y``,
    ``Entonces``…) resolve exactly as the runtime parser resolves them.
    ``*`` is excluded on purpose: it is a generic step whose type is taken
    from the previous step.
    """
    try:
        from behave.i18n import languages
    except ImportError:  # pragma: no cover — behave is always installed
        languages = {}
    data = languages.get(language or "en") or languages.get("en") or {}
    mapping: dict[str, str] = {}
    for step_type in ("given", "when", "then", "and", "but"):
        for keyword in data.get(step_type, []):
            key = keyword.strip().lower()
            if key and key != "*":
                mapping.setdefault(key, step_type)
    return mapping


def _resolve_step_type(
    keyword: str,
    previous: str | None,
    keyword_map: dict[str, str],
) -> str | None:
    """Return the canonical step type for a Gherkin keyword.

    Mirrors the runtime parser (``behave.parser``):

    * ``And``/``But`` (and their localised forms) inherit the previous step
      type. With no previous step, behave uses the last Background step type
      — the caller supplies it as ``previous``.
    * ``*`` inherits the previous step type, defaulting to ``"given"`` when
      it is the first step (behave's keyword loop resolves ``*`` under
      ``given``).
    * Unknown keywords fall back to the previous type.
    """
    key = keyword.strip().lower()
    if key == "*":
        return previous or "given"
    step_type = keyword_map.get(key, key if key in _PRIMARY_TYPES else None)
    if step_type in _PRIMARY_TYPES:
        return step_type
    if step_type in _INHERITING_TYPES:
        return previous
    return previous


def _attach_step_types(
    steps: list[Step],
    keyword_map: dict[str, str],
    previous: str | None = None,
) -> list[Step]:
    """Return copies of ``steps`` with ``step_type`` set, resolving ``And``/``But``.

    ``previous`` is the step type that precedes the sequence — typically the
    last Background step type, which an initial ``And``/``But`` inherits at
    runtime. Copies are returned because ``step_type`` depends on context and
    ``Step`` objects may be shared between iterations.
    """
    out: list[Step] = []
    for step in steps:
        step_type = _resolve_step_type(getattr(step, "keyword", ""), previous, keyword_map)
        new_step = dataclasses.replace(step)
        new_step.step_type = step_type or ""
        out.append(new_step)
        if step_type:
            previous = step_type
    return out


def _scenario_steps(
    scenario: Any,
    keyword_map: dict[str, str],
    previous: str | None,
) -> list[Step]:
    """Return the typed steps of a scenario, expanding Scenario Outline rows."""
    if isinstance(scenario, ScenarioOutline) and scenario.examples:
        steps: list[Step] = []
        for example in scenario.examples:
            table = getattr(example, "table", None)
            if table is None:
                continue
            for row in table.iter_dicts():
                expanded = [_expand_step(step, row) for step in scenario.steps]
                steps.extend(_attach_step_types(expanded, keyword_map, previous))
        return steps
    return _attach_step_types(list(getattr(scenario, "steps", [])), keyword_map, previous)


def _iter_feature_steps(feature: Any) -> list[Step]:
    """Return all concrete steps in a feature, expanding Scenario Outlines.

    Feature-level Background steps are included once; Rule-level backgrounds
    (Gherkin v6, behave 1.3) are included per rule. Step-type chains honour
    background inheritance: a scenario's leading ``And`` inherits the last
    background step type of its container.
    """
    keyword_map = _step_keyword_map(getattr(feature, "language", None))
    steps: list[Step] = []
    last_bg_type: str | None = None
    if feature.background:
        bg_steps = _attach_step_types(list(feature.background.steps), keyword_map)
        steps.extend(bg_steps)
        if bg_steps:
            last_bg_type = getattr(bg_steps[-1], "step_type", None)
    for scenario in getattr(feature, "scenarios", []):
        steps.extend(_scenario_steps(scenario, keyword_map, last_bg_type))
    for rule in getattr(feature, "rules", []) or []:
        # A rule's Background extends the feature Background for its scenarios.
        rule_bg_last = last_bg_type
        rule_background = getattr(rule, "background", None)
        if rule_background:
            rb_steps = _attach_step_types(
                list(rule_background.steps), keyword_map, previous=last_bg_type
            )
            steps.extend(rb_steps)
            if rb_steps:
                rule_bg_last = getattr(rb_steps[-1], "step_type", None)
        for scenario in getattr(rule, "scenarios", []):
            steps.extend(_scenario_steps(scenario, keyword_map, rule_bg_last))
    return steps


def normalize_step_text(text: str) -> str:
    """Normalize step text for matching.

    ``step.name`` never contains the Gherkin keyword, and behave matches
    step names verbatim — internal whitespace is significant, so only
    surrounding whitespace is stripped.
    """
    return text.strip()


def _definition_matches(definition: StepDefinition, text: str) -> bool:
    """Return ``True`` if ``definition`` matches ``text``.

    Uses the matcher's ``match()`` semantics: a match with a failing type
    converter still counts as matched (the definition exists and would be
    selected at runtime, even though running it would raise).
    """
    try:
        return definition.matcher.match(text) is not None
    except Exception:
        return False


def _match_step(
    step: Any,
    definitions: list[StepDefinition],
) -> StepMatch:
    """Match a single step against all definitions.

    A step only matches definitions registered for its keyword type (``given``,
    ``when`` or ``then``) or universal ``step`` definitions. This mirrors Behave's
    step registry behaviour and avoids false positives when the same pattern is
    reused across keywords.

    Behave's ``StepRegistry.find_match`` iterates the keyword registry first
    and the universal ``step`` registry second, returning the first match —
    so the selected definition is the first keyword match, not the first
    file-scan match.
    """
    text = normalize_step_text(getattr(step, "name", "") or "")
    step_type = getattr(step, "step_type", "")
    keyword_matches: list[StepDefinition] = []
    step_matches: list[StepDefinition] = []
    for d in definitions:
        if not _definition_matches(d, text):
            continue
        if d.keyword == step_type:
            keyword_matches.append(d)
        elif d.keyword == "step":
            step_matches.append(d)
    matches = keyword_matches + step_matches
    if not matches:
        return StepMatch(step=step, step_definition=None, ambiguous=False)
    return StepMatch(
        step=step,
        step_definition=matches[0],
        ambiguous=len(matches) > 1,
        matches=tuple(matches),
    )


def _relative_import_target(
    level: int,
    module: str | None,
    current_module: str,
    *,
    is_package_init: bool = False,
) -> str | None:
    """Resolve the dotted target of a relative ``ImportFrom``.

    ``current_module`` is the dotted name of the file containing the import,
    relative to the steps directory. ``is_package_init`` marks ``__init__.py``
    files, whose ``from . import x`` refers to the package itself — one level
    less than a regular module file. Returns ``None`` when the import goes
    above the steps directory.
    """
    parts = current_module.split(".")
    depth = level - 1 if is_package_init else level
    if depth > len(parts):
        return None
    package = ".".join(parts[: len(parts) - depth]) if depth else current_module
    if module:
        return f"{package}.{module}" if package else module
    # `from . import a` – the module is in the alias name, resolved below.
    return package


def _extract_module_imports(file: Path, current_module: str = "") -> set[str]:
    """Parse a Python file and return the set of modules it imports."""
    imports: set[str] = set()
    try:
        # ``tokenize.open`` matches interpreter decoding (BOM + coding cookie).
        with tokenize.open(file) as handle:
            tree = ast.parse(handle.read(), filename=str(file))
    except (SyntaxError, OSError, UnicodeError, ValueError):
        # ValueError: ast.parse raises it for null bytes on Python < 3.12.
        return imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                continue
            if node.level:
                base = _relative_import_target(
                    node.level,
                    node.module,
                    current_module,
                    is_package_init=file.name == "__init__.py",
                )
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
        # Two files can collapse to the same module name (``a.py`` and
        # ``a/__init__.py``): merge their imports rather than overwrite.
        graph.module_imports.setdefault(module_name, set()).update(
            _extract_module_imports(definition.file, module_name)
        )

    return graph

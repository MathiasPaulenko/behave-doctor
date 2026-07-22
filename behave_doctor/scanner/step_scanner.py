"""Step scanner — extract StepDefinition objects from Python source via AST."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

from behave_doctor.model.config import DoctorConfig
from behave_doctor.model.step_definition import StepDefinition

# Decorator names that mark step definitions, mapped to the canonical keyword.
_STEP_KEYWORDS: dict[str, str] = {
    "given": "given",
    "when": "when",
    "then": "then",
    "step": "step",
}

# Regex to find {name} placeholders in parse-type patterns.
_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _compile_parse_pattern(pattern: str) -> re.Pattern[str]:
    """Compile a parse-type pattern, preserving ``{name}`` placeholders as groups."""
    out: list[str] = ["^"]
    i = 0
    while i < len(pattern):
        match = _PLACEHOLDER_RE.match(pattern, i)
        if match:
            out.append(f"(?P<{match.group(1)}>.+)")
            i = match.end()
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out))


def extract_parameters(pattern: str, matcher_type: str) -> list[str]:
    """Extract parameter names from a step pattern."""
    if matcher_type == "re":
        body = pattern[3:] if pattern.startswith("re:") else pattern
        try:
            compiled = re.compile(body)
        except re.error:
            return []
        return [name for name in compiled.groupindex if name]
    return _PLACEHOLDER_RE.findall(pattern)


def _decorator_name(node: ast.expr) -> str | None:
    """Return the simple name a decorator is called with, if any.

    Handles ``given``, ``given`` (attribute access returns the attribute name).
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _decorator_call(node: ast.expr) -> ast.Call | None:
    """Return the underlying ``ast.Call`` for a decorator node.

    Decorators may be bare references or calls; we only care about calls
    that carry a pattern argument.
    """
    if isinstance(node, ast.Call):
        return node
    return None


def _resolve_keyword(
    node: ast.expr,
    alias_map: dict[str, str],
    behave_imported: bool,
) -> str | None:
    """Resolve a decorator node to a canonical step keyword, or ``None``."""
    call = _decorator_call(node)
    target = call.func if call else node

    # Direct or aliased name: @given(...) / @g(...)
    if isinstance(target, ast.Name):
        name = target.id
        if name in alias_map:
            return alias_map[name]
        if name in _STEP_KEYWORDS:
            return _STEP_KEYWORDS[name]
        return None

    # Attribute access: @behave.given(...)
    if isinstance(target, ast.Attribute):
        if isinstance(target.value, ast.Name) and target.value.id == "behave":
            return _STEP_KEYWORDS.get(target.attr)
        return None

    return None


def _first_string_arg(call: ast.Call) -> str | None:
    """Return the first positional string-literal argument of a call, if any."""
    for arg in call.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
    return None


def _has_converter_kwarg(call: ast.Call) -> bool:
    """Return ``True`` if the call has a ``converter=`` keyword argument."""
    return any(kw.arg == "converter" for kw in call.keywords)


def _build_alias_map(tree: ast.AST) -> tuple[dict[str, str], bool]:
    """Build a map of aliased step decorators and detect ``import behave``.

    Returns a tuple ``(alias_map, behave_imported)`` where ``alias_map`` maps
    the local alias name to the canonical keyword (e.g. ``{"g": "given"}``).
    """
    alias_map: dict[str, str] = {}
    behave_imported = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module != "behave":
                continue
            for alias in node.names:
                base = alias.name
                if base in _STEP_KEYWORDS:
                    local = alias.asname or base
                    alias_map[local] = _STEP_KEYWORDS[base]
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "behave":
                    behave_imported = True
    return alias_map, behave_imported


def _module_dotted_path(file: Path, steps_path: Path) -> str:
    """Return the dotted module path of ``file`` relative to ``steps_path``."""
    relative = file.relative_to(steps_path)
    parts = list(relative.with_suffix("").parts)
    return ".".join(parts)


def scan_steps(steps_path: Path, config: DoctorConfig) -> list[StepDefinition]:
    """Scan a steps directory and return all discovered step definitions.

    Args:
        steps_path: Directory containing step definition ``.py`` files.
        config: Configuration (currently unused but reserved for filtering).

    Returns:
        A list of ``StepDefinition`` objects. If ``steps_path`` does not
        exist, an empty list is returned. Malformed Python files are skipped
        with a warning printed to stderr.
    """
    del config  # reserved for future filtering/exclude support

    if not steps_path.exists():
        return []

    definitions: list[StepDefinition] = []
    for py_file in sorted(steps_path.rglob("*.py")):
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError as exc:
            print(
                f"Warning: could not parse {py_file}: {exc}. Skipping this file.",
                file=sys.stderr,
            )
            continue

        alias_map, behave_imported = _build_alias_map(tree)
        module = _module_dotted_path(py_file, steps_path)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                call = _decorator_call(decorator)
                if call is None:
                    continue
                keyword = _resolve_keyword(decorator, alias_map, behave_imported)
                if keyword is None:
                    continue
                pattern = _first_string_arg(call)
                if pattern is None:
                    continue
                if pattern.startswith("re:"):
                    matcher_type = "re"
                elif _has_converter_kwarg(call):
                    matcher_type = "cfparse"
                else:
                    matcher_type = "parse"

                if matcher_type == "re":
                    body = pattern[3:] if pattern.startswith("re:") else pattern
                    try:
                        pattern_compiled = re.compile(f"^{body}")
                    except re.error:
                        continue
                else:
                    pattern_compiled = _compile_parse_pattern(pattern)

                parameters = extract_parameters(pattern, matcher_type)
                definitions.append(
                    StepDefinition(
                        keyword=keyword,
                        pattern=pattern,
                        pattern_compiled=pattern_compiled,
                        matcher_type=matcher_type,
                        file=py_file,
                        line=decorator.lineno,
                        function_name=node.name,
                        module=module,
                        parameters=parameters,
                    )
                )
    return definitions

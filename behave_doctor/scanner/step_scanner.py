"""Step scanner — extract StepDefinition objects from Python source via AST."""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path

from behave_doctor.model.config import DoctorConfig
from behave_doctor.model.step_definition import StepDefinition

logger = logging.getLogger(__name__)

# Decorator names that mark step definitions, mapped to the canonical keyword.
_STEP_KEYWORDS: dict[str, str] = {
    "given": "given",
    "when": "when",
    "then": "then",
    "step": "step",
}

# Regex to find {name} and {name:type} placeholders in parse/cfparse patterns.
_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)(?::[^}]*)?\}")


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
    module_aliases: set[str],
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

    # Attribute access: @behave.given(...) / @b.when(...)
    if isinstance(target, ast.Attribute):
        if isinstance(target.value, ast.Name) and target.value.id in module_aliases:
            return _STEP_KEYWORDS.get(target.attr)
        return None

    return None


def _first_string_arg(call: ast.Call) -> str | None:
    """Return the step pattern string from a decorator call.

    Behave step decorators accept the pattern as the first positional argument
    or as the ``pattern=`` keyword argument. This function returns the first
    string literal found in either location.
    """
    for arg in call.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
    for keyword in call.keywords:
        if keyword.arg == "pattern":
            value = keyword.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                return value.value
    return None


def _has_converter_kwarg(call: ast.Call) -> bool:
    """Return ``True`` if the call has a ``converter=`` keyword argument."""
    return any(kw.arg == "converter" for kw in call.keywords)


def _build_alias_map(tree: ast.AST) -> tuple[dict[str, str], set[str]]:
    """Build a map of aliased step decorators and module aliases.

    Returns ``alias_map`` mapping the local alias name to the canonical keyword
    (e.g. ``{"g": "given"}``), and ``module_aliases`` containing the names
    that refer to the ``behave`` module (e.g. ``{"behave", "b"}``).
    """
    alias_map: dict[str, str] = {}
    module_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module != "behave":
                continue
            # `from behave import *` makes the canonical step decorators available.
            if any(alias.name == "*" for alias in node.names):
                for base in _STEP_KEYWORDS:
                    alias_map.setdefault(base, _STEP_KEYWORDS[base])
            for alias in node.names:
                base = alias.name
                if base in _STEP_KEYWORDS:
                    local = alias.asname or base
                    alias_map[local] = _STEP_KEYWORDS[base]
        elif isinstance(node, ast.Import):
            for alias in node.names:
                # For "import behave" or "import behave.given", the name bound
                # in the module namespace is the top-level package (behave).
                # If an asname is present, only that alias is bound.
                if alias.name == "behave" or alias.name.startswith("behave."):
                    local = alias.asname or alias.name.split(".")[0]
                    module_aliases.add(local)
    return alias_map, module_aliases


class _StepFunctionCollector(ast.NodeVisitor):
    """Collect module-level functions/async functions, excluding nested and class methods."""

    def __init__(self) -> None:
        self.functions: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
        self._func_depth = 0
        self._class_depth = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        if self._func_depth == 0 and self._class_depth == 0:
            self.functions.append(node)
        self._func_depth += 1
        self.generic_visit(node)
        self._func_depth -= 1

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        if self._func_depth == 0 and self._class_depth == 0:
            self.functions.append(node)
        self._func_depth += 1
        self.generic_visit(node)
        self._func_depth -= 1

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self._class_depth += 1
        self.generic_visit(node)
        self._class_depth -= 1


def _module_dotted_path(file: Path, steps_path: Path) -> str:
    """Return the dotted module path of ``file`` relative to ``steps_path``."""
    relative = file.relative_to(steps_path)
    parts = list(relative.with_suffix("").parts)
    return ".".join(parts)


def scan_steps(steps_path: Path, config: DoctorConfig) -> list[StepDefinition]:
    """Scan a steps directory and return all discovered step definitions.

    Args:
        steps_path: Directory containing step definition ``.py`` files.
        config: Configuration (used for ``exclude_paths`` filtering).

    Returns:
        A list of ``StepDefinition`` objects. If ``steps_path`` does not
        exist, an empty list is returned. Malformed Python files are skipped
        with a warning printed to stderr.
    """
    if not steps_path.exists():
        return []

    definitions: list[StepDefinition] = []
    for py_file in sorted(steps_path.rglob("*.py")):
        if config.is_excluded(py_file):
            continue
        try:
            source = py_file.read_text(encoding="utf-8-sig")
            tree = ast.parse(source, filename=str(py_file))
        except (SyntaxError, OSError, UnicodeError) as exc:
            logger.warning("Could not parse %s: %s. Skipping this file.", py_file, exc)
            continue

        alias_map, module_aliases = _build_alias_map(tree)
        try:
            module = _module_dotted_path(py_file, steps_path)
        except ValueError:
            # File is not under steps_path (e.g. via symlink). Skip it.
            continue

        collector = _StepFunctionCollector()
        collector.visit(tree)
        for node in collector.functions:
            for decorator in node.decorator_list:
                call = _decorator_call(decorator)
                if call is None:
                    continue
                keyword = _resolve_keyword(decorator, alias_map, module_aliases)
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

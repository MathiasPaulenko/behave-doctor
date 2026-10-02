"""Step scanner — extract StepDefinition objects from Python source via AST.

Mirrors Behave's runtime registration semantics:

* The step-matcher is selected per module via ``use_step_matcher(name)`` /
  ``use_default_step_matcher(name)`` calls, applied in source order.
* Patterns are compiled with Behave's own matcher classes
  (``ParseMatcher``, ``CFParseMatcher``, ``SimplifiedRegexMatcher``,
  ``CucumberRegexMatcher``), so matching behaviour is identical to runtime.
* Definitions whose pattern fails to compile are skipped, just like
  ``StepRegistry.is_good_step_definition`` ignores them at runtime.  When a
  parse/cfparse pattern uses a custom ``register_type`` that cannot be known
  statically, an approximate matcher is used instead (``approximate=True``).
"""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from typing import Any

from behave.matchers import (
    CFParseMatcher,
    CucumberRegexMatcher,
    Matcher,
    ParseMatcher,
    SimplifiedRegexMatcher,
)

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

# Behave step-matcher names mapped to their matcher classes.
_STEP_MATCHERS: dict[str, type[Matcher]] = {
    "parse": ParseMatcher,
    "cfparse": CFParseMatcher,
    "re": SimplifiedRegexMatcher,
    "re0": CucumberRegexMatcher,
}

_DEFAULT_MATCHER = "parse"

# Functions that change the active step-matcher when called at module level.
_MATCHER_FUNCS = {"use_step_matcher", "use_default_step_matcher"}

# Regex to find ``{name}``, ``{name:type}`` and anonymous ``{}`` placeholders
# in parse/cfparse patterns.
_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)?(?::([^{}]*))?\}")


class _ApproximateMatcher(Matcher):  # type: ignore[misc]  # behave is untyped
    """Fallback matcher for patterns Behave could not compile statically.

    Used when a parse/cfparse pattern references a custom type that is only
    registered at runtime via ``behave.register_type``.  Unknown type specs
    degrade to a permissive ``.+?`` wildcard.
    """

    NAME = "approximate"

    def __init__(self, func: Any, pattern: str, step_type: str | None = None) -> None:
        super().__init__(func, pattern, step_type)
        self._regex = re.compile(_compile_parse_expression(pattern))

    @property
    def regex_pattern(self) -> str:
        return self._regex.pattern

    def compile(self) -> _ApproximateMatcher:
        return self

    def check_match(self, step_text: str) -> list[Any] | None:
        return [] if self._regex.fullmatch(step_text) else None


def _compile_parse_expression(pattern: str) -> str:
    """Translate a parse-style pattern into an approximate regex string.

    ``{name}``, ``{name:type}`` and anonymous ``{}`` placeholders all become
    permissive groups; everything else is escaped literally.  ``{{`` and
    ``}}`` are treated as literal braces, like ``parse`` does.
    """
    out: list[str] = []
    i = 0
    n = len(pattern)
    while i < n:
        ch = pattern[i]
        if ch == "{" and i + 1 < n and pattern[i + 1] == "{":
            out.append(re.escape("{"))
            i += 2
            continue
        if ch == "}" and i + 1 < n and pattern[i + 1] == "}":
            out.append(re.escape("}"))
            i += 2
            continue
        match = _PLACEHOLDER_RE.match(pattern, i)
        if match:
            name = match.group(1)
            out.append(f"(?P<{name}>.+?)" if name else "(.+?)")
            i = match.end()
            continue
        out.append(re.escape(ch))
        i += 1
    return "".join(out)


def _extract_placeholder_names(pattern: str) -> list[str]:
    """Extract named placeholder names from a parse-style pattern."""
    return [m.group(1) for m in _PLACEHOLDER_RE.finditer(pattern) if m.group(1)]


def _wildcard_converter() -> Any:
    """A parse type-converter that matches anything (for unknown custom types)."""
    import parse

    @parse.with_pattern(r".+?")  # type: ignore[untyped-decorator]  # parse is untyped
    def _wildcard(text: str) -> str:
        return text

    return _wildcard


def _make_parse_matcher(matcher_name: str, func: Any, pattern: str) -> tuple[Matcher, bool]:
    """Instantiate a Behave parse/cfparse matcher for ``pattern``.

    Returns ``(matcher, approximate)``.  If the pattern references custom
    types that are only registered at runtime, ``MissingTypeError`` is caught
    and the pattern is retried with permissive wildcard types; the second
    return value flags the result as approximate.
    """
    matcher_cls = _STEP_MATCHERS.get(matcher_name, ParseMatcher)
    try:
        return matcher_cls(func, pattern), False
    except Exception as exc:
        if _missing_type_name(exc) is None:
            raise

    # Retry, feeding wildcard converters for every custom type name that is
    # not part of the parser's built-in registry.
    parser_cls = matcher_cls.PARSER_CLASS
    case_sensitive = getattr(matcher_cls, "CASE_SENSITIVE", True)
    extra_types: dict[str, Any] = {}
    for _ in range(16):  # bounded retry loop — one new name per iteration
        try:
            parser = parser_cls(pattern, extra_types=extra_types, case_sensitive=case_sensitive)
            break
        except Exception as exc:
            name = _missing_type_name(exc)
            if name is None or name in extra_types:
                raise  # pragma: no cover — defensive: wildcarded types register
            extra_types[name] = _wildcard_converter()
    else:  # pragma: no cover — safety net; the loop always breaks or raises
        raise RuntimeError(f"Cannot compile pattern: {pattern}")

    # Bypass ParseMatcher.__init__ (it would rebuild the parser and fail on
    # the unknown custom types again): initialise the base Matcher and inject
    # the parser we built with wildcard types.
    matcher = matcher_cls.__new__(matcher_cls)
    Matcher.__init__(matcher, func, pattern)
    matcher.parser = parser
    return matcher, True


def _missing_type_name(exc: BaseException) -> str | None:
    """Extract the missing type name from a parser construction error.

    Two shapes appear depending on the parser: ``MissingTypeError`` carries the
    type name as ``args[0]`` (cfparse with cardinality suffixes), while
    ``parse.Parser`` wraps it in ``ValueError("format spec 'X' not
    recognised")``. Cardinality suffixes (``+``, ``*``, ``?``) are stripped.
    """
    args = getattr(exc, "args", ())
    if not args:
        return None
    text = str(args[0])
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", text):
        return text
    spec = re.search(r"format spec '([^']+)'", str(exc))
    if spec:
        name = re.split(r"[+*?]", spec.group(1))[0]
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            return name
    return None


def _make_matcher(matcher_name: str, func: Any, pattern: str) -> tuple[Matcher, bool]:
    """Build a Behave matcher for ``pattern``.

    Returns ``(matcher, approximate)``.  Raises on patterns that Behave would
    reject outright (bad regexes, ``^``/``$`` anchors with the ``re`` matcher).
    """
    if matcher_name in ("parse", "cfparse"):
        try:
            return _make_parse_matcher(matcher_name, func, pattern)
        except Exception:
            # Behave would drop this definition (is_good_step_definition),
            # but a static fallback keeps it visible for coverage rules.
            return _ApproximateMatcher(func, pattern), True

    # ``_matcher_at`` normalises unknown names to "parse" before we get here.
    matcher_cls = _STEP_MATCHERS.get(matcher_name, ParseMatcher)
    matcher = matcher_cls(func, pattern)
    # Behave runs compile() in is_good_step_definition and ignores defs whose
    # pattern fails to compile — mirror that so bad regexes are dropped.
    matcher.compile()
    return matcher, False


def _extract_parameters(matcher: Matcher, matcher_name: str, pattern: str) -> list[str]:
    """Extract parameter names from a compiled matcher."""
    if matcher_name in ("re", "re0"):
        regex = getattr(matcher, "regex", None)
        if regex is None:  # pragma: no cover — compiled matchers always set it
            return []
        named = list(regex.groupindex)
        anonymous = regex.groups - len(named)
        return named + [f"arg{i}" for i in range(anonymous)]

    parser = getattr(matcher, "parser", None)
    if parser is not None:
        named = list(getattr(parser, "named_fields", []) or [])
        fixed = list(getattr(parser, "fixed_fields", []) or [])
        return named + [f"arg{i}" for i in range(len(fixed))]

    if isinstance(matcher, _ApproximateMatcher):
        return _extract_placeholder_names(pattern)
    return []  # pragma: no cover — unreachable for the known matcher types


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
    shadowed_names: set[str],
) -> str | None:
    """Resolve a decorator node to a canonical step keyword, or ``None``."""
    call = _decorator_call(node)
    target = call.func if call else node

    # Direct or aliased name: @given(...) / @g(...) / @Given(...)
    if isinstance(target, ast.Name):
        name = target.id
        if name in alias_map:
            return alias_map[name]
        # Bare names count as step decorators unless an import from another
        # module binds the name to something else (e.g. ``hypothesis.given``).
        if name not in shadowed_names:
            return _STEP_KEYWORDS.get(name.lower())
        return None

    # Attribute access: @behave.given(...) / @b.when(...)
    if isinstance(target, ast.Attribute):
        if isinstance(target.value, ast.Name) and target.value.id in module_aliases:
            return _STEP_KEYWORDS.get(target.attr.lower())
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


def _build_alias_map(tree: ast.AST) -> tuple[dict[str, str], set[str], dict[str, str], set[str]]:
    """Build maps describing how the ``behave`` package is imported.

    Returns ``(alias_map, module_aliases, behave_names, shadowed_names)``:

    * ``alias_map``: local name → canonical step keyword for step decorators
      imported from ``behave`` (e.g. ``{"g": "given"}``).
    * ``module_aliases``: names bound to the ``behave`` package itself
      (e.g. ``{"behave", "b"}``).
    * ``behave_names``: local name → original name for any symbol imported
      from ``behave`` or its submodules (e.g. ``{"use_step_matcher": ...}``).
    * ``shadowed_names``: names imported from non-behave modules, so that
      e.g. ``from hypothesis import given`` is not mistaken for a step
      decorator.
    """
    alias_map: dict[str, str] = {}
    module_aliases: set[str] = set()
    behave_names: dict[str, str] = {}
    shadowed_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "__future__":
                continue
            is_behave = module == "behave" or module.startswith("behave.")
            # `from behave import *` makes the canonical step decorators and
            # use_step_matcher available.
            if is_behave and any(alias.name == "*" for alias in node.names):
                for base in _STEP_KEYWORDS:
                    alias_map.setdefault(base, _STEP_KEYWORDS[base])
                behave_names.setdefault("use_step_matcher", "use_step_matcher")
                behave_names.setdefault("use_default_step_matcher", "use_default_step_matcher")
            for alias in node.names:
                if alias.name == "*":
                    continue
                local = alias.asname or alias.name
                if is_behave:
                    behave_names[local] = alias.name
                    base = alias.name.lower()
                    if base in _STEP_KEYWORDS and module == "behave":
                        alias_map[local] = _STEP_KEYWORDS[base]
                else:
                    shadowed_names.add(local)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                # For "import behave" or "import behave.given", the name bound
                # in the module namespace is the top-level package (behave).
                # If an asname is present, only that alias is bound.
                if alias.name == "behave" or alias.name.startswith("behave."):
                    local = alias.asname or alias.name.split(".")[0]
                    module_aliases.add(local)
                else:
                    shadowed_names.add(alias.asname or alias.name.split(".")[0])

    return alias_map, module_aliases, behave_names, shadowed_names


class _MatcherEventCollector(ast.NodeVisitor):
    """Collect ``use_step_matcher(name)`` calls at module scope.

    Calls inside function or class bodies do not run unconditionally at import
    time, so they are ignored — matching how Behave applies the matcher while
    the module body executes top to bottom.
    """

    def __init__(self, behave_names: dict[str, str], module_aliases: set[str]) -> None:
        self._behave_names = behave_names
        self._module_aliases = module_aliases
        self.events: list[tuple[int, str]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        return  # nested scope — calls here do not run at import time

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        return

    def visit_Expr(self, node: ast.Expr) -> None:  # noqa: N802
        if not isinstance(node.value, ast.Call):
            return
        call = node.value
        func = call.func
        original: str | None = None
        if isinstance(func, ast.Name):
            original = self._behave_names.get(func.id)
        elif (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id in self._module_aliases
        ):
            original = func.attr
        if original not in _MATCHER_FUNCS:
            return
        name = self._call_name_arg(call)
        if name:
            self.events.append((call.lineno, name))

    @staticmethod
    def _call_name_arg(call: ast.Call) -> str | None:
        if (
            call.args
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
        ):
            return call.args[0].value
        for kw in call.keywords:
            if (
                kw.arg == "name"
                and isinstance(kw.value, ast.Constant)
                and isinstance(kw.value.value, str)
            ):
                return kw.value.value
        return None


def _matcher_events(
    tree: ast.AST, behave_names: dict[str, str], module_aliases: set[str]
) -> list[tuple[int, str]]:
    """Collect ``use_step_matcher(name)`` calls with their source line numbers."""
    collector = _MatcherEventCollector(behave_names, module_aliases)
    collector.visit(tree)
    return sorted(collector.events)


def _matcher_at(line: int, events: list[tuple[int, str]]) -> str:
    """Return the matcher name in effect at ``line`` given ordered events."""
    current = _DEFAULT_MATCHER
    for lineno, name in events:
        if lineno >= line:
            break
        current = name
    if current not in _STEP_MATCHERS:
        logger.warning("Unknown step matcher %r; falling back to 'parse'.", current)
        return _DEFAULT_MATCHER
    return current


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


def _step_func_stub() -> None:
    """Placeholder function for matcher construction (never called)."""


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

        alias_map, module_aliases, behave_names, shadowed = _build_alias_map(tree)
        events = _matcher_events(tree, behave_names, module_aliases)
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
                keyword = _resolve_keyword(decorator, alias_map, module_aliases, shadowed)
                if keyword is None:
                    continue
                pattern = _first_string_arg(call)
                if pattern is None:
                    continue

                matcher_name = _matcher_at(decorator.lineno, events)
                try:
                    matcher, approximate = _make_matcher(matcher_name, _step_func_stub, pattern)
                except Exception as exc:
                    # Behave drops un-compilable step definitions at
                    # registration time — mirror that behaviour.
                    logger.warning(
                        "Bad step definition %r in %s:%s (%s). Skipping.",
                        pattern,
                        py_file,
                        decorator.lineno,
                        exc,
                    )
                    continue

                parameters = _extract_parameters(matcher, matcher_name, pattern)
                definitions.append(
                    StepDefinition(
                        keyword=keyword,
                        pattern=pattern,
                        matcher=matcher,
                        matcher_type=matcher_name,
                        file=py_file,
                        line=decorator.lineno,
                        function_name=node.name,
                        module=module,
                        parameters=parameters,
                        approximate=approximate,
                    )
                )
    return definitions

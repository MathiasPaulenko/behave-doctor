"""Regression tests for behave 1.3.x compatibility fixes.

Covers: localised keywords, ``Rule:`` backgrounds and tags, ``And``/``But``/``*``
step-type inheritance, ``re``/``re0`` matcher semantics, and approximate
matching for runtime-registered custom types.
"""

from __future__ import annotations

from pathlib import Path

from behave_doctor.graph.builder import build_graph
from behave_doctor.model.config import DoctorConfig
from behave_doctor.model.dependency_graph import DependencyGraph
from behave_doctor.model.enums import Severity
from behave_doctor.rules.base import RuleContext
from behave_doctor.rules.coverage import OrphanScenario, UnparseableFeature
from behave_doctor.rules.quality import ScenarioNoTags
from behave_doctor.scanner import scan_features, scan_steps


def _project(tmp_path: Path, feature_text: str, steps_text: str) -> object:
    """Build (project, steps, graph) from inline sources."""
    features = tmp_path / "features"
    steps_dir = features / "steps"
    steps_dir.mkdir(parents=True, exist_ok=True)
    (features / "test.feature").write_text(feature_text, encoding="utf-8")
    (steps_dir / "steps.py").write_text(steps_text, encoding="utf-8")
    project = scan_features(tmp_path, DoctorConfig())
    defs = scan_steps(steps_dir, DoctorConfig())
    return project, defs, build_graph(project, defs)


def test_localized_feature_keywords_match(tmp_path: Path) -> None:
    """Steps in a ``# language: es`` feature match their definitions."""
    project, _, graph = _project(
        tmp_path,
        "# language: es\n"
        "Característica: login\n"
        "  Escenario: login\n"
        "    Dado que existe un usuario\n"
        "    Cuando inicia sesión\n"
        "    Entonces ve el panel\n"
        "    Y tiene 3 items\n",
        "from behave import given, when, then\n"
        '@given("que existe un usuario")\ndef g(ctx): pass\n'
        '@when("inicia sesión")\ndef w(ctx): pass\n'
        '@then("ve el panel")\ndef t1(ctx): pass\n'
        '@then("tiene {n:d} items")\ndef t2(n): pass\n',
    )
    assert len(graph.step_matches) == 4
    assert not any(m.step_definition is None for m in graph.step_matches)


def test_star_first_step_defaults_to_given(tmp_path: Path) -> None:
    """A leading ``*`` step resolves to the given registry, like behave."""
    _, _, graph = _project(
        tmp_path,
        "Feature: f\n  Scenario: s\n    * first step\n",
        'from behave import given\n@given("first step")\ndef g(ctx): pass\n',
    )
    assert len(graph.step_matches) == 1
    assert graph.step_matches[0].step_definition is not None


def test_and_inherits_last_background_step_type(tmp_path: Path) -> None:
    """A scenario starting with ``And`` inherits the Background step type."""
    _, _, graph = _project(
        tmp_path,
        "Feature: f\n  Background:\n    Given base state\n  Scenario: s\n    And more base state\n",
        "from behave import given\n"
        '@given("base state")\ndef g(ctx): pass\n'
        '@given("more base state")\ndef h(ctx): pass\n',
    )
    assert len(graph.step_matches) == 2
    assert not any(m.step_definition is None for m in graph.step_matches)


def test_rule_background_matches_and_inherits_tags(tmp_path: Path) -> None:
    """Rule backgrounds are matched; scenarios inside rules inherit rule tags."""
    project, _, graph = _project(
        tmp_path,
        "Feature: f\n"
        "  Background:\n"
        "    Given feature bg\n"
        "  @rule-tag\n"
        "  Rule: r\n"
        "    Background:\n"
        "      Given rule bg\n"
        "    Scenario: s\n"
        "      Given x\n"
        "    Scenario: s2\n"
        "      Given x\n",
        "from behave import given\n"
        '@given("feature bg")\ndef a(ctx): pass\n'
        '@given("rule bg")\ndef b(ctx): pass\n'
        '@given("x")\ndef c(ctx): pass\n',
    )
    # feature bg + rule bg (each once) + one step per rule scenario.
    assert len(graph.step_matches) == 4
    assert not any(m.step_definition is None for m in graph.step_matches)

    # The scenarios inside the rule inherit @rule-tag: BD202/BD304 must not fire.
    ctx = RuleContext(
        project=project,
        step_definitions=[],
        dependency_graph=DependencyGraph(),
        config=DoctorConfig(),
    )
    assert ScenarioNoTags().check(ctx) == []
    assert OrphanScenario().check(ctx) == []


def test_re_matcher_matches_regex(tmp_path: Path) -> None:
    """``use_step_matcher("re")`` patterns match as regexes."""
    _, _, graph = _project(
        tmp_path,
        "Feature: f\n  Scenario: s\n    When the user waits 5 seconds\n",
        "from behave import use_step_matcher, when\n"
        'use_step_matcher("re")\n'
        '@when(r"the user waits (\\d+) seconds")\ndef w(ctx, n): pass\n',
    )
    assert len(graph.step_matches) == 1
    assert graph.step_matches[0].step_definition is not None


def test_re_pattern_with_anchors_is_rejected(tmp_path: Path) -> None:
    """Behave ignores ``re`` patterns that contain ^/$ — the def must be skipped."""
    steps_dir = tmp_path / "steps"
    steps_dir.mkdir()
    (steps_dir / "s.py").write_text(
        "from behave import use_step_matcher, given\n"
        'use_step_matcher("re")\n'
        '@given(r"^anchored pattern$")\ndef g(ctx): pass\n',
        encoding="utf-8",
    )
    defs = scan_steps(steps_dir, DoctorConfig())
    assert defs == []


def test_re0_matcher_uses_unanchored_match(tmp_path: Path) -> None:
    """``use_step_matcher("re0")`` (CucumberRegexMatcher) uses ``re.match``:
    a pattern without anchors can match a prefix of the step text."""
    _, _, graph = _project(
        tmp_path,
        "Feature: f\n  Scenario: s\n    Given partial and more text\n",
        "from behave import use_step_matcher, given\n"
        'use_step_matcher("re0")\n'
        '@given("partial")\ndef g(ctx): pass\n',
    )
    assert len(graph.step_matches) == 1
    assert graph.step_matches[0].step_definition is not None


def test_custom_parse_type_uses_approximate_matcher(tmp_path: Path) -> None:
    """Patterns with runtime-registered custom types degrade to a permissive
    approximate matcher instead of disappearing."""
    steps_dir = tmp_path / "steps"
    steps_dir.mkdir()
    (steps_dir / "s.py").write_text(
        'from behave import given\n@given("the price is {p:Money}")\ndef g(ctx, p): pass\n',
        encoding="utf-8",
    )
    defs = scan_steps(steps_dir, DoctorConfig())
    assert len(defs) == 1
    assert defs[0].approximate is True
    assert defs[0].matcher.matches("the price is $10")


def test_unparseable_feature_reports_bd305(tmp_path: Path) -> None:
    """A feature that fails to parse surfaces a BD305 diagnostic."""
    features = tmp_path / "features"
    features.mkdir()
    (features / "bad.feature").write_text(
        "Feature: broken\n  Scenario: s\n    Given ok\n  Bad: syntax\n",
        encoding="utf-8",
    )
    errors: list[tuple[Path, str]] = []
    scan_features(tmp_path, DoctorConfig(), errors=errors)
    assert len(errors) == 1

    ctx = RuleContext(
        project=None,  # type: ignore[arg-type]
        step_definitions=[],
        dependency_graph=DependencyGraph(),
        config=DoctorConfig(),
        scan_errors=errors,
    )
    diagnostics = UnparseableFeature().check(ctx)
    assert len(diagnostics) == 1
    assert diagnostics[0].severity is Severity.ERROR
    assert diagnostics[0].file == features / "bad.feature"


def test_cli_unknown_option_reports_clean_error() -> None:
    """Unknown CLI flags print a short error, not a traceback."""
    from behave_doctor.cli.app import main

    code = main(["scan", ".", "--nonexistent-flag"])
    assert code == 2


# --- Scanner internals: matcher events, fallbacks, edge cases ---


def _scan_source(tmp_path: Path, source: str) -> list:
    steps = tmp_path / "steps"
    steps.mkdir(exist_ok=True)
    (steps / "s.py").write_text(source, encoding="utf-8")
    return scan_steps(steps, DoctorConfig())


def test_use_step_matcher_unknown_name_falls_back_to_parse(tmp_path: Path) -> None:
    """An unknown matcher name falls back to 'parse' with a warning."""
    defs = _scan_source(
        tmp_path,
        "from behave import given, use_step_matcher\n"
        'use_step_matcher("cucumber_expressions")\n'
        '@given("a parse-ish step")\ndef g(ctx): pass\n',
    )
    assert len(defs) == 1
    assert defs[0].matcher_type == "parse"
    assert defs[0].matcher.matches("a parse-ish step")


def test_use_step_matcher_name_kwarg(tmp_path: Path) -> None:
    defs = _scan_source(
        tmp_path,
        "from behave import given, use_step_matcher\n"
        'use_step_matcher(name="re")\n'
        '@given(r"abc (\\d+)")\ndef g(ctx): pass\n',
    )
    assert defs[0].matcher_type == "re"


def test_use_step_matcher_non_string_arg_ignored(tmp_path: Path) -> None:
    defs = _scan_source(
        tmp_path,
        "from behave import given, use_step_matcher\n"
        "use_step_matcher(MATCHER)\n"
        '@given("plain")\ndef g(ctx): pass\n',
    )
    assert defs[0].matcher_type == "parse"


def test_use_step_matcher_via_module_attribute(tmp_path: Path) -> None:
    defs = _scan_source(
        tmp_path,
        "import behave\n"
        'behave.use_step_matcher("re")\n'
        '@behave.given(r"abc (\\d+)")\ndef g(ctx): pass\n',
    )
    assert defs[0].matcher_type == "re"


def test_use_step_matcher_from_matchers_submodule(tmp_path: Path) -> None:
    defs = _scan_source(
        tmp_path,
        "from behave import given\n"
        "from behave.matchers import use_step_matcher\n"
        'use_step_matcher("re0")\n'
        '@given("^anchored$")\ndef g(ctx): pass\n',
    )
    assert defs[0].matcher_type == "re0"


def test_use_step_matcher_aliased(tmp_path: Path) -> None:
    defs = _scan_source(
        tmp_path,
        "from behave import given, use_step_matcher as usm\n"
        'usm("re")\n'
        '@given(r"abc (\\d+)")\ndef g(ctx): pass\n',
    )
    assert defs[0].matcher_type == "re"


def test_use_step_matcher_inside_function_ignored(tmp_path: Path) -> None:
    """A call inside a function does not run at import time — ignored."""
    defs = _scan_source(
        tmp_path,
        "from behave import given, use_step_matcher\n"
        "def setup():\n"
        '    use_step_matcher("re")\n'
        '@given("plain")\ndef g(ctx): pass\n',
    )
    assert defs[0].matcher_type == "parse"


def test_use_step_matcher_via_star_import(tmp_path: Path) -> None:
    defs = _scan_source(
        tmp_path,
        'from behave import *\nuse_step_matcher("re")\n@given(r"abc (\\d+)")\ndef g(ctx): pass\n',
    )
    assert defs[0].matcher_type == "re"


def test_async_step_function_detected(tmp_path: Path) -> None:
    defs = _scan_source(
        tmp_path,
        'from behave import given\n@given("async step")\nasync def g(ctx): pass\n',
    )
    assert len(defs) == 1
    assert defs[0].function_name == "g"


def test_bare_decorator_without_call_skipped(tmp_path: Path) -> None:
    """A bare ``@given`` reference (no call) carries no pattern."""
    defs = _scan_source(
        tmp_path,
        "from behave import given\ndef impl(ctx): pass\ng = given\n\n@given\ndef bare(ctx): pass\n",
    )
    assert defs == []


def test_decorator_without_string_pattern_skipped(tmp_path: Path) -> None:
    defs = _scan_source(
        tmp_path,
        "from behave import given\n@given(42)\ndef g(ctx): pass\n",
    )
    assert defs == []


def test_non_behave_attribute_decorator_skipped(tmp_path: Path) -> None:
    defs = _scan_source(
        tmp_path,
        'import other\n@other.given("a step")\ndef g(ctx): pass\n',
    )
    assert defs == []


def test_re_matcher_anonymous_groups_counted(tmp_path: Path) -> None:
    defs = _scan_source(
        tmp_path,
        "from behave import use_step_matcher, given\n"
        'use_step_matcher("re")\n'
        '@given(r"value (\\d+) or (\\w+)")\ndef g(ctx, a, b): pass\n',
    )
    assert defs[0].parameters == ["arg0", "arg1"]


def test_bad_regex_definition_skipped(tmp_path: Path) -> None:
    """An un-compilable regex is dropped, as Behave drops it at registration."""
    defs = _scan_source(
        tmp_path,
        "from behave import use_step_matcher, given\n"
        'use_step_matcher("re0")\n'
        '@given("(unclosed")\ndef g(ctx): pass\n',
    )
    assert defs == []


def test_uncompilable_parse_pattern_uses_approximate(tmp_path: Path) -> None:
    """Patterns that even ``parse`` cannot compile degrade to the
    approximate matcher instead of being dropped."""
    defs = _scan_source(
        tmp_path,
        'from behave import given\n@given("{a:b:c} broken")\ndef g(ctx): pass\n',
    )
    assert len(defs) == 1
    assert defs[0].approximate is True


def test_approximate_matcher_handles_literal_braces(tmp_path: Path) -> None:
    """``{{``/``}}`` escapes are handled by the approximate compiler."""
    from behave_doctor.scanner.step_scanner import _compile_parse_expression

    expr = _compile_parse_expression("literal {{brace}} and {value}")
    assert "\\{brace\\}" in expr
    assert "(?P<value>.+?)" in expr


def test_approximate_matcher_direct() -> None:
    """Direct unit coverage for the fallback matcher object."""
    from behave_doctor.scanner.step_scanner import _ApproximateMatcher

    matcher = _ApproximateMatcher(lambda: None, "a {thing} here")
    assert matcher.matches("a something here")
    assert not matcher.matches("a here")
    assert "(?P<thing>.+?)" in matcher.regex_pattern
    assert matcher.compile() is matcher


def test_missing_type_name_helper() -> None:
    from behave_doctor.scanner.step_scanner import _missing_type_name

    assert _missing_type_name(Exception()) is None
    assert _missing_type_name(Exception("Money")) == "Money"
    assert _missing_type_name(ValueError("format spec 'Money+' not recognised")) == "Money"
    assert _missing_type_name(ValueError("unrelated error")) is None


def test_bare_given_without_behave_import_detected(tmp_path: Path) -> None:
    """A bare ``@given`` with no behave import still counts (fallback)."""
    defs = _scan_source(
        tmp_path,
        '@given("a bare step")\ndef g(ctx): pass\n',
    )
    assert len(defs) == 1
    assert defs[0].keyword == "given"


def test_call_chained_decorator_skipped(tmp_path: Path) -> None:
    """``@factory()("x")`` — func is a Call, not Name/Attribute — is skipped."""
    defs = _scan_source(
        tmp_path,
        "from behave import given\n"
        "g = given\n"
        "\n"
        '@given("ok step")\ndef f(ctx): pass\n'
        "\n"
        "def deco_factory():\n"
        "    return given\n"
        "\n"
        '@deco_factory()("chained")\ndef h(ctx): pass\n',
    )
    patterns = {d.pattern for d in defs}
    assert "ok step" in patterns
    # The chained decorator's func is a Call — not resolvable statically.
    assert "chained" not in patterns


def test_module_docstring_and_bare_exprs_ignored(tmp_path: Path) -> None:
    """Module-level non-call expressions (docstrings etc.) are ignored."""
    defs = _scan_source(
        tmp_path,
        '"""Module docstring."""\n'
        "from behave import given, use_step_matcher\n"
        "use_step_matcher\n"  # bare name, not a call
        "use_step_matcher()\n"  # no args
        "x = 1\n"
        '@given("a step")\ndef g(ctx): pass\n',
    )
    assert len(defs) == 1
    assert defs[0].matcher_type == "parse"


def test_future_import_in_module_imports(tmp_path: Path) -> None:
    """``from __future__`` imports are not recorded as module imports."""
    from behave_doctor.graph.builder import _extract_module_imports

    py = tmp_path / "x.py"
    py.write_text("from __future__ import annotations\nimport os\n", encoding="utf-8")
    assert _extract_module_imports(py, "x") == {"os"}

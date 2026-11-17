"""Regression tests for behave 1.3.x compatibility fixes.

Covers: localised keywords, ``Rule:`` backgrounds and tags, ``And``/``But``/``*``
step-type inheritance, ``re``/``re0`` matcher semantics, and approximate
matching for runtime-registered custom types.
"""

from __future__ import annotations

from pathlib import Path

from behave_model import Metadata, Project

from behave_doctor.graph.builder import build_graph
from behave_doctor.model.config import DoctorConfig
from behave_doctor.model.dependency_graph import DependencyGraph
from behave_doctor.model.enums import Severity
from behave_doctor.model.step_definition import StepDefinition
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


# --- Regression: whitespace must match Behave runtime semantics ---


def test_step_with_extra_whitespace_is_undefined(tmp_path: Path) -> None:
    """A step whose text has collapsed/normalised whitespace must NOT match
    — behave's parser compares names verbatim, so runtime would report the
    step undefined."""
    _, _, graph = _project(
        tmp_path,
        "Feature: f\n  Scenario: s\n    Given I  have  things\n",
        'from behave import given\n@given("I have things")\ndef g(ctx): pass\n',
    )
    assert len(graph.step_matches) == 1
    assert graph.step_matches[0].step_definition is None


def test_step_with_tab_is_undefined(tmp_path: Path) -> None:
    """A literal tab in a step is significant — no whitespace normalisation."""
    _, _, graph = _project(
        tmp_path,
        "Feature: f\n  Scenario: s\n    Given I have\tthings\n",
        'from behave import given\n@given("I have things")\ndef g(ctx): pass\n',
    )
    assert graph.step_matches[0].step_definition is None


# --- Regression: keyword registry takes priority over the `step` registry ---


def test_keyword_definition_beats_step_definition(tmp_path: Path) -> None:
    """Behave's StepRegistry checks steps[keyword] before steps["step"], so a
    @given def wins over a @step def regardless of file scan order — even
    when the @step def lives in an alphabetically earlier file."""
    features = tmp_path / "features"
    steps_dir = features / "steps"
    steps_dir.mkdir(parents=True)
    (features / "f.feature").write_text(
        "Feature: f\n  Scenario: s\n    Given I login\n", encoding="utf-8"
    )
    (steps_dir / "a_steps.py").write_text(
        'from behave import step\n@step("I login")\ndef s(ctx): pass\n',
        encoding="utf-8",
    )
    (steps_dir / "z_steps.py").write_text(
        'from behave import given\n@given("I login")\ndef g(ctx): pass\n',
        encoding="utf-8",
    )
    project = scan_features(tmp_path, DoctorConfig())
    defs = scan_steps(steps_dir, DoctorConfig())
    graph = build_graph(project, defs)
    match = graph.step_matches[0]
    assert match.ambiguous is True
    assert match.step_definition is not None
    assert match.step_definition.keyword == "given"
    assert match.step_definition.function_name == "g"
    # step_usage must track the definition behave would actually run.
    assert match.step_definition.def_id in graph.step_usage


def test_step_match_records_all_candidates(tmp_path: Path) -> None:
    """``StepMatch.matches`` lists every matching def in registry order."""
    _, _, graph = _project(
        tmp_path,
        "Feature: f\n  Scenario: s\n    Given dup\n",
        "from behave import given\n"
        '@given("dup")\ndef a(ctx): pass\n'
        '@given("dup")\ndef b(ctx): pass\n',
    )
    match = graph.step_matches[0]
    assert match.ambiguous is True
    assert len(match.matches) == 2
    assert match.step_definition is match.matches[0]


# --- Regression: impact analysis expands Scenario Outline rows ---


def test_impact_expands_scenario_outline(tmp_path: Path) -> None:
    """A def with a typed pattern (``{n:d}``) matches the concrete example
    row, not the ``<n>`` template — impact must expand outline rows."""
    from behave_doctor.impact import impact_analysis

    features = tmp_path / "features"
    steps_dir = features / "steps"
    steps_dir.mkdir(parents=True)
    (features / "cart.feature").write_text(
        "Feature: cart\n"
        "  Scenario Outline: add items\n"
        "    Given I have <n> items\n"
        "\n"
        "    Examples:\n"
        "      | n |\n"
        "      | 5 |\n",
        encoding="utf-8",
    )
    steps_file = steps_dir / "cart_steps.py"
    steps_file.write_text(
        'from behave import given\n@given("I have {n:d} items")\ndef g(ctx, n): pass\n',
        encoding="utf-8",
    )
    result = impact_analysis(tmp_path, [str(steps_file)])
    assert [s.name for s in result.affected_scenarios] == ["add items"]


# --- Regression: ambiguous match via @step + @given reports both candidates ---


def test_impact_counts_all_ambiguous_candidates(tmp_path: Path) -> None:
    """Changing the shadowed @step def still flags the scenario — the match
    is ambiguous, so either definition may matter."""
    from behave_doctor.impact import impact_analysis

    features = tmp_path / "features"
    steps_dir = features / "steps"
    steps_dir.mkdir(parents=True)
    (features / "f.feature").write_text(
        "Feature: f\n  Scenario: s\n    Given I login\n", encoding="utf-8"
    )
    a_file = steps_dir / "a.py"
    a_file.write_text(
        'from behave import step\n@step("I login")\ndef s(ctx): pass\n',
        encoding="utf-8",
    )
    (steps_dir / "z.py").write_text(
        'from behave import given\n@given("I login")\ndef g(ctx): pass\n',
        encoding="utf-8",
    )
    result = impact_analysis(tmp_path, [str(a_file)])
    assert [s.name for s in result.affected_scenarios] == ["s"]


# --- Regression: tabless Examples blocks must not drop the whole feature ---


def test_examples_block_without_table_is_tolerated(tmp_path: Path) -> None:
    """Behave tolerates an ``Examples:`` block with no table (zero generated
    scenarios); the feature must still be scanned, not skipped entirely."""
    _, _, graph = _project(
        tmp_path,
        "Feature: f\n"
        "  Scenario Outline: s\n"
        "    Given x <a>\n"
        "\n"
        "    @tagged-empty\n"
        "    Examples:\n"
        "\n"
        "  Scenario: plain\n"
        "    Given y\n",
        'from behave import given\n@given("y")\ndef g(ctx): pass\n',
    )
    # The outline step is scanned but stays unmatched (no definition for
    # "x <a>"), and the plain scenario still matches — the feature was
    # not dropped.
    assert len(graph.step_matches) == 2
    unmatched = [m for m in graph.step_matches if m.step_definition is None]
    assert [m.step.name for m in unmatched] == ["x <a>"]


def test_examples_block_without_table_does_not_error(tmp_path: Path) -> None:
    """No scan error is recorded — behave would not error either."""
    features = tmp_path / "features"
    features.mkdir()
    (features / "f.feature").write_text(
        "Feature: f\n  Scenario Outline: s\n    Given x <a>\n\n    Examples:\n",
        encoding="utf-8",
    )
    errors: list[tuple[Path, str]] = []
    project = scan_features(tmp_path, DoctorConfig(), errors=errors)
    assert errors == []
    assert len(project.features) == 1


def test_use_default_step_matcher_bare_call_resets_to_parse(tmp_path: Path) -> None:
    """A bare ``use_default_step_matcher()`` resets the current matcher to
    the default (``parse``), like Behave does between module switches."""
    steps_dir = tmp_path / "steps"
    steps_dir.mkdir()
    (steps_dir / "s.py").write_text(
        "from behave import use_step_matcher, use_default_step_matcher, given\n"
        'use_step_matcher("re")\n'
        '@given(r"re (\\d+)")\ndef a(ctx, n): pass\n'
        "use_default_step_matcher()\n"
        '@given("parse {n:d}")\ndef b(ctx, n): pass\n',
        encoding="utf-8",
    )
    defs = scan_steps(steps_dir, DoctorConfig())
    types = {d.function_name: d.matcher_type for d in defs}
    assert types == {"a": "re", "b": "parse"}


def test_use_default_step_matcher_with_name_sets_new_default(tmp_path: Path) -> None:
    """``use_default_step_matcher("cfparse")`` changes both the current
    matcher and the default a later bare reset returns to."""
    steps_dir = tmp_path / "steps"
    steps_dir.mkdir()
    (steps_dir / "s.py").write_text(
        "from behave import use_step_matcher, use_default_step_matcher, given\n"
        'use_default_step_matcher("cfparse")\n'
        '@given("cf {n:d}")\ndef a(ctx, n): pass\n'
        'use_step_matcher("re")\n'
        '@given(r"re (\\d+)")\ndef b(ctx, n): pass\n'
        "use_default_step_matcher()\n"
        '@given("back to cf {n:d}")\ndef c(ctx, n): pass\n',
        encoding="utf-8",
    )
    defs = scan_steps(steps_dir, DoctorConfig())
    types = {d.function_name: d.matcher_type for d in defs}
    assert types == {"a": "cfparse", "b": "re", "c": "cfparse"}


def test_deprecated_step_matcher_alias_is_recognised(tmp_path: Path) -> None:
    """``step_matcher(name)`` — Behave's deprecated alias — also switches."""
    steps_dir = tmp_path / "steps"
    steps_dir.mkdir()
    (steps_dir / "s.py").write_text(
        "from behave import step_matcher, given\n"
        'step_matcher("re")\n'
        '@given(r"re (\\d+)")\ndef a(ctx, n): pass\n',
        encoding="utf-8",
    )
    defs = scan_steps(steps_dir, DoctorConfig())
    assert [d.matcher_type for d in defs] == ["re"]


def test_empty_feature_file_is_silently_skipped(tmp_path: Path) -> None:
    """Behave's parser returns ``None`` for feature files with no Feature
    statement (empty, comments only) and the runner skips them — they are
    not parse errors."""
    features = tmp_path / "features"
    features.mkdir()
    (features / "empty.feature").write_text("", encoding="utf-8")
    (features / "comments.feature").write_text("# only a comment\n", encoding="utf-8")
    (features / "ok.feature").write_text(
        "Feature: f\n  Scenario: s\n    Given x\n", encoding="utf-8"
    )
    errors: list[tuple[Path, str]] = []
    project = scan_features(tmp_path, DoctorConfig(), errors=errors)
    assert errors == []
    assert len(project.features) == 1


def test_same_module_name_files_merge_imports(tmp_path: Path) -> None:
    """``a.py`` and ``a/__init__.py`` both resolve to module ``a`` — their
    imports must be merged in the dependency graph, not overwritten."""
    steps_dir = tmp_path / "steps"
    (steps_dir / "pkg").mkdir(parents=True)
    (steps_dir / "pkg" / "__init__.py").write_text("import helper_one\n", encoding="utf-8")
    (steps_dir / "pkg.py").write_text("import helper_two\n", encoding="utf-8")
    # Neither file defines steps, so build the graph manually via defs.
    d1 = StepDefinition(
        keyword="given",
        pattern="x",
        matcher=None,
        matcher_type="parse",
        file=steps_dir / "pkg.py",
        line=1,
        function_name="a",
        module="pkg",
    )
    d2 = StepDefinition(
        keyword="given",
        pattern="y",
        matcher=None,
        matcher_type="parse",
        file=steps_dir / "pkg" / "__init__.py",
        line=1,
        function_name="b",
        module="pkg",
    )
    project = Project(features=[], global_tags=[], metadata=Metadata())
    graph = build_graph(project, [d1, d2])
    assert graph.module_imports["pkg"] == {"helper_one", "helper_two"}


def test_bom_feature_file_is_a_parse_error_like_runtime(tmp_path: Path) -> None:
    """``behave.parser.parse_file`` decodes feature files with ``utf-8``
    and never strips a BOM — a BOM'd feature fails to parse at runtime,
    so it must surface as a scan error (BD305), not a silently valid file."""
    features = tmp_path / "features"
    features.mkdir()
    (features / "bom.feature").write_bytes(b"\xef\xbb\xbfFeature: f\n  Scenario: s\n    Given x\n")
    errors: list[tuple[Path, str]] = []
    project = scan_features(tmp_path, DoctorConfig(), errors=errors)
    assert len(project.features) == 0
    assert len(errors) == 1
    assert errors[0][0].name == "bom.feature"


def test_step_file_with_coding_cookie_is_read_like_the_interpreter(
    tmp_path: Path,
) -> None:
    """A step module declaring ``# -*- coding: latin-1 -*-`` imports fine at
    runtime — the scanner must use the same decoding rules and not flag it
    as unparseable."""
    steps_dir = tmp_path / "features" / "steps"
    steps_dir.mkdir(parents=True)
    (steps_dir / "latin.py").write_bytes(
        b"# -*- coding: latin-1 -*-\nfrom behave import given\n"
        b'@given("caf\xe9")\ndef s(ctx): pass\n'
    )
    errors: list[tuple[Path, str]] = []
    defs = scan_steps(steps_dir, DoctorConfig(), errors=errors)
    assert errors == []
    assert [d.pattern for d in defs] == ["café"]


def test_step_file_with_unknown_coding_is_flagged(tmp_path: Path) -> None:
    """An unknown ``# -*- coding: -*-`` name is a SyntaxError at import —
    the scanner must report it instead of crashing."""
    steps_dir = tmp_path / "features" / "steps"
    steps_dir.mkdir(parents=True)
    (steps_dir / "bad.py").write_text("# -*- coding: no-such-codec -*-\nx = 1\n", encoding="utf-8")
    errors: list[tuple[Path, str]] = []
    defs = scan_steps(steps_dir, DoctorConfig(), errors=errors)
    assert defs == []
    assert len(errors) == 1


def test_matcher_switch_inside_main_guard_is_ignored(tmp_path: Path) -> None:
    """``use_step_matcher`` inside ``if __name__ == "__main__":`` never runs
    at import time — it must not affect the matcher of the module's defs."""
    steps_dir = tmp_path / "features" / "steps"
    steps_dir.mkdir(parents=True)
    (steps_dir / "s.py").write_text(
        "from behave import given, use_step_matcher\n"
        'use_step_matcher("re")\n'
        'if __name__ == "__main__":\n'
        '    use_step_matcher("parse")\n'
        "    from hypothesis import given as hg  # noqa: F401\n"
        '@given("x(.+)")\n'
        "def f(ctx): pass\n",
        encoding="utf-8",
    )
    defs = scan_steps(steps_dir, DoctorConfig())
    assert [(d.keyword, d.pattern, d.matcher_type) for d in defs] == [("given", "x(.+)", "re")]

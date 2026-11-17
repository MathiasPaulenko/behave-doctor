"""Edge case and regression tests for bug fixes and boundary conditions."""

from __future__ import annotations

from pathlib import Path

from behave_doctor.core import _filter_by_severity, build_report
from behave_doctor.graph.builder import _match_step, normalize_step_text
from behave_doctor.model.config import DoctorConfig
from behave_doctor.model.dependency_graph import DependencyGraph
from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Category, Severity
from behave_doctor.model.location import location_path
from behave_doctor.model.step_definition import StepDefinition
from behave_doctor.reporters.json_reporter import JsonReporter
from behave_doctor.reporters.sarif import SarifReporter
from behave_doctor.reporters.text import TextReporter
from behave_doctor.scanner import scan_features
from behave_doctor.scanner.step_scanner import scan_steps

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _parse_matcher(pattern: str):
    from behave.matchers import ParseMatcher

    def _stub() -> None:
        pass

    return ParseMatcher(_stub, pattern)


# --- Issue 8: .match() vs .fullmatch() — partial match false positives ---


def test_fullmatch_prevents_partial_match_for_exact_pattern() -> None:
    """An exact step pattern must not match a longer step text."""
    matcher = _parse_matcher("the user is logged in")
    assert matcher.matches("the user is logged in")
    assert not matcher.matches("the user is logged in and more")


def test_match_step_uses_fullmatch_not_match() -> None:
    """A step definition must not partially match a longer feature step."""

    class FakeStep:
        name = "the user is logged in and does more"
        step_type = "given"

    definition = StepDefinition(
        keyword="given",
        pattern="the user is logged in",
        matcher=_parse_matcher("the user is logged in"),
        matcher_type="parse",
        file=Path("steps.py"),
        line=1,
        function_name="step_impl",
        module="steps",
    )
    match = _match_step(FakeStep(), [definition])
    assert match.step_definition is None  # no partial match


# --- Issue 6: BD503 no longer duplicates BD302 ---


def test_bd503_does_not_fire_when_definitions_exist() -> None:
    """BD503 must not report when step definitions exist (BD302 handles that)."""
    from behave_doctor.rules.dependencies import MissingStepModule

    root = FIXTURES / "undefined_steps_project"
    from behave_doctor.scanner import scan_features

    project = scan_features(root, DoctorConfig())
    steps = scan_steps(root / "features" / "steps", DoctorConfig())
    from behave_doctor.graph.builder import build_graph

    graph = build_graph(project, steps)
    from behave_doctor.rules.base import RuleContext

    ctx = RuleContext(
        project=project,
        step_definitions=steps,
        dependency_graph=graph,
        config=DoctorConfig(),
    )
    diagnostics = MissingStepModule().check(ctx)
    assert diagnostics == []


# --- Issue 5: BD502 __future__ imports not flagged as unused ---


def test_bd502_skips_future_imports(tmp_path: Path) -> None:
    """`from __future__ import annotations` must not be flagged as unused."""
    from behave_doctor.rules.dependencies import UnusedImport

    steps = tmp_path / "features" / "steps"
    steps.mkdir(parents=True)
    (steps / "future.py").write_text(
        "from __future__ import annotations\nfrom behave import given\n\n\n"
        '@given("a step")\ndef step():\n    pass\n',
        encoding="utf-8",
    )
    from behave_doctor.scanner import scan_features

    project = scan_features(tmp_path, DoctorConfig())
    step_defs = scan_steps(steps, DoctorConfig())
    from behave_doctor.rules.base import RuleContext

    ctx = RuleContext(
        project=project,
        step_definitions=step_defs,
        dependency_graph=DependencyGraph(),
        config=DoctorConfig(),
    )
    diagnostics = UnusedImport().check(ctx)
    assert all(d.metadata["import"] != "annotations" for d in diagnostics)


# --- Issue 11 & 12: CLI error handling for invalid --severity and --format ---


def test_cli_invalid_severity_exits_with_code_2() -> None:
    from behave_doctor.cli.app import main

    code = main(["scan", str(FIXTURES / "sample_project"), "--severity", "critical"])
    assert code == 2


def test_cli_invalid_format_exits_with_code_2() -> None:
    from behave_doctor.cli.app import main

    code = main(["scan", str(FIXTURES / "sample_project"), "--format", "xml"])
    assert code == 2


# --- Issue 20: JSON reporter includes exit_code ---


def test_json_reporter_includes_exit_code() -> None:
    from datetime import datetime

    from behave_doctor.model.project_report import ProjectReport, ProjectStatistics

    report = ProjectReport(
        project_path=Path("test/"),
        diagnostics=[],
        statistics=ProjectStatistics(),
        scanned_at=datetime(2024, 1, 1),
        scan_duration_ms=10,
    )
    out = JsonReporter().format(report)
    import json

    data = json.loads(out)
    assert data["exit_code"] == 0


# --- Issue 1: location_path shared utility ---


def test_location_path_with_filename() -> None:
    class FakeLocation:
        filename = "features/test.feature"
        line = 5

    assert location_path(FakeLocation()) == Path("features/test.feature")


def test_location_path_with_empty_filename() -> None:
    class FakeLocation:
        filename = ""
        line = 1

    assert location_path(FakeLocation()) is None


def test_location_path_with_none_filename() -> None:
    class FakeLocation:
        filename = None
        line = 1

    assert location_path(FakeLocation()) is None


# --- Issue 2: SEVERITY_ORDER shared ---


def test_filter_by_severity_error_only() -> None:
    diags = [
        Diagnostic(
            rule_id="BD1",
            rule_name="test",
            severity=Severity.ERROR,
            category=Category.STRUCTURE,
            message="err",
        ),
        Diagnostic(
            rule_id="BD2",
            rule_name="test",
            severity=Severity.WARNING,
            category=Category.STRUCTURE,
            message="warn",
        ),
        Diagnostic(
            rule_id="BD3",
            rule_name="test",
            severity=Severity.INFO,
            category=Category.STRUCTURE,
            message="info",
        ),
    ]
    filtered = _filter_by_severity(diags, Severity.ERROR)
    assert len(filtered) == 1
    assert filtered[0].severity is Severity.ERROR


def test_filter_by_severity_warning_and_above() -> None:
    diags = [
        Diagnostic(
            rule_id="BD1",
            rule_name="test",
            severity=Severity.ERROR,
            category=Category.STRUCTURE,
            message="err",
        ),
        Diagnostic(
            rule_id="BD2",
            rule_name="test",
            severity=Severity.WARNING,
            category=Category.STRUCTURE,
            message="warn",
        ),
        Diagnostic(
            rule_id="BD3",
            rule_name="test",
            severity=Severity.INFO,
            category=Category.STRUCTURE,
            message="info",
        ),
    ]
    filtered = _filter_by_severity(diags, Severity.WARNING)
    assert len(filtered) == 2


# --- Empty project edge cases ---


def test_scan_empty_features_dir(tmp_path: Path) -> None:
    """Scanning a project with an empty features/ dir should not crash."""
    (tmp_path / "features").mkdir()
    (tmp_path / "features" / "steps").mkdir()
    report = build_report(tmp_path, DoctorConfig())
    assert report.statistics.features == 0
    assert report.statistics.scenarios == 0
    assert report.exit_code == 0


def test_scan_project_with_no_steps_dir(tmp_path: Path) -> None:
    """A project with features but no steps/ dir should still scan."""
    features = tmp_path / "features"
    features.mkdir()
    (features / "test.feature").write_text(
        "Feature: Test\n  Scenario: Test\n    Given something\n",
        encoding="utf-8",
    )
    report = build_report(tmp_path, DoctorConfig())
    assert report.statistics.features == 1
    # Undefined steps should be detected.
    rule_ids = {d.rule_id for d in report.diagnostics}
    assert "BD302" in rule_ids


# --- Unicode in feature files ---


def test_scan_project_with_unicode_in_feature(tmp_path: Path) -> None:
    """Feature files with Unicode characters should parse correctly."""
    features = tmp_path / "features"
    features.mkdir()
    (features / "steps").mkdir()
    (features / "unicode.feature").write_text(
        "Feature: Café résumé\n  Scenario: User types naïve text\n"
        '    Given the user enters "café"\n',
        encoding="utf-8",
    )
    report = build_report(tmp_path, DoctorConfig())
    assert report.statistics.features == 1
    assert report.statistics.scenarios == 1


# --- SARIF reporter edge cases ---


def test_sarif_reporter_with_file_outside_project(tmp_path: Path) -> None:
    """SARIF reporter must handle files outside project_path (relative_to fails)."""
    from datetime import datetime

    from behave_doctor.model.project_report import ProjectReport, ProjectStatistics

    diag = Diagnostic(
        rule_id="BD301",
        rule_name="unused",
        severity=Severity.WARNING,
        category=Category.COVERAGE,
        message="Unused",
        file=Path("/other/path/steps.py"),
        line=10,
    )
    report = ProjectReport(
        project_path=tmp_path,
        diagnostics=[diag],
        statistics=ProjectStatistics(),
        scanned_at=datetime(2024, 1, 1),
        scan_duration_ms=10,
    )
    out = SarifReporter().format(report)
    import json

    data = json.loads(out)
    result = data["runs"][0]["results"][0]
    # Should fall back to as_posix() when relative_to fails.
    assert result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] != ""


def test_sarif_reporter_with_no_file() -> None:
    """SARIF reporter must handle diagnostics with file=None."""
    from datetime import datetime

    from behave_doctor.model.project_report import ProjectReport, ProjectStatistics

    diag = Diagnostic(
        rule_id="BD101",
        rule_name="count",
        severity=Severity.INFO,
        category=Category.STRUCTURE,
        message="3 features",
    )
    report = ProjectReport(
        project_path=Path("test/"),
        diagnostics=[diag],
        statistics=ProjectStatistics(),
        scanned_at=datetime(2024, 1, 1),
        scan_duration_ms=10,
    )
    out = SarifReporter().format(report)
    import json

    data = json.loads(out)
    result = data["runs"][0]["results"][0]
    # Diagnostics without a file omit "locations" entirely (SARIF-valid).
    assert "locations" not in result


# --- Text reporter edge cases ---


def test_text_reporter_with_no_diagnostics() -> None:
    """Text reporter must handle a report with zero diagnostics."""
    from datetime import datetime

    from behave_doctor.model.project_report import ProjectReport, ProjectStatistics

    report = ProjectReport(
        project_path=Path("test/"),
        diagnostics=[],
        statistics=ProjectStatistics(),
        scanned_at=datetime(2024, 1, 1),
        scan_duration_ms=0,
    )
    out = TextReporter(use_color=False).format(report)
    assert "0 errors" in out
    assert "0 warnings" in out


def test_text_reporter_verbose_includes_suggestion() -> None:
    """Verbose mode must include suggestion and metadata."""
    from datetime import datetime

    from behave_doctor.model.project_report import ProjectReport, ProjectStatistics

    diag = Diagnostic(
        rule_id="BD301",
        rule_name="unused",
        severity=Severity.WARNING,
        category=Category.COVERAGE,
        message="Unused step",
        file=Path("steps.py"),
        line=10,
        suggestion="Remove it",
        metadata={"key": "value"},
    )
    report = ProjectReport(
        project_path=Path("test/"),
        diagnostics=[diag],
        statistics=ProjectStatistics(),
        scanned_at=datetime(2024, 1, 1),
        scan_duration_ms=10,
    )
    out = TextReporter(use_color=False, verbose=True).format(report)
    assert "Suggestion: Remove it" in out
    assert "Metadata:" in out


def test_text_reporter_location_with_only_file() -> None:
    """Location formatting when line is None but file is present."""
    from datetime import datetime

    from behave_doctor.model.project_report import ProjectReport, ProjectStatistics

    diag = Diagnostic(
        rule_id="BD101",
        rule_name="count",
        severity=Severity.INFO,
        category=Category.STRUCTURE,
        message="test",
        file=Path("features/test.feature"),
    )
    report = ProjectReport(
        project_path=Path("test/"),
        diagnostics=[diag],
        statistics=ProjectStatistics(),
        scanned_at=datetime(2024, 1, 1),
        scan_duration_ms=10,
    )
    out = TextReporter(use_color=False).format(report)
    assert "test.feature" in out


# --- normalize_step_text edge cases ---


def test_normalize_step_text_preserves_internal_whitespace() -> None:
    """Behave matches step names verbatim — internal whitespace is significant."""
    assert normalize_step_text("  multiple   spaces ") == "multiple   spaces"
    assert normalize_step_text("a\tb") == "a\tb"


def test_normalize_step_text_empty_string() -> None:
    assert normalize_step_text("") == ""


def test_normalize_step_text_no_keyword_stripping() -> None:
    """A step text that starts with a word like 'And' is kept verbatim."""
    assert normalize_step_text("And again") == "And again"
    assert normalize_step_text("the user is logged in") == "the user is logged in"


# --- DOT output edge cases ---


def test_to_dot_empty_graph() -> None:
    from behave_doctor.graph.dot import to_dot

    out = to_dot(DependencyGraph())
    assert "digraph behave_doctor" in out
    assert out.endswith("}")


def test_to_dot_with_self_loop() -> None:
    from behave_doctor.graph.dot import to_dot

    graph = DependencyGraph()
    graph.module_imports = {"a": {"a"}}
    out = to_dot(graph)
    assert '"a" -> "a"' in out


# --- BUG A: scan_project(None) should raise TypeError ---


def test_scan_project_none_raises_type_error() -> None:
    """scan_project(None) must raise TypeError, not crash with obscure error."""
    import pytest

    from behave_doctor import scan_project

    with pytest.raises(TypeError, match="path"):
        scan_project(None)


def test_scan_project_nonexistent_raises_filenotfound() -> None:
    """scan_project with a non-existent path must raise FileNotFoundError."""
    import pytest

    from behave_doctor import scan_project

    with pytest.raises(FileNotFoundError):
        scan_project("/nonexistent/path/that/does/not/exist")


# --- BUG B & C: from_pyproject(None) and from_pyproject(directory) ---


def test_from_pyproject_none_raises_type_error() -> None:
    """from_pyproject(None) must raise TypeError."""
    import pytest

    with pytest.raises(TypeError, match="Path"):
        DoctorConfig.from_pyproject(None)


def test_from_pyproject_directory_raises_isadir() -> None:
    """from_pyproject with a directory must raise IsADirectoryError."""
    import pytest

    with pytest.raises(IsADirectoryError):
        DoctorConfig.from_pyproject(Path("."))


# --- BUG D & G: config exclude as non-dict ---


def test_config_exclude_as_string_does_not_crash(tmp_path: Path) -> None:
    """exclude = 'not a dict' in TOML should not crash — should use empty lists."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.behave-doctor]\nexclude = "not a dict"\n',
        encoding="utf-8",
    )
    cfg = DoctorConfig.from_pyproject(pyproject)
    assert cfg.exclude_paths == []
    assert cfg.exclude_tags == []


def test_config_exclude_paths_as_non_list(tmp_path: Path) -> None:
    """A bare string under ``exclude.paths`` coerces to a one-element list,
    matching how a top-level ``exclude_paths = "x"`` is treated."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.behave-doctor]\nexclude = {paths = "not a list"}\n',
        encoding="utf-8",
    )
    cfg = DoctorConfig.from_pyproject(pyproject)
    assert cfg.exclude_paths == ["not a list"]


def test_config_exclude_tags_as_non_list(tmp_path: Path) -> None:
    """exclude.tags as a non-list should not crash — should use empty list."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.behave-doctor]\nexclude = {tags = 123}\n",
        encoding="utf-8",
    )
    cfg = DoctorConfig.from_pyproject(pyproject)
    assert cfg.exclude_tags == []


# --- BUG E: BOM handling in feature and Python files ---


def test_scan_features_with_bom(tmp_path: Path) -> None:
    """Feature files with a UTF-8 BOM are a parse error — Behave decodes
    them with plain ``utf-8``, so the BOM breaks ``Feature:`` at runtime."""
    from behave_doctor.scanner.project_scanner import scan_features

    features = tmp_path / "features"
    features.mkdir()
    (features / "bom.feature").write_text(
        "\ufeffFeature: BOM Test\n  Scenario: Test\n    Given something\n",
        encoding="utf-8",
    )
    errors: list[tuple[Path, str]] = []
    project = scan_features(tmp_path, DoctorConfig(), errors=errors)
    assert len(project.features) == 0
    assert len(errors) == 1


def test_scan_steps_with_bom(tmp_path: Path) -> None:
    """Python step files with UTF-8 BOM should be parsed, not skipped."""
    steps = tmp_path / "steps"
    steps.mkdir()
    (steps / "bom.py").write_text(
        '\ufefffrom behave import given\n\n\n@given("a step")\ndef step():\n    pass\n',
        encoding="utf-8",
    )
    defs = scan_steps(steps, DoctorConfig())
    assert len(defs) == 1
    assert defs[0].pattern == "a step"


def test_extract_module_imports_with_bom(tmp_path: Path) -> None:
    """_extract_module_imports should handle BOM-prefixed files."""
    from behave_doctor.graph.builder import _extract_module_imports

    py_file = tmp_path / "bom.py"
    py_file.write_text(
        "\ufeffimport os\nimport sys\n",
        encoding="utf-8",
    )
    imports = _extract_module_imports(py_file)
    assert "os" in imports
    assert "sys" in imports


def test_bd502_with_bom_file(tmp_path: Path) -> None:
    """BD502 UnusedImport should handle BOM-prefixed Python files."""
    from behave_doctor.rules.base import RuleContext
    from behave_doctor.rules.dependencies import UnusedImport

    steps = tmp_path / "steps"
    steps.mkdir()
    (steps / "bom.py").write_text(
        '\ufefffrom behave import given\n\n\n@given("test")\ndef step():\n    pass\n',
        encoding="utf-8",
    )
    step_defs = scan_steps(steps, DoctorConfig())
    ctx = RuleContext(
        project=_make_empty_project(),
        step_definitions=step_defs,
        dependency_graph=DependencyGraph(),
        config=DoctorConfig(),
    )
    diagnostics = UnusedImport().check(ctx)
    # `given` is used as a decorator, so it should not be flagged.
    assert all(d.metadata["import"] != "given" for d in diagnostics)


def test_bd403_with_bom_feature_file(tmp_path: Path) -> None:
    """BD403 FeatureTooLarge should handle BOM-prefixed feature files."""
    from behave_doctor.rules.base import RuleContext
    from behave_doctor.rules.complexity import FeatureTooLarge

    features = tmp_path / "features"
    features.mkdir()
    (features / "big.feature").write_text(
        "\ufeffFeature: Big\n" + "  Scenario: S\n    Given step\n" * 200,
        encoding="utf-8",
    )
    from behave_doctor.scanner.project_scanner import scan_features

    project = scan_features(tmp_path, DoctorConfig())
    ctx = RuleContext(
        project=project,
        step_definitions=[],
        dependency_graph=DependencyGraph(),
        config=DoctorConfig(),
    )
    diagnostics = FeatureTooLarge().check(ctx)
    # The BOM'd feature never reaches the model (parse error), so BD403
    # has nothing to report — it must not crash either way.
    assert diagnostics == []


# --- BUG F: to_dot escaping ---


def test_to_dot_escapes_quotes_in_module_names() -> None:
    """to_dot must escape double quotes in module names."""
    from behave_doctor.graph.dot import to_dot

    graph = DependencyGraph()
    graph.module_imports = {'mod"with"quotes': set()}
    out = to_dot(graph)
    assert '\\"' in out
    assert '"mod"with"quotes"' not in out  # unescaped quotes must not appear


def test_to_dot_escapes_backslashes_in_module_names() -> None:
    """to_dot must escape backslashes in module names."""
    from behave_doctor.graph.dot import to_dot

    graph = DependencyGraph()
    graph.module_imports = {"mod\\back": set()}
    out = to_dot(graph)
    assert "\\\\" in out  # DOT-escaped backslash


# --- Helper ---


def _make_empty_project() -> object:
    """Create a minimal behave-model Project with no features."""
    from behave_model import Metadata, Project

    return Project(features=[], global_tags=[], metadata=Metadata(source_path=""))


# --- BD502 string annotation with bracketed generics ---


def test_bd502_string_annotation_with_generics(tmp_path: Path) -> None:
    """BD502 must not flag imports used in string annotations like 'List[int]'."""
    from behave_doctor.rules.base import RuleContext
    from behave_doctor.rules.dependencies import UnusedImport

    steps = tmp_path / "steps"
    steps.mkdir()
    (steps / "typed.py").write_text(
        "from __future__ import annotations\n"
        "from typing import List, Optional\n"
        "from behave import given\n\n\n"
        '@given("a step")\n'
        "def step(items: 'List[int]', name: 'Optional[str]') -> None:\n"
        "    pass\n",
        encoding="utf-8",
    )
    step_defs = scan_steps(steps, DoctorConfig())
    ctx = RuleContext(
        project=_make_empty_project(),
        step_definitions=step_defs,
        dependency_graph=DependencyGraph(),
        config=DoctorConfig(),
    )
    diagnostics = UnusedImport().check(ctx)
    flagged = {d.metadata["import"] for d in diagnostics}
    assert "List" not in flagged
    assert "Optional" not in flagged


# --- Invalid config int values should not crash rules ---


def test_bd401_invalid_max_steps_does_not_crash() -> None:
    """BD401 with non-integer max_steps should use default, not crash."""
    from behave_doctor.rules.base import RuleContext
    from behave_doctor.rules.complexity import ScenarioTooManySteps

    config = DoctorConfig(rules={"BD401": {"max_steps": "not a number"}})
    ctx = RuleContext(
        project=_make_empty_project(),
        step_definitions=[],
        dependency_graph=DependencyGraph(),
        config=config,
    )
    # Should not raise — should fall back to default.
    diagnostics = ScenarioTooManySteps().check(ctx)
    assert diagnostics == []


def test_bd403_invalid_max_lines_does_not_crash() -> None:
    """BD403 with non-integer max_lines should use default, not crash."""
    from behave_doctor.rules.base import RuleContext
    from behave_doctor.rules.complexity import FeatureTooLarge

    config = DoctorConfig(rules={"BD403": {"max_lines": "invalid"}})
    ctx = RuleContext(
        project=_make_empty_project(),
        step_definitions=[],
        dependency_graph=DependencyGraph(),
        config=config,
    )
    diagnostics = FeatureTooLarge().check(ctx)
    assert diagnostics == []


def test_bd203_invalid_max_scenarios_does_not_crash() -> None:
    """BD203 with non-integer max_scenarios should use default, not crash."""
    from behave_doctor.rules.base import RuleContext
    from behave_doctor.rules.quality import FeatureTooManyScenarios

    config = DoctorConfig(rules={"BD203": {"max_scenarios": "bad"}})
    ctx = RuleContext(
        project=_make_empty_project(),
        step_definitions=[],
        dependency_graph=DependencyGraph(),
        config=config,
    )
    diagnostics = FeatureTooManyScenarios().check(ctx)
    assert diagnostics == []


# --- _extract_module_imports handles OSError ---


def test_extract_module_imports_handles_oserror(tmp_path: Path) -> None:
    """_extract_module_imports should return empty set on OSError, not crash."""
    from behave_doctor.graph.builder import _extract_module_imports

    # Use a path that doesn't exist
    missing = tmp_path / "nonexistent.py"
    imports = _extract_module_imports(missing)
    assert imports == set()


# --- FeatureTooLarge handles file read error ---


def test_bd403_handles_unreadable_file(tmp_path: Path) -> None:
    """BD403 should skip files that can't be read, not crash."""
    from behave_doctor.rules.base import RuleContext
    from behave_doctor.rules.complexity import FeatureTooLarge
    from behave_doctor.scanner.project_scanner import scan_features

    features = tmp_path / "features"
    features.mkdir()
    feature_file = features / "test.feature"
    feature_file.write_text("Feature: Test\n  Scenario: T\n    Given step\n", encoding="utf-8")

    project = scan_features(tmp_path, DoctorConfig())
    ctx = RuleContext(
        project=project,
        step_definitions=[],
        dependency_graph=DependencyGraph(),
        config=DoctorConfig(),
    )
    # Delete the file after scanning to simulate a race condition
    feature_file.unlink()
    # Should not crash
    diagnostics = FeatureTooLarge().check(ctx)
    assert diagnostics == []


# --- normalize_step_text with tabs (not just spaces) ---


def test_normalize_step_text_with_tabs() -> None:
    """Tabs in step text are kept verbatim — behave matches names verbatim."""
    assert normalize_step_text("the user\tdoes something") == "the user\tdoes something"


def test_normalize_step_text_mixed_tabs_and_spaces() -> None:
    """Mixed tabs and spaces are preserved; only outer whitespace is stripped."""
    assert normalize_step_text("the  \t  user") == "the  \t  user"
    assert normalize_step_text("  outer  ") == "outer"


# --- JSON reporter with non-serializable metadata ---


def test_json_reporter_with_path_in_metadata() -> None:
    """JSON reporter should handle Path objects in metadata without crashing."""
    from datetime import datetime

    from behave_doctor.model.project_report import ProjectReport, ProjectStatistics

    diag = Diagnostic(
        rule_id="BD999",
        rule_name="test",
        severity=Severity.ERROR,
        category=Category.STRUCTURE,
        message="test",
        metadata={"path": Path("/test/path")},
    )
    report = ProjectReport(
        project_path=Path("test/"),
        diagnostics=[diag],
        statistics=ProjectStatistics(),
        scanned_at=datetime(2024, 1, 1),
        scan_duration_ms=0,
    )
    out = JsonReporter().format(report)
    import json

    data = json.loads(out)
    assert data["diagnostics"][0]["metadata"]["path"] == "/test/path"


def test_json_reporter_with_set_in_metadata() -> None:
    """JSON reporter should handle set objects in metadata without crashing."""
    from datetime import datetime

    from behave_doctor.model.project_report import ProjectReport, ProjectStatistics

    diag = Diagnostic(
        rule_id="BD999",
        rule_name="test",
        severity=Severity.ERROR,
        category=Category.STRUCTURE,
        message="test",
        metadata={"items": {3, 1, 2}},
    )
    report = ProjectReport(
        project_path=Path("test/"),
        diagnostics=[diag],
        statistics=ProjectStatistics(),
        scanned_at=datetime(2024, 1, 1),
        scan_duration_ms=0,
    )
    out = JsonReporter().format(report)
    import json

    data = json.loads(out)
    # Sets should be serialized as sorted lists.
    assert data["diagnostics"][0]["metadata"]["items"] == [1, 2, 3]


# --- BD502 type comment support ---


def test_bd502_type_comment_not_flagged(tmp_path: Path) -> None:
    """BD502 must not flag imports used in `# type: ...` comments."""
    from behave_doctor.rules.base import RuleContext
    from behave_doctor.rules.dependencies import UnusedImport

    steps = tmp_path / "steps"
    steps.mkdir()
    (steps / "typecomment.py").write_text(
        "from behave import given\n"
        "from typing import List\n\n"
        '@given("a step")\n'
        "def step(items):  # type: List[int]\n"
        "    pass\n",
        encoding="utf-8",
    )
    step_defs = scan_steps(steps, DoctorConfig())
    ctx = RuleContext(
        project=_make_empty_project(),
        step_definitions=step_defs,
        dependency_graph=DependencyGraph(),
        config=DoctorConfig(),
    )
    diagnostics = UnusedImport().check(ctx)
    flagged = {d.metadata["import"] for d in diagnostics}
    assert "List" not in flagged


# --- scan_steps handles OSError (permission denied, etc.) ---


def test_scan_steps_handles_oserror(tmp_path: Path) -> None:
    """scan_steps should skip files that can't be read, not crash."""
    steps = tmp_path / "steps"
    steps.mkdir()
    py_file = steps / "test.py"
    py_file.write_text(
        'from behave import given\n@given("a step")\ndef step():\n    pass\n',
        encoding="utf-8",
    )
    # Create a directory with .py extension — rglob finds it, read_text raises OSError
    weird = steps / "weird.py"
    weird.mkdir()
    defs = scan_steps(steps, DoctorConfig())
    # Should still find the step from test.py, skipping weird.py
    assert len(defs) == 1
    assert defs[0].pattern == "a step"


def test_scan_steps_handles_non_utf8(tmp_path: Path) -> None:
    """scan_steps should skip files that are not valid UTF-8, not crash."""
    steps = tmp_path / "steps"
    steps.mkdir()
    (steps / "test.py").write_text(
        'from behave import given\n@given("a step")\ndef step():\n    pass\n',
        encoding="utf-8",
    )
    (steps / "binary.py").write_bytes(b"\xff\xfe")
    defs = scan_steps(steps, DoctorConfig())
    assert len(defs) == 1
    assert defs[0].pattern == "a step"


def test_scan_features_handles_unreadable(tmp_path: Path) -> None:
    """scan_features should skip unreadable or non-UTF-8 .feature entries, not crash."""
    features = tmp_path / "features"
    features.mkdir()
    (features / "keep.feature").write_text("Feature: Keep\n", encoding="utf-8")
    # Directory with .feature extension triggers an OSError on read_text.
    (features / "skip.feature").mkdir()
    (features / "binary.feature").write_bytes(b"\xff\xfe")
    project = scan_features(tmp_path, DoctorConfig())
    assert len(project.features) == 1
    assert project.features[0].name == "Keep"


# --- location=None resilience ---


def test_rules_handle_missing_location() -> None:
    """Rules must not crash when a scenario or feature has no location."""
    from behave_model import Feature, Scenario, Step

    from behave_doctor.rules.base import RuleContext
    from behave_doctor.rules.quality import ScenarioNoTags

    scenario = Scenario(
        name="NoLocation",
        steps=[Step(name="Given something")],
        location=None,
        tags=[],
    )
    feature = Feature(name="NoLocationFeature", scenarios=[scenario], location=None)
    project = _make_empty_project()
    project.features = [feature]

    ctx = RuleContext(
        project=project,
        step_definitions=[],
        dependency_graph=DependencyGraph(),
        config=DoctorConfig(),
    )
    diags = ScenarioNoTags().check(ctx)
    assert len(diags) == 1
    assert diags[0].file is None
    assert diags[0].line is None


# --- step scanner module alias support ---


def test_scan_steps_import_behave_alias(tmp_path: Path) -> None:
    """Step scanner must recognise @b.given when behave is imported as b."""
    steps = tmp_path / "steps"
    steps.mkdir()
    (steps / "alias.py").write_text(
        'import behave as b\n\n@b.given("aliased behave import")\ndef step_impl():\n    pass\n',
        encoding="utf-8",
    )
    defs = scan_steps(steps, DoctorConfig())
    assert len(defs) == 1
    assert defs[0].keyword == "given"
    assert defs[0].pattern == "aliased behave import"


def test_scan_steps_wildcard_import(tmp_path: Path) -> None:
    """Step scanner must recognise @given after `from behave import *`."""
    steps = tmp_path / "steps"
    steps.mkdir()
    (steps / "wildcard.py").write_text(
        'from behave import *\n\n@given("wildcard behave import")\ndef step_impl():\n    pass\n',
        encoding="utf-8",
    )
    defs = scan_steps(steps, DoctorConfig())
    assert len(defs) == 1
    assert defs[0].keyword == "given"
    assert defs[0].pattern == "wildcard behave import"


# --- exclude_paths support ---


def test_scan_features_respects_exclude_paths(tmp_path: Path) -> None:
    """scan_features must skip .feature files matching exclude_paths."""
    features = tmp_path / "features"
    features.mkdir()
    (features / "keep.feature").write_text("Feature: Keep\n", encoding="utf-8")
    (features / "skip.feature").write_text("Feature: Skip\n", encoding="utf-8")
    config = DoctorConfig(exclude_paths=["**/skip.feature"])
    project = scan_features(tmp_path, config)
    names = {f.name for f in project.features}
    assert "Keep" in names
    assert "Skip" not in names


def test_scan_steps_respects_exclude_paths(tmp_path: Path) -> None:
    """scan_steps must skip .py files matching exclude_paths."""
    steps = tmp_path / "steps"
    steps.mkdir()
    (steps / "keep.py").write_text(
        'from behave import given\n@given("keep")\ndef step():\n    pass\n',
        encoding="utf-8",
    )
    (steps / "skip.py").write_text(
        'from behave import given\n@given("skip")\ndef step():\n    pass\n',
        encoding="utf-8",
    )
    config = DoctorConfig(exclude_paths=["**/skip.py"])
    defs = scan_steps(steps, config)
    patterns = {d.pattern for d in defs}
    assert "keep" in patterns
    assert "skip" not in patterns


def test_doctor_config_is_excluded(tmp_path: Path) -> None:
    """DoctorConfig.is_excluded matches file and directory glob patterns."""
    config = DoctorConfig(exclude_paths=["**/skip.feature", "excluded/**"])
    assert config.is_excluded(tmp_path / "skip.feature") is True
    assert config.is_excluded(tmp_path / "a" / "b" / "skip.feature") is True
    assert config.is_excluded(tmp_path / "excluded" / "x.feature") is True
    assert config.is_excluded(tmp_path / "keep.feature") is False


# --- OrphanScenario with feature-level tags ---


def test_orphan_scenario_considers_feature_tags(tmp_path: Path) -> None:
    """A scenario should not be flagged orphan when it inherits a shared feature tag."""
    from behave_model import Feature, Scenario, Step

    from behave_doctor.rules.base import RuleContext
    from behave_doctor.rules.coverage import OrphanScenario

    s1 = Scenario(
        name="One",
        steps=[Step(name="Given x")],
        tags=[],
    )
    s2 = Scenario(
        name="Two",
        steps=[Step(name="Given y")],
        tags=["@unique"],
    )
    feature = Feature(
        name="WithFeatureTag",
        tags=["@shared"],
        scenarios=[s1, s2],
    )
    project = _make_empty_project()
    project.features = [feature]

    ctx = RuleContext(
        project=project,
        step_definitions=[],
        dependency_graph=DependencyGraph(),
        config=DoctorConfig(),
    )
    diags = OrphanScenario().check(ctx)
    assert len(diags) == 0, diags


# --- Scenario Outline Examples tags ---


def test_scenario_outline_example_tags_counted(tmp_path: Path) -> None:
    """Tags on Scenario Outline Examples blocks must appear in BD104 and statistics."""
    features = tmp_path / "features"
    features.mkdir()
    (features / "steps").mkdir()
    (features / "steps" / "steps.py").write_text(
        'from behave import given\n@given("a step")\ndef step(): pass\n',
        encoding="utf-8",
    )
    (features / "outline.feature").write_text(
        "Feature: outline\n\n"
        "  Scenario Outline: example\n"
        "    Given a step\n\n"
        "    @example_tag\n"
        "    Examples:\n"
        "      | col |\n"
        "      | a   |\n",
        encoding="utf-8",
    )
    report = build_report(tmp_path, DoctorConfig())
    assert report.statistics.tags == 1
    assert report.statistics.total_tag_usages == 1
    tag_diag = next(d for d in report.diagnostics if d.rule_id == "BD104")
    assert "1 unique tags" in tag_diag.message


def test_scenario_no_tags_honors_example_tags(tmp_path: Path) -> None:
    """Scenario Outlines with Examples tags must not be flagged as tagless."""
    features = tmp_path / "features"
    features.mkdir()
    (features / "steps").mkdir()
    (features / "steps" / "steps.py").write_text(
        'from behave import given\n@given("a step")\ndef step(): pass\n',
        encoding="utf-8",
    )
    (features / "outline.feature").write_text(
        "Feature: outline\n\n"
        "  Scenario Outline: example\n"
        "    Given a step\n\n"
        "    @example_tag\n"
        "    Examples:\n"
        "      | col |\n"
        "      | a   |\n",
        encoding="utf-8",
    )
    report = build_report(tmp_path, DoctorConfig())
    assert not any(d.rule_id == "BD202" for d in report.diagnostics)


def test_outline_example_rows_expand_counts(tmp_path: Path) -> None:
    """Scenario and step counts must expand Scenario Outline example rows."""
    features = tmp_path / "features"
    features.mkdir()
    (features / "steps").mkdir()
    (features / "steps" / "steps.py").write_text(
        'from behave import given\n@given("a <col> step")\ndef step(col): pass\n',
        encoding="utf-8",
    )
    (features / "outline.feature").write_text(
        "Feature: outline\n\n"
        "  Scenario Outline: example\n"
        "    Given a <col> step\n"
        "    When another step\n\n"
        "    Examples:\n"
        "      | col |\n"
        "      | a   |\n"
        "      | b   |\n"
        "      | c   |\n",
        encoding="utf-8",
    )
    report = build_report(tmp_path, DoctorConfig())
    assert report.statistics.scenarios == 3
    assert report.statistics.steps == 6
    assert report.statistics.average_steps_per_scenario == 2.0
    scenario_diag = next(d for d in report.diagnostics if d.rule_id == "BD102")
    assert "3 scenarios found" in scenario_diag.message
    step_diag = next(d for d in report.diagnostics if d.rule_id == "BD103")
    assert "6 steps found" in step_diag.message


# --- Regression: is_excluded must not match ancestors above the scan root ---


def test_is_excluded_does_not_match_above_within(tmp_path: Path) -> None:
    """An exclude pattern matching a *parent* of the project root must not
    exclude the entire project (e.g. 'build' when the project lives under
    a 'build' directory)."""
    project = tmp_path / "build" / "project"
    feature = project / "features" / "x.feature"
    feature.parent.mkdir(parents=True)
    feature.write_text("Feature: x\n", encoding="utf-8")
    config = DoctorConfig(exclude_paths=["build"])
    # Without `within`, the "build" ancestor matches and excludes everything.
    assert config.is_excluded(feature) is True
    # With the scan root bound, only in-project ancestors are considered.
    assert config.is_excluded(feature, within=project / "features") is False


def test_is_excluded_within_still_matches_dir_patterns(tmp_path: Path) -> None:
    """Directory patterns must still work when `within` bounds the walk."""
    root = tmp_path / "features"
    feature = root / "excluded" / "x.feature"
    config = DoctorConfig(exclude_paths=["excluded"])
    assert config.is_excluded(feature, within=root) is True


# --- Regression: unparseable step files surface as diagnostics (BD305) ---


def test_unparseable_step_file_surfaces_bd305(tmp_path: Path) -> None:
    """A .py file that fails to parse must produce a BD305 diagnostic —
    Behave would abort importing it, so a silent skip hides a broken suite."""
    features = tmp_path / "features"
    steps = features / "steps"
    steps.mkdir(parents=True)
    (features / "ok.feature").write_text(
        "Feature: ok\n  Scenario: s\n    Given ok\n", encoding="utf-8"
    )
    (steps / "broken.py").write_text("def broken(:\n", encoding="utf-8")
    report = build_report(tmp_path, DoctorConfig())
    bd305 = [d for d in report.diagnostics if d.rule_id == "BD305"]
    assert len(bd305) == 1
    assert bd305[0].file == steps / "broken.py"
    assert "step file" in bd305[0].message


def test_scan_steps_collects_errors(tmp_path: Path) -> None:
    """scan_steps(errors=...) must receive (path, message) for failed files."""
    steps = tmp_path / "steps"
    steps.mkdir()
    (steps / "bad.py").write_text("def bad(:\n", encoding="utf-8")
    errors: list[tuple[Path, str]] = []
    defs = scan_steps(steps, DoctorConfig(), errors=errors)
    assert defs == []
    assert len(errors) == 1
    assert errors[0][0] == steps / "bad.py"


# --- Regression: module dotted path for __init__.py ---


def test_module_dotted_path_strips_init() -> None:
    """pkg/__init__.py must map to module 'pkg', matching `import pkg`."""
    from behave_doctor.scanner.step_scanner import _module_dotted_path

    steps_path = Path("steps")
    assert _module_dotted_path(Path("steps/pkg/__init__.py"), steps_path) == "pkg"
    assert _module_dotted_path(Path("steps/pkg/mod.py"), steps_path) == "pkg.mod"
    assert _module_dotted_path(Path("steps/plain.py"), steps_path) == "plain"


# --- Regression: imports inside functions must not leak to module scope ---


def test_import_inside_function_does_not_create_module_alias(tmp_path: Path) -> None:
    """`import behave` inside a function does not bind `behave` at module
    level, so @behave.given decorators must not resolve."""
    steps = tmp_path / "steps"
    steps.mkdir()
    (steps / "scoped.py").write_text(
        "def setup():\n"
        "    import behave\n"
        "    return behave\n"
        "\n"
        '@behave.given("a step")\n'
        "def impl(ctx): pass\n",
        encoding="utf-8",
    )
    defs = scan_steps(steps, DoctorConfig())
    assert defs == []


def test_module_level_def_shadows_bare_decorator(tmp_path: Path) -> None:
    """A module-level `def given(...)` shadows the bare-name fallback —
    it is a local function, not a step decorator."""
    steps = tmp_path / "steps"
    steps.mkdir()
    (steps / "shadow.py").write_text(
        'def given(text):\n    return lambda f: f\n\n@given("not a step")\ndef impl(ctx): pass\n',
        encoding="utf-8",
    )
    defs = scan_steps(steps, DoctorConfig())
    assert defs == []


def test_module_level_assignment_shadows_bare_decorator(tmp_path: Path) -> None:
    """A module-level assignment to `given` shadows the bare-name fallback."""
    steps = tmp_path / "steps"
    steps.mkdir()
    (steps / "shadow2.py").write_text(
        'given = lambda text: (lambda f: f)\n\n@given("not a step")\ndef impl(ctx): pass\n',
        encoding="utf-8",
    )
    defs = scan_steps(steps, DoctorConfig())
    assert defs == []


# --- Regression: format_report validates fmt like format_impact does ---


def test_format_report_rejects_empty_format() -> None:
    """format_report(report, '') must raise ValueError, not AttributeError."""
    from datetime import datetime

    from behave_doctor.cli.formatters import format_report
    from behave_doctor.model.project_report import ProjectReport, ProjectStatistics

    report = ProjectReport(
        project_path=Path("."),
        diagnostics=[],
        statistics=ProjectStatistics(),
        scanned_at=datetime(2024, 1, 1),
        scan_duration_ms=0,
    )
    import pytest

    with pytest.raises(ValueError, match="non-empty"):
        format_report(report, "")
    with pytest.raises(ValueError, match="non-empty"):
        format_report(report, "   ")


# --- Regression: SARIF startLine must be >= 1 ---


def test_sarif_reporter_line_zero_omits_region() -> None:
    """SARIF startLine must be >= 1; a line of 0 must omit the region."""
    from datetime import datetime

    from behave_doctor.model.project_report import ProjectReport, ProjectStatistics

    diag = Diagnostic(
        rule_id="BD101",
        rule_name="count",
        severity=Severity.INFO,
        category=Category.STRUCTURE,
        message="test",
        file=Path("features/x.feature"),
        line=0,
    )
    report = ProjectReport(
        project_path=Path("."),
        diagnostics=[diag],
        statistics=ProjectStatistics(),
        scanned_at=datetime(2024, 1, 1),
        scan_duration_ms=0,
    )
    out = SarifReporter().format(report)
    import json

    data = json.loads(out)
    location = data["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
    assert "region" not in location


# --- Regression: approximate matcher keeps anonymous placeholder params ---


def test_approximate_matcher_parameters_include_anonymous(tmp_path: Path) -> None:
    """Anonymous {} placeholders become argN parameters for approximate matchers."""
    steps = tmp_path / "steps"
    steps.mkdir()
    (steps / "approx.py").write_text(
        'from behave import given\n@given("{x:Bogus} and {}")\ndef g(ctx, x, y): pass\n',
        encoding="utf-8",
    )
    defs = scan_steps(steps, DoctorConfig())
    assert len(defs) == 1
    assert defs[0].approximate is True
    assert defs[0].parameters == ["x", "arg0"]


# --- Regression: CLI -h shows help ---


def test_cli_dash_h_shows_help() -> None:
    """`-h` was listed as a known command but click only registered --help."""
    from behave_doctor.cli.app import main

    assert main(["-h"]) == 0


# --- Regression: impact_analysis validates project_path ---


def test_impact_analysis_none_raises_type_error() -> None:
    """impact_analysis(None, ...) must raise TypeError, like scan_project."""
    import pytest

    from behave_doctor import impact_analysis

    with pytest.raises(TypeError, match="project_path"):
        impact_analysis(None, [])  # type: ignore[arg-type]


# --- Regression: BD304 honours exclude_tags like BD303 does ---


def test_bd304_excluded_tag_behaves_as_tagless(tmp_path: Path) -> None:
    """A scenario whose only tag is in exclude_tags is skipped, not flagged
    orphan — the tag is excluded from coverage analysis entirely."""
    from behave_doctor.rules.base import RuleContext
    from behave_doctor.rules.coverage import OrphanScenario
    from behave_doctor.scanner import scan_features

    features = tmp_path / "features"
    features.mkdir()
    (features / "f.feature").write_text(
        "Feature: f\n"
        "  @manual\n"
        "  Scenario: only-manual\n"
        "    Given x\n"
        "  Scenario: tagless\n"
        "    Given x\n",
        encoding="utf-8",
    )
    project = scan_features(tmp_path, DoctorConfig())
    ctx = RuleContext(
        project=project,
        step_definitions=[],
        dependency_graph=DependencyGraph(),
        config=DoctorConfig(exclude_tags=["@manual"]),
    )
    diagnostics = OrphanScenario().check(ctx)
    assert diagnostics == []


def test_bd304_excluded_tag_still_leaves_other_tags(tmp_path: Path) -> None:
    """Excluded tags don't mask orphan status from remaining unique tags."""
    from behave_doctor.rules.base import RuleContext
    from behave_doctor.rules.coverage import OrphanScenario
    from behave_doctor.scanner import scan_features

    features = tmp_path / "features"
    features.mkdir()
    (features / "f.feature").write_text(
        "Feature: f\n  @manual @unique-x\n  Scenario: s\n    Given x\n",
        encoding="utf-8",
    )
    project = scan_features(tmp_path, DoctorConfig())
    ctx = RuleContext(
        project=project,
        step_definitions=[],
        dependency_graph=DependencyGraph(),
        config=DoctorConfig(exclude_tags=["@manual"]),
    )
    diagnostics = OrphanScenario().check(ctx)
    assert len(diagnostics) == 1
    assert diagnostics[0].metadata["tags"] == ["@unique-x"]


def test_text_reporter_quiet_counts_hidden_warnings() -> None:
    """--quiet hides warnings but the summary must still count them."""
    from datetime import datetime

    from behave_doctor.model.project_report import ProjectReport, ProjectStatistics

    diag = Diagnostic(
        rule_id="BD301",
        rule_name="unused",
        severity=Severity.WARNING,
        category=Category.COVERAGE,
        message="Unused step",
    )
    report = ProjectReport(
        project_path=Path("test/"),
        diagnostics=[diag],
        statistics=ProjectStatistics(),
        scanned_at=datetime(2024, 1, 1),
        scan_duration_ms=0,
    )
    out = TextReporter(use_color=False, quiet=True).format(report)
    assert "0 errors, 1 warnings" in out

"""Unit tests for the impact analysis module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from behave_doctor.impact import (
    AffectedScenario,
    ChangedFile,
    ImpactResult,
    ImpactSummary,
    format_impact,
    impact_analysis,
)
from behave_doctor.model.config import DoctorConfig
from behave_doctor.scanner.project_scanner import ScanError

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
IMPACT_PROJECT = FIXTURES / "impact_project"


# ---------------------------------------------------------------------------
# impact_analysis — core algorithm
# ---------------------------------------------------------------------------


class TestImpactAnalysis:
    """Tests for the impact_analysis() function."""

    def test_empty_changed_files_returns_empty_result(self) -> None:
        result = impact_analysis(IMPACT_PROJECT, [])
        assert result.affected_scenarios == []
        assert result.affected_features == []
        assert result.changed_files == []
        assert result.summary.changed_files == 0
        assert result.summary.scenarios_affected == 0

    def test_changed_py_file_finds_affected_scenarios(self) -> None:
        login_steps = IMPACT_PROJECT / "features" / "steps" / "login_steps.py"
        result = impact_analysis(IMPACT_PROJECT, [str(login_steps)])
        names = {s.name for s in result.affected_scenarios}
        assert "Successful login" in names
        assert "Failed login" in names
        # search.feature scenarios are also affected via Background
        assert "Search by keyword" in names
        assert "Search with filter" in names
        # Checkout scenarios should NOT be affected.
        assert "Add item to cart" not in names
        assert "Complete checkout" not in names

    def test_changed_feature_file_affects_all_scenarios_in_it(self) -> None:
        login_feature = IMPACT_PROJECT / "features" / "login.feature"
        result = impact_analysis(IMPACT_PROJECT, [str(login_feature)])
        names = {s.name for s in result.affected_scenarios}
        assert "Successful login" in names
        assert "Failed login" in names
        # Checkout scenarios should NOT be affected.
        assert "Add item to cart" not in names
        assert "Complete checkout" not in names

    def test_changed_checkout_steps_only_affects_checkout_scenarios(self) -> None:
        checkout_steps = IMPACT_PROJECT / "features" / "steps" / "checkout_steps.py"
        result = impact_analysis(IMPACT_PROJECT, [str(checkout_steps)])
        names = {s.name for s in result.affected_scenarios}
        assert "Add item to cart" in names
        assert "Complete checkout" in names
        assert "Successful login" not in names
        assert "Failed login" not in names
        assert "Search by keyword" not in names
        assert "Search with filter" not in names

    def test_changed_files_both_py_and_feature(self) -> None:
        login_steps = IMPACT_PROJECT / "features" / "steps" / "login_steps.py"
        checkout_feature = IMPACT_PROJECT / "features" / "checkout.feature"
        result = impact_analysis(IMPACT_PROJECT, [str(login_steps), str(checkout_feature)])
        names = {s.name for s in result.affected_scenarios}
        # From login_steps.py (including search.feature via Background)
        assert "Successful login" in names
        assert "Failed login" in names
        assert "Search by keyword" in names
        assert "Search with filter" in names
        # From checkout.feature
        assert "Add item to cart" in names
        assert "Complete checkout" in names

    def test_affected_scenarios_sorted_by_feature_then_line(self) -> None:
        login_feature = IMPACT_PROJECT / "features" / "login.feature"
        result = impact_analysis(IMPACT_PROJECT, [str(login_feature)])
        scenarios = result.affected_scenarios
        for i in range(1, len(scenarios)):
            key_prev = (scenarios[i - 1].feature_path, scenarios[i - 1].line)
            key_curr = (scenarios[i].feature_path, scenarios[i].line)
            assert key_prev <= key_curr

    def test_affected_features_are_unique_and_sorted(self) -> None:
        login_steps = IMPACT_PROJECT / "features" / "steps" / "login_steps.py"
        result = impact_analysis(IMPACT_PROJECT, [str(login_steps)])
        assert result.affected_features == sorted(set(result.affected_features))
        assert len(result.affected_features) == 2  # login.feature + search.feature

    def test_changed_file_entries_have_step_definition_counts(self) -> None:
        login_steps = IMPACT_PROJECT / "features" / "steps" / "login_steps.py"
        result = impact_analysis(IMPACT_PROJECT, [str(login_steps)])
        assert len(result.changed_files) == 1
        assert result.changed_files[0].step_definitions == 4

    def test_changed_feature_file_has_zero_step_definitions(self) -> None:
        login_feature = IMPACT_PROJECT / "features" / "login.feature"
        result = impact_analysis(IMPACT_PROJECT, [str(login_feature)])
        assert len(result.changed_files) == 1
        assert result.changed_files[0].step_definitions == 0

    def test_summary_counts_are_correct(self) -> None:
        login_steps = IMPACT_PROJECT / "features" / "steps" / "login_steps.py"
        result = impact_analysis(IMPACT_PROJECT, [str(login_steps)])
        assert result.summary.changed_files == 1
        # 2 from login.feature + 2 from search.feature (via Background)
        assert result.summary.scenarios_affected == 4
        assert result.summary.features_affected == 2
        assert result.summary.step_definitions_affected == 4

    def test_scenario_names_property(self) -> None:
        login_feature = IMPACT_PROJECT / "features" / "login.feature"
        result = impact_analysis(IMPACT_PROJECT, [str(login_feature)])
        assert "Successful login" in result.scenario_names
        assert "Failed login" in result.scenario_names

    def test_nonexistent_project_raises_filenotfounderror(self) -> None:
        with pytest.raises(FileNotFoundError, match="Project path does not exist"):
            impact_analysis(Path("/nonexistent/path"), [])

    def test_nonexistent_changed_file_raises_filenotfounderror(self) -> None:
        with pytest.raises(FileNotFoundError, match="Changed file does not exist"):
            impact_analysis(IMPACT_PROJECT, [str(IMPACT_PROJECT / "nonexistent.py")])

    def test_project_without_features_raises_scanerror(self, tmp_path: Path) -> None:
        fake_file = tmp_path / "fake.py"
        fake_file.write_text("# empty", encoding="utf-8")
        with pytest.raises(ScanError):
            impact_analysis(tmp_path, [str(fake_file)])

    def test_accepts_path_objects(self) -> None:
        login_steps = IMPACT_PROJECT / "features" / "steps" / "login_steps.py"
        result = impact_analysis(IMPACT_PROJECT, [login_steps])
        # 2 from login.feature + 2 from search.feature (via Background)
        assert len(result.affected_scenarios) == 4

    def test_explicit_config(self) -> None:
        login_steps = IMPACT_PROJECT / "features" / "steps" / "login_steps.py"
        cfg = DoctorConfig()
        result = impact_analysis(IMPACT_PROJECT, [str(login_steps)], cfg)
        # 2 from login.feature + 2 from search.feature (via Background)
        assert len(result.affected_scenarios) == 4

    # --- Regression tests for bugs found during audit ---

    def test_relative_paths_resolved_against_project_path(self) -> None:
        """Bug A: relative paths must resolve against project_path, not cwd."""
        result = impact_analysis(IMPACT_PROJECT, ["features/steps/login_steps.py"])
        # 2 from login.feature + 2 from search.feature (via Background)
        assert len(result.affected_scenarios) == 4
        names = {s.name for s in result.affected_scenarios}
        assert "Successful login" in names
        assert "Failed login" in names

    def test_relative_feature_path_resolved_against_project(self) -> None:
        """Bug A: relative .feature paths also resolve against project_path."""
        result = impact_analysis(IMPACT_PROJECT, ["features/checkout.feature"])
        assert len(result.affected_scenarios) == 2
        names = {s.name for s in result.affected_scenarios}
        assert "Add item to cart" in names

    def test_non_py_non_feature_file_is_skipped(self, tmp_path: Path) -> None:
        """Non-.py/.feature files should be silently skipped, not crash."""
        # Create a minimal project with a .txt file
        features_dir = tmp_path / "features"
        features_dir.mkdir()
        (features_dir / "dummy.feature").write_text(
            "Feature: Dummy\n  Scenario: Dummy\n    Given a step\n", encoding="utf-8"
        )
        txt_file = tmp_path / "README.txt"
        txt_file.write_text("test", encoding="utf-8")
        result = impact_analysis(tmp_path, [str(txt_file)])
        assert result.summary.changed_files == 0
        assert result.summary.scenarios_affected == 0

    def test_file_outside_project_is_skipped(self, tmp_path: Path) -> None:
        """Files outside project_path should be skipped with a warning."""
        features_dir = tmp_path / "features"
        features_dir.mkdir()
        (features_dir / "dummy.feature").write_text(
            "Feature: Dummy\n  Scenario: Dummy\n    Given a step\n", encoding="utf-8"
        )
        outside_py = tmp_path.parent / "outside_steps.py"
        outside_py.write_text("# empty", encoding="utf-8")
        try:
            result = impact_analysis(tmp_path, [str(outside_py)])
            assert result.summary.changed_files == 0
        finally:
            outside_py.unlink(missing_ok=True)

    def test_duplicate_changed_files_deduplicated(self) -> None:
        """Passing the same file twice should not double-count."""
        login_steps = str(IMPACT_PROJECT / "features" / "steps" / "login_steps.py")
        result = impact_analysis(IMPACT_PROJECT, [login_steps, login_steps])
        assert result.summary.changed_files == 1
        # 2 from login.feature + 2 from search.feature (via Background)
        assert result.summary.scenarios_affected == 4

    def test_mixed_valid_and_skipped_files(self) -> None:
        """Mix of valid .py and non-.py files should only count the valid ones."""
        login_steps = str(IMPACT_PROJECT / "features" / "steps" / "login_steps.py")
        readme = str(IMPACT_PROJECT / "features" / "login.feature")  # valid .feature
        result = impact_analysis(IMPACT_PROJECT, [login_steps, readme])
        assert result.summary.changed_files == 2
        # login_steps.py affects 4 (login + search via bg), login.feature affects 2
        # but they overlap, so total is 4
        assert result.summary.scenarios_affected == 4

    def test_step_definitions_affected_count_correct(self) -> None:
        """step_definitions_affected should count unique def_ids, not patterns."""
        login_steps = str(IMPACT_PROJECT / "features" / "steps" / "login_steps.py")
        result = impact_analysis(IMPACT_PROJECT, [login_steps])
        # login_steps.py has 4 step definitions
        assert result.summary.step_definitions_affected == 4

    def test_changed_file_entries_only_for_valid_files(self) -> None:
        """ChangedFile entries should only exist for .py and .feature files."""
        login_steps = str(IMPACT_PROJECT / "features" / "steps" / "login_steps.py")
        result = impact_analysis(IMPACT_PROJECT, [login_steps])
        assert len(result.changed_files) == 1
        assert result.changed_files[0].path.endswith("login_steps.py")
        assert result.changed_files[0].step_definitions == 4

    def test_background_steps_cause_cross_feature_impact(self) -> None:
        """Changing login_steps.py should also affect search.feature scenarios
        because search.feature has a Background that uses a login step."""
        login_steps = str(IMPACT_PROJECT / "features" / "steps" / "login_steps.py")
        result = impact_analysis(IMPACT_PROJECT, [login_steps])
        names = {s.name for s in result.affected_scenarios}
        # search.feature has Background: Given the user is on the login page
        assert "Search by keyword" in names
        assert "Search with filter" in names


# ---------------------------------------------------------------------------
# format_impact — output formatters
# ---------------------------------------------------------------------------


class TestFormatImpact:
    """Tests for format_impact() with text, json, and names formats."""

    @pytest.fixture
    def sample_result(self) -> ImpactResult:
        return ImpactResult(
            changed_files=[
                ChangedFile(path="/fake/login_steps.py", step_definitions=4),
            ],
            affected_scenarios=[
                AffectedScenario(
                    feature_path="/fake/login.feature",
                    line=3,
                    name="Successful login",
                    matched_steps=["the user is on the login page"],
                ),
                AffectedScenario(
                    feature_path="/fake/login.feature",
                    line=8,
                    name="Failed login",
                    matched_steps=["the user is on the login page"],
                ),
            ],
            affected_features=["/fake/login.feature"],
            summary=ImpactSummary(
                changed_files=1,
                step_definitions_affected=4,
                scenarios_affected=2,
                features_affected=1,
            ),
        )

    def test_text_format_contains_key_sections(self, sample_result: ImpactResult) -> None:
        out = format_impact(sample_result, "text")
        assert "Impact analysis: 1 changed files" in out
        assert "Changed files:" in out
        assert "Affected scenarios (2):" in out
        assert "Affected features (1):" in out
        assert "Successful login" in out
        assert "Failed login" in out

    def test_text_format_no_affected_scenarios(self) -> None:
        result = ImpactResult(
            changed_files=[],
            affected_scenarios=[],
            affected_features=[],
            summary=ImpactSummary(0, 0, 0, 0),
        )
        out = format_impact(result, "text")
        assert "Affected scenarios (0):" in out
        assert "(none)" in out

    def test_json_format_is_valid_json(self, sample_result: ImpactResult) -> None:
        out = format_impact(sample_result, "json")
        data = json.loads(out)
        assert data["summary"]["scenarios_affected"] == 2
        assert data["summary"]["changed_files"] == 1
        assert len(data["affected_scenarios"]) == 2
        assert data["affected_scenarios"][0]["name"] == "Successful login"
        assert data["affected_features"] == ["/fake/login.feature"]

    def test_names_format_one_per_line(self, sample_result: ImpactResult) -> None:
        out = format_impact(sample_result, "names")
        lines = out.strip().split("\n")
        assert lines == ["Successful login", "Failed login"]

    def test_names_format_empty_result(self) -> None:
        result = ImpactResult(
            changed_files=[],
            affected_scenarios=[],
            affected_features=[],
            summary=ImpactSummary(0, 0, 0, 0),
        )
        out = format_impact(result, "names")
        assert out == ""

    def test_invalid_format_raises_valueerror(self, sample_result: ImpactResult) -> None:
        with pytest.raises(ValueError, match="Unknown format"):
            format_impact(sample_result, "xml")

    def test_format_is_case_insensitive(self, sample_result: ImpactResult) -> None:
        out = format_impact(sample_result, "JSON")
        data = json.loads(out)
        assert data["summary"]["scenarios_affected"] == 2

    def test_empty_format_raises_valueerror(self, sample_result: ImpactResult) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            format_impact(sample_result, "")

    def test_whitespace_format_raises_valueerror(self, sample_result: ImpactResult) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            format_impact(sample_result, "   ")

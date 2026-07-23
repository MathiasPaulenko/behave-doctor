from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from behave_model import BehaveParserAdapter

from behave_doctor.model.config import DoctorConfig
from behave_doctor.scanner import ScanError, scan_features

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
SAMPLE_PROJECT = FIXTURES / "sample_project"


def test_scan_sample_project_returns_two_features() -> None:
    project = scan_features(SAMPLE_PROJECT, DoctorConfig())
    assert len(project.features) == 2
    names = {f.name for f in project.features}
    assert names == {"Login", "Checkout"}


def test_missing_features_dir_raises_scan_error(tmp_path: Path) -> None:
    with pytest.raises(ScanError, match="features/ directory not found"):
        scan_features(tmp_path, DoctorConfig())


def test_empty_features_dir_returns_empty_project(tmp_path: Path) -> None:
    (tmp_path / "features").mkdir()
    project = scan_features(tmp_path, DoctorConfig())
    assert len(project.features) == 0


def test_unparseable_feature_file_is_skipped(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    features = tmp_path / "features"
    features.mkdir()
    (features / "good.feature").write_text(
        "Feature: Good\n  Scenario: ok\n    Given a step\n", encoding="utf-8"
    )
    (features / "bad.feature").write_text(
        "This is not valid Gherkin at all !!!\n", encoding="utf-8"
    )
    project = scan_features(tmp_path, DoctorConfig())
    assert len(project.features) == 1
    assert project.features[0].name == "Good"
    assert "Could not parse" in caplog.text
    assert "bad.feature" in caplog.text


def test_unadaptable_feature_file_is_skipped(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    features = tmp_path / "features"
    features.mkdir()
    (features / "good.feature").write_text(
        "Feature: Good\n  Scenario: ok\n    Given a step\n", encoding="utf-8"
    )
    (features / "weird.feature").write_text(
        "Feature: Weird\n  Scenario: ok\n    Given a step\n", encoding="utf-8"
    )

    original = BehaveParserAdapter.adapt_feature

    def _boom_on_weird(
        self: BehaveParserAdapter, behave_feature: object, *, filename: str
    ) -> object:
        if "weird" in filename:
            raise AttributeError("boom")
        return original(self, behave_feature, filename=filename)

    with patch.object(BehaveParserAdapter, "adapt_feature", _boom_on_weird):
        project = scan_features(tmp_path, DoctorConfig())
    assert len(project.features) == 1
    assert project.features[0].name == "Good"
    assert "Could not adapt" in caplog.text
    assert "weird.feature" in caplog.text

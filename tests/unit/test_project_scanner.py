from __future__ import annotations

from pathlib import Path

import pytest

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
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
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
    captured = capsys.readouterr()
    assert "could not parse" in captured.err
    assert "bad.feature" in captured.err

from __future__ import annotations

from pathlib import Path

import pytest

from behave_doctor.model.config import DoctorConfig
from behave_doctor.model.enums import Severity

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
SAMPLE = FIXTURES / "config_sample_pyproject.toml"


def test_default_config_values() -> None:
    config = DoctorConfig()
    assert config.features_dir == "features/"
    assert config.steps_dir == "features/steps/"
    assert config.min_severity is Severity.INFO
    assert config.rules == {}
    assert config.exclude_paths == []
    assert config.exclude_tags == []


def test_config_mutable_defaults_are_independent() -> None:
    a = DoctorConfig()
    b = DoctorConfig()
    a.rules["BD401"] = {"max_steps": 5}
    a.exclude_paths.append("legacy/")
    a.exclude_tags.append("@wip")
    assert b.rules == {}
    assert b.exclude_paths == []
    assert b.exclude_tags == []


def test_from_pyproject_loads_full_config() -> None:
    config = DoctorConfig.from_pyproject(SAMPLE)
    assert config.features_dir == "features/"
    assert config.steps_dir == "features/steps/"
    assert config.min_severity is Severity.WARNING
    assert config.rules["BD203"] == {"enabled": True, "max_scenarios": 15}
    assert config.rules["BD401"] == {"enabled": True, "max_steps": 8}
    assert config.rules["BD402"] == {"enabled": False, "max_params": 4}
    assert config.exclude_paths == ["features/legacy/**", "features/archived/**"]
    assert config.exclude_tags == ["@wip", "@experimental"]


def test_from_pyproject_missing_section_returns_defaults(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "other"\n', encoding="utf-8")
    config = DoctorConfig.from_pyproject(pyproject)
    assert config.features_dir == "features/"
    assert config.min_severity is Severity.INFO
    assert config.rules == {}


def test_from_pyproject_invalid_severity_raises(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.behave-doctor]\nmin_severity = "critical"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid min_severity"):
        DoctorConfig.from_pyproject(pyproject)


def test_from_pyproject_nonexistent_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        DoctorConfig.from_pyproject(tmp_path / "missing.toml")


def test_from_pyproject_rule_overrides_merge_enabled_default(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.behave-doctor]\n[tool.behave-doctor.rules]\n"BD401" = { max_steps = 5 }\n',
        encoding="utf-8",
    )
    config = DoctorConfig.from_pyproject(pyproject)
    assert config.rules["BD401"] == {"enabled": True, "max_steps": 5}

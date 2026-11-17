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


def test_from_pyproject_top_level_exclude_tags(tmp_path: Path) -> None:
    """Top-level exclude_tags and exclude_paths are read and merged with sub-table."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.behave-doctor]\n"
        'exclude_tags = ["@smoke"]\n'
        'exclude_paths = ["features/legacy/**"]\n'
        "[tool.behave-doctor.exclude]\n"
        'tags = ["@wip"]\n'
        'paths = ["features/archived/**"]\n',
        encoding="utf-8",
    )
    config = DoctorConfig.from_pyproject(pyproject)
    assert config.exclude_tags == ["@smoke", "@wip"]
    assert config.exclude_paths == ["features/legacy/**", "features/archived/**"]


def test_from_pyproject_severity_is_case_insensitive(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.behave-doctor]\nmin_severity = "ERROR"\n', encoding="utf-8")
    config = DoctorConfig.from_pyproject(pyproject)
    assert config.min_severity is Severity.ERROR


def test_from_pyproject_exclude_values_can_be_strings(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.behave-doctor]\nexclude_paths = "features/legacy/**"\nexclude_tags = "@wip"\n',
        encoding="utf-8",
    )
    config = DoctorConfig.from_pyproject(pyproject)
    assert config.exclude_paths == ["features/legacy/**"]
    assert config.exclude_tags == ["@wip"]


def test_from_pyproject_rule_override_can_be_boolean(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.behave-doctor.rules]\nBD101 = false\nBD102 = true\n",
        encoding="utf-8",
    )
    config = DoctorConfig.from_pyproject(pyproject)
    assert config.rules["BD101"] == {"enabled": False}
    assert config.rules["BD102"] == {"enabled": True}


def test_config_coerces_string_fields() -> None:
    cfg = DoctorConfig(exclude_paths="vendor/**", exclude_tags="wip")  # type: ignore[arg-type]
    assert cfg.exclude_paths == ["vendor/**"]
    assert cfg.exclude_tags == ["wip"]
    cfg = DoctorConfig(min_severity="Warning")  # type: ignore[arg-type]
    assert cfg.min_severity is Severity.WARNING


def test_config_coerces_path_like_dirs() -> None:
    cfg = DoctorConfig(features_dir=Path("bdd"), steps_dir=Path("bdd/steps"))  # type: ignore[arg-type]
    assert cfg.features_dir == "bdd"
    assert cfg.steps_dir == "bdd/steps" or cfg.steps_dir == r"bdd\steps"


def test_from_pyproject_malformed_tool_section(tmp_path: Path) -> None:
    """A non-table ``tool`` or ``behave-doctor`` value must not crash."""
    for content in ('tool = "x"\n', '[tool]\nbehave-doctor = "x"\n'):
        f = tmp_path / "pyproject.toml"
        f.write_text(content, encoding="utf-8")
        assert DoctorConfig.from_pyproject(f) == DoctorConfig()


def test_config_coerces_non_string_pattern_elements() -> None:
    """Non-string entries (e.g. TOML ``exclude_paths = [123]``) must not
    reach ``Path.match`` — it raises ``TypeError`` for them."""
    cfg = DoctorConfig(exclude_paths=[123, "legacy/**"], exclude_tags=[None, "wip"])  # type: ignore[list-item]
    assert cfg.exclude_paths == ["123", "legacy/**"]
    assert cfg.exclude_tags == ["None", "wip"]
    # And exclusion matching still works without crashing.
    assert cfg.is_excluded(Path("features/legacy/old.feature"))
    assert not cfg.is_excluded(Path("features/new.feature"))

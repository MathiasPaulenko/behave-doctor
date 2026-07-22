"""DoctorConfig dataclass — configuration for behave-doctor."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from behave_doctor.model.enums import Severity


@dataclass
class DoctorConfig:
    """Configuration for a behave-doctor scan.

    Attributes:
        features_dir: Relative path to the features directory.
        steps_dir: Relative path to the step definitions directory.
        min_severity: Minimum severity to report.
        rules: Per-rule overrides keyed by rule ID. Each rule dict defaults
            to ``{"enabled": True}`` merged with any user-provided overrides.
        exclude_paths: Glob patterns of paths to exclude from scanning.
        exclude_tags: Tags to exclude from coverage analysis.
    """

    features_dir: str = "features/"
    steps_dir: str = "features/steps/"
    min_severity: Severity = Severity.INFO
    rules: dict[str, dict[str, Any]] = field(default_factory=dict)
    exclude_paths: list[str] = field(default_factory=list)
    exclude_tags: list[str] = field(default_factory=list)

    @classmethod
    def from_pyproject(cls, path: Path) -> DoctorConfig:
        """Load configuration from the ``[tool.behave-doctor]`` section of a TOML file.

        Args:
            path: Path to a ``pyproject.toml`` (or any TOML) file.

        Returns:
            A ``DoctorConfig``. If the ``[tool.behave-doctor]`` section is
            missing, the default config is returned.

        Raises:
            FileNotFoundError: If ``path`` does not exist.
            ValueError: If ``min_severity`` is not a valid severity name.
        """
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with path.open("rb") as handle:
            data = tomllib.load(handle)

        section = data.get("tool", {}).get("behave-doctor")
        if not section:
            return cls()

        features_dir = str(section.get("features_dir", "features/"))
        steps_dir = str(section.get("steps_dir", "features/steps/"))

        min_severity_raw = str(section.get("min_severity", "info"))
        try:
            min_severity = Severity(min_severity_raw)
        except ValueError as exc:
            valid = ", ".join(s.value for s in Severity)
            msg = f"Invalid min_severity {min_severity_raw!r} in {path}. Valid values: {valid}."
            raise ValueError(msg) from exc

        raw_rules = section.get("rules", {})
        rules: dict[str, dict[str, Any]] = {}
        if isinstance(raw_rules, dict):
            for rule_id, overrides in raw_rules.items():
                merged: dict[str, Any] = {"enabled": True}
                if isinstance(overrides, dict):
                    merged.update(overrides)
                rules[str(rule_id)] = merged

        exclude = section.get("exclude", {}) or {}
        exclude_paths = [str(p) for p in exclude.get("paths", [])]
        exclude_tags = [str(t) for t in exclude.get("tags", [])]

        return cls(
            features_dir=features_dir,
            steps_dir=steps_dir,
            min_severity=min_severity,
            rules=rules,
            exclude_paths=exclude_paths,
            exclude_tags=exclude_tags,
        )

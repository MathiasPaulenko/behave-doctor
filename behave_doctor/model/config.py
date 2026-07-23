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

    def is_excluded(self, path: Path) -> bool:
        """Return ``True`` if ``path`` matches any configured exclude glob pattern.

        Both the path itself and each of its parent directories are checked
        so that directory-level patterns (``"excluded/**"``) and file-level
        patterns (``"*.feature"``) both work.
        """
        if not self.exclude_paths:
            return False
        parts = [path, *path.parents]
        for pattern in self.exclude_paths:
            if not pattern:
                continue
            for part in parts:
                try:
                    if part.match(pattern):
                        return True
                except ValueError:
                    # Invalid glob pattern; ignore it.
                    continue
        return False

    @classmethod
    def from_pyproject(cls, path: Path) -> DoctorConfig:
        """Load configuration from the ``[tool.behave-doctor]`` section of a TOML file.

        Args:
            path: Path to a ``pyproject.toml`` (or any TOML) file.

        Returns:
            A ``DoctorConfig``. If the ``[tool.behave-doctor]`` section is
            missing, the default config is returned.

        Raises:
            TypeError: If ``path`` is ``None``.
            FileNotFoundError: If ``path`` does not exist.
            IsADirectoryError: If ``path`` is a directory, not a file.
            ValueError: If ``min_severity`` is not a valid severity name.
        """
        if path is None:
            msg = "from_pyproject() requires a Path argument, got None."
            raise TypeError(msg)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        if path.is_dir():
            raise IsADirectoryError(f"Config path is a directory, not a file: {path}")

        with path.open("rb") as handle:
            data = tomllib.load(handle)

        section = data.get("tool", {}).get("behave-doctor")
        if not section:
            return cls()

        features_dir = str(section.get("features_dir", "features/"))
        steps_dir = str(section.get("steps_dir", "features/steps/"))

        min_severity_raw = str(section.get("min_severity", "info")).strip().lower()
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
                if isinstance(overrides, bool):
                    merged["enabled"] = overrides
                elif isinstance(overrides, dict):
                    merged.update(overrides)
                rules[str(rule_id)] = merged

        # Read exclude_paths and exclude_tags from both the top level and
        # the [tool.behave-doctor.exclude] sub-table. Both sources are merged.
        def _as_str_list(value: Any) -> list[str]:
            if isinstance(value, str):
                return [value]
            if isinstance(value, (list, tuple)):
                return [str(item) for item in value]
            return []

        def _as_list(value: Any) -> list[str]:
            if isinstance(value, (list, tuple)):
                return [str(item) for item in value]
            return []

        top_paths = section.get("exclude_paths", [])
        top_tags = section.get("exclude_tags", [])
        exclude = section.get("exclude", {})
        if isinstance(exclude, dict):
            sub_paths = exclude.get("paths", [])
            sub_tags = exclude.get("tags", [])
        else:
            sub_paths = []
            sub_tags = []
        raw_paths = _as_str_list(top_paths) + _as_list(sub_paths)
        raw_tags = _as_str_list(top_tags) + _as_list(sub_tags)
        exclude_paths = [str(p) for p in raw_paths]
        exclude_tags = [str(t) for t in raw_tags]

        return cls(
            features_dir=features_dir,
            steps_dir=steps_dir,
            min_severity=min_severity,
            rules=rules,
            exclude_paths=exclude_paths,
            exclude_tags=exclude_tags,
        )

"""DoctorConfig dataclass — configuration for behave-doctor."""

from __future__ import annotations

import itertools
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

    def __post_init__(self) -> None:
        # Tolerate common construction mistakes: a bare string is one
        # element, not an iterable of characters, and Path objects are fine
        # for directory fields.
        self.features_dir = str(self.features_dir)
        self.steps_dir = str(self.steps_dir)
        if isinstance(self.min_severity, str):
            self.min_severity = Severity(self.min_severity.strip().lower())
        if isinstance(self.exclude_paths, str):
            self.exclude_paths = [self.exclude_paths]
        if isinstance(self.exclude_tags, str):
            self.exclude_tags = [self.exclude_tags]
        # Glob patterns must be strings — a TOML array like ``[123]`` would
        # otherwise crash ``Path.match`` with ``TypeError`` during the scan.
        self.exclude_paths = [str(p) for p in self.exclude_paths]
        self.exclude_tags = [str(t) for t in self.exclude_tags]
        # Rule IDs are upper-case (``BD301``); normalise keys so hand-built
        # configs match the same way ``from_pyproject`` normalised them.
        if isinstance(self.rules, dict):
            self.rules = {str(k).upper(): v for k, v in self.rules.items()}

    def is_excluded(self, path: Path, *, within: Path | None = None) -> bool:
        """Return ``True`` if ``path`` matches any configured exclude glob pattern.

        Both the path itself and each of its parent directories are checked
        so that directory-level patterns (``"excluded/**"``) and file-level
        patterns (``"*.feature"``) both work.

        When ``within`` is given, ancestors are only checked down to (and
        excluding) that directory — otherwise a pattern could silently
        exclude the whole project by matching a parent directory of the
        scan root (e.g. ``"build"`` when the project lives under
        ``C:\\build\\project``).
        """
        if not self.exclude_paths:
            return False
        parts = [path, *itertools.takewhile(lambda parent: parent != within, path.parents)]
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
            tomllib.TOMLDecodeError: If the file is not valid TOML
                (a subclass of ``ValueError``).
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

        tool = data.get("tool", {})
        section = tool.get("behave-doctor") if isinstance(tool, dict) else None
        if not isinstance(section, dict):
            # Missing section, or a malformed TOML shape like
            # ``tool = "x"`` / ``behave-doctor = "x"`` — treat as defaults.
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
                # Normalise to upper-case so ``rules.bd301`` matches ``BD301``.
                rules[str(rule_id).upper()] = merged

        # Read exclude_paths and exclude_tags from both the top level and
        # the [tool.behave-doctor.exclude] sub-table. Both sources are merged.
        def _as_str_list(value: Any) -> list[str]:
            if isinstance(value, str):
                return [value]
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
        raw_paths = _as_str_list(top_paths) + _as_str_list(sub_paths)
        raw_tags = _as_str_list(top_tags) + _as_str_list(sub_tags)
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

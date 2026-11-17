"""Project scanner — load all ``.feature`` files into a behave-model Project."""

from __future__ import annotations

import fnmatch
import logging
import os
from collections.abc import Iterator
from pathlib import Path

from behave_model import BehaveParserAdapter, Metadata, Project, parse_feature
from behave_model.exceptions import ParseError

from behave_doctor.model.config import DoctorConfig

logger = logging.getLogger(__name__)


class ScanError(Exception):
    """Raised when a project cannot be scanned (e.g. missing features dir)."""


def _walk_files(
    root: Path,
    pattern: str,
    errors: list[tuple[Path, str]] | None = None,
) -> Iterator[Path]:
    """Yield files under ``root`` whose name matches ``pattern``.

    Equivalent to ``root.rglob(pattern)`` but tolerant of unreadable
    directories — ``os.walk``'s ``onerror`` logs and continues instead of
    aborting the whole scan (e.g. a permission-denied subdirectory on
    POSIX CI). Case sensitivity follows ``fnmatch``/the platform, the same
    rule ``rglob`` uses.

    When ``errors`` is provided, each unreadable directory is recorded as a
    ``(path, message)`` pair so callers can surface it (BD305).
    """

    def _onerror(error: OSError) -> None:
        logger.warning("Cannot access %s: %s. Skipping.", error.filename or root, error)
        if errors is not None:
            errors.append((Path(error.filename) if error.filename else root, str(error)))

    for dirpath, _dirnames, filenames in os.walk(root, onerror=_onerror):
        for name in filenames:
            if fnmatch.fnmatch(name, pattern):
                yield Path(dirpath) / name


def _strip_empty_examples(behave_feature: object) -> None:
    """Drop ``Examples`` blocks without a table, matching Behave's runtime.

    Behave tolerates a tabless ``Examples:`` block — it simply generates
    zero scenarios — but behave-model's adapter dereferences
    ``table.headings`` unconditionally and would drop the whole feature.
    Applies to outlines directly under the feature and inside ``Rule:``
    blocks.
    """
    scenarios = list(getattr(behave_feature, "scenarios", []) or [])
    for rule in getattr(behave_feature, "rules", []) or []:
        scenarios.extend(getattr(rule, "scenarios", []) or [])
    for scenario in scenarios:
        examples = getattr(scenario, "examples", None)
        if examples:
            scenario.examples = [ex for ex in examples if getattr(ex, "table", None) is not None]


def scan_features(
    project_path: Path,
    config: DoctorConfig,
    errors: list[tuple[Path, str]] | None = None,
) -> Project:
    """Scan a Behave project directory and return a behave-model ``Project``.

    Args:
        project_path: Root directory of the Behave project.
        config: Configuration specifying the features directory.
        errors: Optional list that receives ``(file, message)`` pairs for
            feature files that fail to parse or adapt. Failures are also
            logged as warnings.

    Returns:
        A ``Project`` containing all parseable ``.feature`` files.

    Raises:
        ScanError: If the features directory does not exist.
    """
    features_dir = (project_path / config.features_dir).resolve()
    if not features_dir.exists():
        raise ScanError(f"features/ directory not found at {features_dir}")
    if not features_dir.is_dir():
        raise ScanError(f"features/ path is not a directory: {features_dir}")

    feature_files = sorted(_walk_files(features_dir, "*.feature", errors))
    feature_files = [f for f in feature_files if not config.is_excluded(f, within=features_dir)]
    if not feature_files:
        return Project(
            features=[],
            global_tags=[],
            metadata=Metadata(source_path=str(features_dir)),
        )

    adapter = BehaveParserAdapter()
    features = []
    for fpath in feature_files:
        try:
            # Decode exactly like ``behave.parser.parse_file``
            # (``data.decode("utf8")`` — no BOM stripping): a BOM'd feature
            # is a parse error at runtime, not a silently valid file.
            text = fpath.read_text(encoding="utf-8")
            behave_feature = parse_feature(text, filename=str(fpath))
            if behave_feature is None:
                # Empty file or no Feature: statement — Behave silently
                # skips these at runtime, it is not a parse error.
                continue
            _strip_empty_examples(behave_feature)
            features.append(adapter.adapt_feature(behave_feature, filename=str(fpath)))
        except (ParseError, OSError, UnicodeError) as exc:
            logger.warning("Could not parse %s: %s. Skipping this file.", fpath, exc)
            if errors is not None:
                errors.append((fpath, str(exc)))
            continue
        except Exception as exc:
            if isinstance(exc, (MemoryError, RecursionError)):
                raise
            logger.warning("Could not adapt %s: %s. Skipping this file.", fpath, exc)
            if errors is not None:
                errors.append((fpath, str(exc)))
            continue

    return Project(
        features=features,
        global_tags=[],
        metadata=Metadata(source_path=str(features_dir)),
    )

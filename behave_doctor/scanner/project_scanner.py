"""Project scanner — load all ``.feature`` files into a behave-model Project."""

from __future__ import annotations

import logging
from pathlib import Path

from behave_model import BehaveParserAdapter, Metadata, Project, parse_feature
from behave_model.exceptions import ParseError

from behave_doctor.model.config import DoctorConfig

logger = logging.getLogger(__name__)


class ScanError(Exception):
    """Raised when a project cannot be scanned (e.g. missing features dir)."""


def scan_features(project_path: Path, config: DoctorConfig) -> Project:
    """Scan a Behave project directory and return a behave-model ``Project``.

    Args:
        project_path: Root directory of the Behave project.
        config: Configuration specifying the features directory.

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

    feature_files = sorted(features_dir.rglob("*.feature"))
    feature_files = [f for f in feature_files if not config.is_excluded(f)]
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
            text = fpath.read_text(encoding="utf-8-sig")
            behave_feature = parse_feature(text, filename=str(fpath))
            features.append(adapter.adapt_feature(behave_feature, filename=str(fpath)))
        except (ParseError, OSError, UnicodeError) as exc:
            logger.warning("Could not parse %s: %s. Skipping this file.", fpath, exc)
            continue
        except Exception as exc:
            if isinstance(exc, (MemoryError, RecursionError)):
                raise
            logger.warning("Could not adapt %s: %s. Skipping this file.", fpath, exc)
            continue

    return Project(
        features=features,
        global_tags=[],
        metadata=Metadata(source_path=str(features_dir)),
    )

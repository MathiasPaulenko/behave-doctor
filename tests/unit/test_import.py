from __future__ import annotations

import behave_doctor


def test_import_works() -> None:
    assert behave_doctor is not None


def test_version_is_set() -> None:
    from importlib.metadata import version as metadata_version

    # __version__ must match the installed package metadata (pyproject.toml).
    assert behave_doctor.__version__ == metadata_version("behave-doctor")
    assert behave_doctor.__version__ != "0.0.0"

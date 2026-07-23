from __future__ import annotations

import behave_doctor


def test_import_works() -> None:
    assert behave_doctor is not None


def test_version_is_set() -> None:
    assert behave_doctor.__version__ == "1.1.0"

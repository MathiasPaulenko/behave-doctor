from __future__ import annotations

from pathlib import Path

import pytest

from behave_doctor.model.config import DoctorConfig
from behave_doctor.scanner.step_scanner import scan_steps

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _scan_fixture(filename: str, tmp_path: Path) -> list:
    """Copy a fixture file into a temp steps dir and scan it."""
    steps_dir = tmp_path / "steps"
    steps_dir.mkdir()
    (steps_dir / filename).write_text(
        (FIXTURES / filename).read_text(encoding="utf-8"), encoding="utf-8"
    )
    return scan_steps(steps_dir, DoctorConfig())


def test_extracts_all_keyword_types(tmp_path: Path) -> None:
    defs = _scan_fixture("steps_sample.py", tmp_path)
    keywords = {d.keyword for d in defs}
    assert {"given", "when", "then", "step"} <= keywords


def test_handles_behave_attribute_form(tmp_path: Path) -> None:
    defs = _scan_fixture("steps_sample.py", tmp_path)
    behave_defs = [d for d in defs if d.pattern == "the user is on the login page"]
    assert len(behave_defs) == 1
    assert behave_defs[0].keyword == "given"


def test_handles_aliased_imports(tmp_path: Path) -> None:
    defs = _scan_fixture("steps_aliased.py", tmp_path)
    patterns = {d.pattern for d in defs}
    assert "the user is logged in" in patterns
    assert "the user clicks the button" in patterns
    assert all(d.keyword in {"given", "when"} for d in defs)


def test_re_prefix_detected(tmp_path: Path) -> None:
    defs = _scan_fixture("steps_sample.py", tmp_path)
    re_defs = [d for d in defs if d.matcher_type == "re"]
    assert len(re_defs) == 1
    assert re_defs[0].pattern.startswith("re:")


def test_converter_kwarg_detected(tmp_path: Path) -> None:
    defs = _scan_fixture("steps_sample.py", tmp_path)
    cf_defs = [d for d in defs if d.matcher_type == "cfparse"]
    assert len(cf_defs) == 1
    assert cf_defs[0].pattern == "a product with converter"


def test_function_name_and_line_extracted(tmp_path: Path) -> None:
    defs = _scan_fixture("steps_sample.py", tmp_path)
    by_name = {d.function_name: d for d in defs}
    assert "given_user_logged_in" in by_name
    assert by_name["given_user_logged_in"].line >= 1


def test_parameters_extracted(tmp_path: Path) -> None:
    defs = _scan_fixture("steps_sample.py", tmp_path)
    by_pattern = {d.pattern: d for d in defs}
    assert "text" in by_pattern["the user enters {text}"].parameters
    assert "n" in by_pattern["the cart should contain {n} items"].parameters


def test_malformed_file_skipped_with_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    defs = _scan_fixture("steps_malformed.py", tmp_path)
    assert defs == []
    captured = capsys.readouterr()
    assert "could not parse" in captured.err


def test_empty_dir_returns_empty_list(tmp_path: Path) -> None:
    assert scan_steps(tmp_path, DoctorConfig()) == []


def test_nonexistent_dir_returns_empty_list(tmp_path: Path) -> None:
    assert scan_steps(tmp_path / "missing", DoctorConfig()) == []

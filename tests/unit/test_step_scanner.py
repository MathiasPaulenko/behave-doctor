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
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    defs = _scan_fixture("steps_malformed.py", tmp_path)
    assert defs == []
    assert "Could not parse" in caplog.text


def test_empty_dir_returns_empty_list(tmp_path: Path) -> None:
    assert scan_steps(tmp_path, DoctorConfig()) == []


def test_nonexistent_dir_returns_empty_list(tmp_path: Path) -> None:
    assert scan_steps(tmp_path / "missing", DoctorConfig()) == []


def test_nested_functions_are_not_step_defs(tmp_path: Path) -> None:
    """Nested functions and class methods must not be picked up as step definitions."""
    steps = tmp_path / "steps"
    steps.mkdir()
    (steps / "nested.py").write_text(
        "from behave import given\n"
        "\n"
        '@given("outer step")\n'
        "def outer():\n"
        '    @given("nested step")\n'
        "    def inner():\n"
        "        pass\n"
        "\n"
        "class Steps:\n"
        '    @given("method step")\n'
        "    def method(self):\n"
        "        pass\n",
        encoding="utf-8",
    )
    defs = scan_steps(steps, DoctorConfig())
    assert len(defs) == 1
    assert defs[0].pattern == "outer step"


def test_dotted_import_behave_detected(tmp_path: Path) -> None:
    """'import behave.given' still lets @behave.given decorators be discovered."""
    steps = tmp_path / "steps"
    steps.mkdir()
    (steps / "dotted.py").write_text(
        "import behave.given\n"
        "\n"
        '@behave.given("a dotted import step")\n'
        "def step_impl():\n"
        "    pass\n",
        encoding="utf-8",
    )
    defs = scan_steps(steps, DoctorConfig())
    assert len(defs) == 1
    assert defs[0].pattern == "a dotted import step"


def test_pattern_keyword_argument_detected(tmp_path: Path) -> None:
    """Step decorators with pattern='...' keyword argument must be discovered."""
    steps = tmp_path / "steps"
    steps.mkdir()
    (steps / "kwarg.py").write_text(
        "from behave import given, when, then\n"
        "\n"
        '@given(pattern="a keyword pattern")\n'
        "def step_given():\n"
        "    pass\n"
        "\n"
        '@when(pattern="an action occurs")\n'
        "def step_when():\n"
        "    pass\n"
        "\n"
        '@then(pattern="the result is visible")\n'
        "def step_then():\n"
        "    pass\n",
        encoding="utf-8",
    )
    defs = scan_steps(steps, DoctorConfig())
    patterns = {d.pattern for d in defs}
    assert "a keyword pattern" in patterns
    assert "an action occurs" in patterns
    assert "the result is visible" in patterns
    assert {d.keyword for d in defs} == {"given", "when", "then"}


def test_typed_parse_placeholder_detected(tmp_path: Path) -> None:
    """Parse/cfparse patterns with {name:type} placeholders must be compiled
    and their parameters extracted."""
    steps = tmp_path / "steps"
    steps.mkdir()
    (steps / "typed.py").write_text(
        "from behave import given, when\n"
        "\n"
        '@given("I have {n:d} items", converter=lambda x: int(x))\n'
        "def step_count(n):\n"
        "    pass\n"
        "\n"
        '@when("user {name} logs in")\n'
        "def step_user(name):\n"
        "    pass\n",
        encoding="utf-8",
    )
    defs = scan_steps(steps, DoctorConfig())
    by_pattern = {d.pattern: d for d in defs}
    assert "I have {n:d} items" in by_pattern
    assert "n" in by_pattern["I have {n:d} items"].parameters
    assert by_pattern["I have {n:d} items"].matcher_type == "cfparse"
    assert "name" in by_pattern["user {name} logs in"].parameters
    assert by_pattern["user {name} logs in"].pattern_compiled.fullmatch("user Alice logs in")

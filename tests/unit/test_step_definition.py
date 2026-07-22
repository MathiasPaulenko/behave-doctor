from __future__ import annotations

import re
from pathlib import Path

from behave_doctor.model.step_definition import StepDefinition


def _make_def(**overrides: object) -> StepDefinition:
    defaults: dict[str, object] = {
        "keyword": "given",
        "pattern": "the user is logged in",
        "pattern_compiled": re.compile("the user is logged in"),
        "matcher_type": "parse",
        "file": Path("steps/auth.py"),
        "line": 10,
        "function_name": "user_logged_in",
        "module": "auth",
        "parameters": [],
    }
    defaults.update(overrides)
    return StepDefinition(**defaults)  # type: ignore[arg-type]


def test_step_definition_is_frozen() -> None:
    sd = _make_def()
    try:
        sd.keyword = "when"  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("StepDefinition should be frozen")


def test_def_id_combines_module_and_function() -> None:
    sd = _make_def(module="auth", function_name="user_logged_in")
    assert sd.def_id == "auth.user_logged_in"


def test_default_parameters_is_empty_list() -> None:
    sd = _make_def()
    assert sd.parameters == []

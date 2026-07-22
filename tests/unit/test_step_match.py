from __future__ import annotations

from behave_doctor.model.step_match import StepMatch


def test_step_match_no_definition_defaults() -> None:
    match = StepMatch(step=object(), step_definition=None)
    assert match.step_definition is None
    assert match.ambiguous is False


def test_step_match_ambiguous_flag() -> None:
    match = StepMatch(step=object(), step_definition=None, ambiguous=True)
    assert match.ambiguous is True

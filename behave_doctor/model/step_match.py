"""The StepMatch dataclass — a feature step matched to a step definition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from behave_doctor.model.step_definition import StepDefinition


@dataclass(frozen=True)
class StepMatch:
    """The result of matching a feature step against step definitions.

    Attributes:
        step: The behave-model ``Step`` being matched.
        step_definition: The matched ``StepDefinition``, or ``None`` if no match.
        ambiguous: ``True`` if multiple definitions matched.
    """

    step: Any
    step_definition: StepDefinition | None
    ambiguous: bool = False

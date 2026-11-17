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
            When several definitions match, this is the one Behave would
            select at runtime (keyword-registry definitions take priority).
        ambiguous: ``True`` if multiple definitions matched.
        matches: All matching definitions, in Behave's registry order.
    """

    step: Any
    step_definition: StepDefinition | None
    ambiguous: bool = False
    matches: tuple[StepDefinition, ...] = ()

"""The DependencyGraph dataclass — feature/step/module relationships."""

from __future__ import annotations

from dataclasses import dataclass, field

from behave_doctor.model.step_match import StepMatch


@dataclass
class DependencyGraph:
    """Graph mapping features → step definitions → modules.

    Attributes:
        feature_steps: Feature name → set of step definition IDs used.
        step_usage: Step definition ID → set of feature names using it.
        module_imports: Module name → set of imported module names.
        step_matches: One ``StepMatch`` per step in the project.
    """

    feature_steps: dict[str, set[str]] = field(default_factory=dict)
    step_usage: dict[str, set[str]] = field(default_factory=dict)
    module_imports: dict[str, set[str]] = field(default_factory=dict)
    step_matches: list[StepMatch] = field(default_factory=list)

    def add_step_match(self, match: StepMatch, feature_name: str = "") -> None:
        """Record a step match, updating ``step_matches`` and the usage maps.

        Args:
            match: The step match to record.
            feature_name: Name of the feature the step belongs to. When
                provided and the match resolved a definition, the
                ``feature_steps`` and ``step_usage`` maps are updated.
        """
        self.step_matches.append(match)
        definition = match.step_definition
        if definition is None or not feature_name:
            return
        self.feature_steps.setdefault(feature_name, set()).add(definition.def_id)
        self.step_usage.setdefault(definition.def_id, set()).add(feature_name)

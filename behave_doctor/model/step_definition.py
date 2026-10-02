"""The StepDefinition dataclass — a discovered step definition."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StepDefinition:
    """A step definition discovered from Python source files.

    Attributes:
        keyword: The step keyword (``"given"`` | ``"when"`` | ``"then"`` | ``"step"``).
        pattern: The step pattern string.
        matcher: The matcher object used to match step text — a Behave
            ``Matcher`` (``ParseMatcher``, ``CFParseMatcher``, regex matchers)
            or an approximate fallback for patterns with runtime-registered
            custom types. Exposes ``matches(text) -> bool``.
        matcher_type: The matcher type (``"parse"`` | ``"cfparse"`` |
            ``"re"`` | ``"re0"``), as selected by ``use_step_matcher``.
        file: Source file path.
        line: Line number of the decorator.
        function_name: Name of the step function.
        module: Module dotted path.
        parameters: Parameter names extracted from the pattern.
        approximate: ``True`` when the matcher is approximate because the
            pattern uses a custom type only registered at runtime.
    """

    keyword: str
    pattern: str
    matcher: Any
    matcher_type: str
    file: Path
    line: int
    function_name: str
    module: str
    parameters: list[str] = field(default_factory=list)
    approximate: bool = False

    @property
    def def_id(self) -> str:
        """Stable identifier for the definition: ``"{module}.{function_name}"``."""
        return f"{self.module}.{self.function_name}"

"""The StepDefinition dataclass — a discovered step definition."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class StepDefinition:
    """A step definition discovered from Python source files.

    Attributes:
        keyword: The step keyword (``"given"`` | ``"when"`` | ``"then"`` | ``"step"``).
        pattern: The step pattern string.
        pattern_compiled: Compiled regex used for matching step text.
        matcher_type: The matcher type (``"re"`` | ``"parse"`` | ``"cfparse"`` | ``"regex"``).
        file: Source file path.
        line: Line number of the decorator.
        function_name: Name of the step function.
        module: Module dotted path.
        parameters: Parameter names extracted from the pattern.
    """

    keyword: str
    pattern: str
    pattern_compiled: re.Pattern[str]
    matcher_type: str
    file: Path
    line: int
    function_name: str
    module: str
    parameters: list[str] = field(default_factory=list)

    @property
    def def_id(self) -> str:
        """Stable identifier for the definition: ``"{module}.{function_name}"``."""
        return f"{self.module}.{self.function_name}"

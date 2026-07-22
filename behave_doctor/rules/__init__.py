"""Rule registry — discovers and provides all built-in rule instances."""

from __future__ import annotations

import contextlib
import importlib
from typing import TYPE_CHECKING

from behave_doctor.rules.base import Rule

if TYPE_CHECKING:
    from behave_doctor.rules.base import RuleContext  # noqa: F401


# Rule modules that ship with behave-doctor. Each is imported lazily so the
# registry works even if some modules do not yet exist.
_RULE_MODULES: list[str] = [
    "behave_doctor.rules.structure",
    "behave_doctor.rules.quality",
    "behave_doctor.rules.coverage",
    "behave_doctor.rules.complexity",
    "behave_doctor.rules.dependencies",
]

_registry: dict[str, type[Rule]] = {}


def register(rule_cls: type[Rule]) -> type[Rule]:
    """Register a rule class. Usable as a decorator."""
    if rule_cls.id:
        _registry[rule_cls.id] = rule_cls
    return rule_cls


def _discover_rules() -> None:
    """Import all rule modules and collect ``Rule`` subclasses into the registry."""
    for module_name in _RULE_MODULES:
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Rule) and attr is not Rule and attr.id:
                _registry.setdefault(attr.id, attr)


def get_all_rules() -> list[Rule]:
    """Return instances of all registered rules."""
    if not _registry:
        _discover_rules()
    return [cls() for cls in _registry.values()]


def get_rule(rule_id: str) -> Rule | None:
    """Return an instance of the rule with the given ID, or ``None``."""
    if not _registry:
        _discover_rules()
    cls = _registry.get(rule_id)
    return cls() if cls is not None else None


def clear_registry() -> None:
    """Clear the registry. Primarily useful for tests."""
    _registry.clear()


__all__ = [
    "Rule",
    "clear_registry",
    "get_all_rules",
    "get_rule",
    "register",
]


# Import rule modules so rules register themselves on package import.
# Each import is guarded so a missing module does not break the registry.
for _module in _RULE_MODULES:
    with contextlib.suppress(ModuleNotFoundError):
        importlib.import_module(_module)

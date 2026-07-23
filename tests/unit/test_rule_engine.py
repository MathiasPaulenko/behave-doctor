from __future__ import annotations

from behave_model import Project

from behave_doctor.model.config import DoctorConfig
from behave_doctor.model.dependency_graph import DependencyGraph
from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Category, Severity
from behave_doctor.rules import (
    Rule,
    clear_registry,
    get_all_rules,
    get_rule,
    register,
)
from behave_doctor.rules.base import RuleContext, run_rules


def _context(config: DoctorConfig | None = None) -> RuleContext:
    return RuleContext(
        project=Project(),
        step_definitions=[],
        dependency_graph=DependencyGraph(),
        config=config or DoctorConfig(),
    )


class _DummyA(Rule):
    id = "BDX01"
    name = "dummy-a"
    severity = Severity.ERROR
    category = Category.STRUCTURE
    description = "dummy a"

    def check(self, context: RuleContext) -> list[Diagnostic]:
        return [
            Diagnostic(
                rule_id=self.id,
                rule_name=self.name,
                severity=self.severity,
                category=self.category,
                message="a",
            )
        ]


class _DummyB(Rule):
    id = "BDX02"
    name = "dummy-b"
    severity = Severity.WARNING
    category = Category.QUALITY
    description = "dummy b"

    def check(self, context: RuleContext) -> list[Diagnostic]:
        return [
            Diagnostic(
                rule_id=self.id,
                rule_name=self.name,
                severity=self.severity,
                category=self.category,
                message="b",
            )
        ]


def test_rule_is_abstract() -> None:
    try:
        Rule()  # type: ignore[abstract]
    except TypeError:
        pass
    else:
        raise AssertionError("Rule should be abstract")


def test_run_rules_concatenates_diagnostics() -> None:
    diagnostics = run_rules(_context(), [_DummyA(), _DummyB()])
    assert len(diagnostics) == 2
    assert {d.rule_id for d in diagnostics} == {"BDX01", "BDX02"}


def test_run_rules_filters_by_rule_ids() -> None:
    diagnostics = run_rules(_context(), [_DummyA(), _DummyB()], rule_ids=["BDX01"])
    assert len(diagnostics) == 1
    assert diagnostics[0].rule_id == "BDX01"


def test_run_rules_excludes_by_exclude_ids() -> None:
    diagnostics = run_rules(_context(), [_DummyA(), _DummyB()], exclude_ids=["BDX01"])
    assert len(diagnostics) == 1
    assert diagnostics[0].rule_id == "BDX02"


def test_run_rules_skips_disabled_rules() -> None:
    config = DoctorConfig(rules={"BDX01": {"enabled": False}})
    diagnostics = run_rules(_context(config), [_DummyA(), _DummyB()])
    assert len(diagnostics) == 1
    assert diagnostics[0].rule_id == "BDX02"


def test_run_rules_treats_bool_overrides_as_enabled_flag() -> None:
    config = DoctorConfig(rules={"BDX01": False, "BDX02": True})
    diagnostics = run_rules(_context(config), [_DummyA(), _DummyB()])
    assert len(diagnostics) == 1
    assert diagnostics[0].rule_id == "BDX02"


def test_run_rules_ignores_invalid_override_types() -> None:
    config = DoctorConfig(rules={"BDX01": [1, 2, 3]})
    diagnostics = run_rules(_context(config), [_DummyA(), _DummyB()])
    assert len(diagnostics) == 2


def test_registry_register_and_get() -> None:
    clear_registry()
    register(_DummyA)
    assert get_rule("BDX01") is not None
    assert get_rule("BDX01").id == "BDX01"  # type: ignore[union-attr]
    assert get_rule("missing") is None


def test_registry_get_all_rules_returns_instances() -> None:
    clear_registry()
    register(_DummyA)
    register(_DummyB)
    rules = get_all_rules()
    ids = {r.id for r in rules}
    assert ids == {"BDX01", "BDX02"}
    assert all(isinstance(r, Rule) for r in rules)
    clear_registry()

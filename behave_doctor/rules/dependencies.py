"""Dependency rules (BD501-503) — import and module analysis."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from behave_doctor.graph.cycles import detect_cycles
from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Category, Severity
from behave_doctor.rules import register
from behave_doctor.rules.base import Rule, RuleContext


@register
class CircularDependency(Rule):
    """BD501: circular import dependencies between step modules."""

    id = "BD501"
    name = "circular-dependency"
    severity = Severity.ERROR
    category = Category.DEPENDENCY
    description = "Circular import dependency between step modules."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        cycles = detect_cycles(context.dependency_graph.module_imports)
        return [
            Diagnostic(
                rule_id=self.id,
                rule_name=self.name,
                severity=self.severity,
                category=self.category,
                message=f"Circular dependency: {' -> '.join(cycle)}",
                metadata={"cycle": cycle},
            )
            for cycle in cycles
        ]


@register
class UnusedImport(Rule):
    """BD502: imports in step modules that are never referenced in the file body."""

    id = "BD502"
    name = "unused-import"
    severity = Severity.WARNING
    category = Category.DEPENDENCY
    description = "Import in step module not used."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        seen_files: set[Path] = set()
        for definition in context.step_definitions:
            if definition.file in seen_files:
                continue
            seen_files.add(definition.file)
            diagnostics.extend(self._check_file(definition.file))
        return diagnostics

    def _check_file(self, file: Path) -> list[Diagnostic]:
        try:
            source = file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file))
        except (SyntaxError, OSError):
            return []

        imports: list[tuple[str, int, str]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    local = alias.asname or alias.name.split(".")[0]
                    imports.append((local, node.lineno, local))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    local = alias.asname or alias.name
                    imports.append((local, node.lineno, local))

        # Collect all Name references in the file body.
        used: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used.add(node.id)
            elif isinstance(node, ast.Attribute):
                root: ast.expr = node
                while isinstance(root, ast.Attribute):
                    root = root.value
                if isinstance(root, ast.Name):
                    used.add(root.id)

        diagnostics: list[Diagnostic] = []
        for local, lineno, _name in imports:
            if local not in used:
                diagnostics.append(
                    Diagnostic(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=self.severity,
                        category=self.category,
                        message=f'Unused import "{local}" in {file.name}',
                        file=file,
                        line=lineno,
                        metadata={"import": local},
                    )
                )
        return diagnostics


@register
class MissingStepModule(Rule):
    """BD503: feature steps with no matching definition, suggesting missing modules."""

    id = "BD503"
    name = "missing-step-module"
    severity = Severity.ERROR
    category = Category.DEPENDENCY
    description = "Feature references steps from a non-existent or empty module."

    def check(self, context: RuleContext) -> list[Diagnostic]:
        undefined = [m for m in context.dependency_graph.step_matches if m.step_definition is None]
        if not undefined:
            return []

        # If no step definitions exist at all, report the steps directory issue.
        if not context.step_definitions:
            return [
                Diagnostic(
                    rule_id=self.id,
                    rule_name=self.name,
                    severity=self.severity,
                    category=self.category,
                    message=(
                        f"{len(undefined)} undefined step(s) and no step "
                        f"definitions found — the steps directory is empty or missing"
                    ),
                    metadata={"undefined_count": len(undefined)},
                )
            ]

        # Otherwise report undefined steps as potentially from missing modules.
        return [
            Diagnostic(
                rule_id=self.id,
                rule_name=self.name,
                severity=self.severity,
                category=self.category,
                message=(
                    f'Undefined step "{m.step.full_text}" may reference a missing step module'
                ),
                file=_location_path(m.step.location),
                line=m.step.location.line or None,
                metadata={"step": m.step.name},
            )
            for m in undefined
        ]


def _location_path(location: Any) -> Path | None:
    """Return a Path for a behave-model location, or ``None``."""
    filename = getattr(location, "filename", "") or ""
    return Path(filename) if filename else None

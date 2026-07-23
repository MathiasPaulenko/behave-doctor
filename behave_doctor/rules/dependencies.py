"""Dependency rules (BD501-503) — import and module analysis."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from behave_doctor.graph.cycles import detect_cycles
from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Category, Severity
from behave_doctor.rules import register
from behave_doctor.rules.base import Rule, RuleContext

# Regex to extract Python identifiers from string annotations.
_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


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
            source = file.read_text(encoding="utf-8-sig")
            tree = ast.parse(source, filename=str(file), type_comments=True)
        except (SyntaxError, OSError, UnicodeError):
            return []

        imports: list[tuple[str, int]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    local = alias.asname or alias.name.split(".")[0]
                    imports.append((local, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                # Skip __future__ imports — they are always "used" by the interpreter.
                if node.module == "__future__":
                    continue
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    local = alias.asname or alias.name
                    imports.append((local, node.lineno))

        # Collect all Name references and string annotation names in the file body.
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
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                # String annotations (forward references) may reference imports.
                # Extract identifiers so "List[int]" yields "List" and "int".
                words = set(_IDENTIFIER_RE.findall(node.value))
                for local, _ in imports:
                    if local in words:
                        used.add(local)
            # Check type_comment attributes (from `# type: ...` comments).
            tc = getattr(node, "type_comment", None)
            if tc and isinstance(tc, str):
                words = set(_IDENTIFIER_RE.findall(tc))
                for local, _ in imports:
                    if local in words:
                        used.add(local)

        diagnostics: list[Diagnostic] = []
        for local, lineno in imports:
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
        # When definitions exist but some steps don't match, BD302 already
        # reports those — BD503 only fires for the "no definitions at all" case.
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

        return []

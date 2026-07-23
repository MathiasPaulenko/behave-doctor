"""DOT format export for the dependency graph."""

from __future__ import annotations

from behave_doctor.model.dependency_graph import DependencyGraph


def _escape_dot_string(s: str) -> str:
    """Escape a string for use in a DOT double-quoted identifier."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def to_dot(graph: DependencyGraph) -> str:
    """Render a ``DependencyGraph``'s module import graph in DOT format."""
    lines = ["digraph behave_doctor {"]
    for module in sorted(graph.module_imports):
        lines.append(f'    "{_escape_dot_string(module)}";')
    for module in sorted(graph.module_imports):
        for target in sorted(graph.module_imports[module]):
            lines.append(f'    "{_escape_dot_string(module)}" -> "{_escape_dot_string(target)}";')
    lines.append("}")
    return "\n".join(lines)

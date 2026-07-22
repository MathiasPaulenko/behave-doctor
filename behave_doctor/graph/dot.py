"""DOT format export for the dependency graph."""

from __future__ import annotations

from behave_doctor.model.dependency_graph import DependencyGraph


def to_dot(graph: DependencyGraph) -> str:
    """Render a ``DependencyGraph``'s module import graph in DOT format."""
    lines = ["digraph behave_doctor {"]
    for module in sorted(graph.module_imports):
        lines.append(f'    "{module}";')
    for module in sorted(graph.module_imports):
        for target in sorted(graph.module_imports[module]):
            lines.append(f'    "{module}" -> "{target}";')
    lines.append("}")
    return "\n".join(lines)

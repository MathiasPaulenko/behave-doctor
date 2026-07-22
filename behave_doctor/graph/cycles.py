"""Circular dependency detection via DFS on the module import graph."""

from __future__ import annotations


def detect_cycles(module_imports: dict[str, set[str]]) -> list[list[str]]:
    """Find all cycles in a directed module import graph using DFS.

    Args:
        module_imports: Mapping of module name → set of imported module names.

    Returns:
        A list of cycles, each represented as a list of module names forming
        the cycle path (e.g. ``["a", "b", "c", "a"]``). Each distinct cycle is
        reported once. Self-imports (``a → a``) are reported as ``["a", "a"]``.
    """
    cycles: list[list[str]] = []
    seen_cycle_keys: set[tuple[str, ...]] = set()

    # Build the full set of nodes (modules + any imported modules not keys).
    nodes: set[str] = set(module_imports.keys())
    for targets in module_imports.values():
        nodes.update(targets)

    visited: set[str] = set()
    stack: list[str] = []
    on_stack: set[str] = set()

    def _dfs(node: str) -> None:
        stack.append(node)
        on_stack.add(node)
        for neighbour in sorted(module_imports.get(node, set())):
            if neighbour == node:
                _record([node, node])
                continue
            if neighbour in on_stack:
                # Found a cycle: slice the stack from the neighbour to current.
                idx = stack.index(neighbour)
                _record(stack[idx:] + [neighbour])
            elif neighbour not in visited and neighbour in module_imports:
                _dfs(neighbour)
        on_stack.discard(node)
        stack.pop()
        visited.add(node)

    def _record(cycle: list[str]) -> None:
        # Normalize the cycle to a canonical rotation for deduplication.
        key = _canonical_cycle_key(cycle)
        if key in seen_cycle_keys:
            return
        seen_cycle_keys.add(key)
        cycles.append(cycle)

    for node in sorted(nodes):
        if node not in visited:
            _dfs(node)

    return cycles


def _canonical_cycle_key(cycle: list[str]) -> tuple[str, ...]:
    """Return a rotation-independent key for a cycle for deduplication.

    Self-cycles (``[a, a]``) are keyed directly. For longer cycles, the key is
    the minimal rotation of the cycle nodes (excluding the repeated closing node).
    """
    if len(cycle) <= 2:
        return tuple(cycle)
    core = cycle[:-1]
    rotations = [tuple(core[i:] + core[:i]) for i in range(len(core))]
    return min(rotations)

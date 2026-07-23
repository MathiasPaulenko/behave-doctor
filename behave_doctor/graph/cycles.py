"""Circular dependency detection via DFS on the module import graph."""

from __future__ import annotations

from collections import deque


def detect_cycles(module_imports: dict[str, set[str]]) -> list[list[str]]:
    """Find all cycles in a directed module import graph using iterative DFS.

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
    on_stack: set[str] = set()

    def _record(cycle: list[str]) -> None:
        key = _canonical_cycle_key(cycle)
        if key in seen_cycle_keys:
            return
        seen_cycle_keys.add(key)
        cycles.append(cycle)

    for start in sorted(nodes):
        if start in visited:
            continue
        # Iterative DFS with an explicit stack of (node, iterator) pairs.
        stack: list[str] = []
        iters: list[deque[str]] = []
        current: str | None = start
        neighbours: deque[str] = deque(sorted(module_imports.get(start, set())))

        while True:
            if current is not None:
                stack.append(current)
                on_stack.add(current)
                iters.append(neighbours)
                current = None

            # Try to advance the top iterator.
            advanced = False
            while iters:
                top_iter = iters[-1]
                if not top_iter:
                    # Backtrack: pop this node.
                    done = stack.pop()
                    on_stack.discard(done)
                    iters.pop()
                    visited.add(done)
                    continue
                neighbour = top_iter.popleft()
                if neighbour == stack[-1]:
                    _record([stack[-1], stack[-1]])
                    continue
                if neighbour in on_stack:
                    idx = stack.index(neighbour)
                    _record(stack[idx:] + [neighbour])
                    continue
                if neighbour not in visited and neighbour in module_imports:
                    current = neighbour
                    neighbours = deque(sorted(module_imports.get(neighbour, set())))
                    advanced = True
                    break
                # Skip: already visited or not in graph.

            if not advanced:
                break

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

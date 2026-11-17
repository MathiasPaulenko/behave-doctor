from __future__ import annotations

from pathlib import Path

from behave_doctor.graph.cycles import detect_cycles


def test_no_cycles() -> None:
    graph = {"a": {"b"}, "b": {"c"}, "c": set()}
    assert detect_cycles(graph) == []


def test_simple_cycle() -> None:
    graph = {"a": {"b"}, "b": {"a"}}
    cycles = detect_cycles(graph)
    assert len(cycles) == 1
    cycle = cycles[0]
    assert cycle[0] == cycle[-1]
    assert set(cycle) == {"a", "b"}


def test_self_cycle() -> None:
    graph = {"a": {"a"}}
    cycles = detect_cycles(graph)
    assert len(cycles) == 1
    assert cycles[0] == ["a", "a"]


def test_multiple_independent_cycles() -> None:
    graph = {"a": {"b"}, "b": {"a"}, "c": {"d"}, "d": {"c"}}
    cycles = detect_cycles(graph)
    assert len(cycles) == 2


def test_complex_graph() -> None:
    graph = {"a": {"b"}, "b": {"c"}, "c": {"a"}, "d": {"e"}, "e": set()}
    cycles = detect_cycles(graph)
    assert len(cycles) == 1
    assert set(cycles[0]) == {"a", "b", "c"}


def test_cycle_not_duplicated() -> None:
    graph = {"a": {"b"}, "b": {"c"}, "c": {"a"}}
    cycles = detect_cycles(graph)
    assert len(cycles) == 1


def test_deep_chain_no_recursion_limit() -> None:
    """A very deep chain must not hit Python's recursion limit."""
    n = 5000
    graph = {f"m{i}": {f"m{i + 1}"} for i in range(n)}
    graph[f"m{n}"] = set()
    # Should complete without RecursionError.
    cycles = detect_cycles(graph)
    assert cycles == []


def test_deep_chain_with_cycle_at_end() -> None:
    """A deep chain with a cycle at the end is detected without recursion limit."""
    n = 5000
    graph = {f"m{i}": {f"m{i + 1}"} for i in range(n)}
    graph[f"m{n}"] = {"m0"}  # cycle back to start
    cycles = detect_cycles(graph)
    assert len(cycles) == 1


def test_relative_import_from_package_init_resolves_inside_package(tmp_path: Path) -> None:
    """``from . import helpers`` inside ``pkg/__init__.py`` resolves to
    ``pkg.helpers``, not bare ``helpers`` — the package init's anchor is the
    package itself."""
    from behave_doctor.graph.builder import _extract_module_imports

    pkg = tmp_path / "pkg"
    pkg.mkdir()
    init = pkg / "__init__.py"
    init.write_text("from . import helpers\n", encoding="utf-8")
    assert _extract_module_imports(init, "pkg") == {"pkg.helpers"}
    # And one level up escapes to the parent package.
    init.write_text("from .. import top\n", encoding="utf-8")
    assert _extract_module_imports(init, "pkg") == {"top"}

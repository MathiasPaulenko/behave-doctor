from __future__ import annotations

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

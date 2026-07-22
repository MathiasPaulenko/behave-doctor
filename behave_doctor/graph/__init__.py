"""Graph package — dependency graph building and analysis."""

from __future__ import annotations

from behave_doctor.graph.builder import build_graph
from behave_doctor.graph.cycles import detect_cycles
from behave_doctor.graph.dot import to_dot

__all__ = ["build_graph", "detect_cycles", "to_dot"]

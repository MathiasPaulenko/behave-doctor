# Architecture

This page describes the internal design of behave-doctor — how the
modules fit together, the data flow, and the key abstractions.

## High-level data flow

```text
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌────────────┐
│  .feature   │────▶│  Project     │     │  Step       │     │  Dependency│
│  files      │     │  Scanner     │     │  Scanner    │     │  Graph     │
│  .py steps  │     │  (behave-    │     │  (AST)      │────▶│  Builder   │
└─────────────┘     │  model)      │     │             │     │            │
                    └──────┬───────┘     └──────┬──────┘     └─────┬──────┘
                           │                    │                  │
                           ▼                    ▼                  ▼
                    ┌──────────────────────────────────────────────────┐
                    │              Rule Engine                          │
                    │  18 rules visit the project, step defs, and graph │
                    └──────────────────────┬───────────────────────────┘
                                           │
                                           ▼
                                    ┌──────────────┐
                                    │  Reporters   │
                                    │  text/json/  │
                                    │  sarif       │
                                    └──────────────┘
```

## Module structure

```text
behave_doctor/
├── __init__.py              # Public API: scan_project, ProjectReport, etc.
├── __main__.py              # python -m behave_doctor entry point
├── core.py                  # Orchestrator: scan → match → analyze → report
├── model/                   # Core dataclasses (no external deps)
│   ├── __init__.py          #   Public re-exports
│   ├── config.py            #   DoctorConfig
│   ├── dependency_graph.py  #   DependencyGraph
│   ├── diagnostic.py        #   Diagnostic
│   ├── enums.py             #   Severity, Category enums
│   ├── location.py          #   location_path() helper
│   ├── project_report.py    #   ProjectReport, ProjectStatistics
│   ├── step_definition.py   #   StepDefinition
│   └── step_match.py        #   StepMatch
├── scanner/                 # Static analysis (no execution)
│   ├── __init__.py
│   ├── project_scanner.py   #   Parses .feature files via behave-model
│   └── step_scanner.py      #   Parses .py files via AST
├── graph/                   # Dependency graph
│   ├── __init__.py
│   ├── builder.py           #   Builds step match + import graph
│   ├── cycles.py            #   DFS cycle detection
│   └── dot.py               #   DOT format output
├── rules/                   # Diagnostic rules
│   ├── __init__.py          #   Rule registry with lazy imports
│   ├── base.py              #   Rule ABC, RuleContext, run_rules()
│   ├── structure.py         #   BD101-104
│   ├── quality.py           #   BD201-204
│   ├── coverage.py          #   BD301-304
│   ├── complexity.py        #   BD401-403
│   └── dependencies.py      #   BD501-503
├── reporters/               # Output formatters
│   ├── __init__.py
│   ├── text.py              #   Human-readable with ANSI colors
│   ├── json_reporter.py     #   Structured JSON
│   └── sarif.py             #   SARIF 2.1.0
└── cli/                     # Command-line interface
    ├── __init__.py
    ├── app.py               #   Typer-based CLI
    └── formatters.py        #   Console output helpers
```

## Key abstractions

### `StepDefinition`

Represents a single `@given`/`@when`/`@then` decorator found in a Python
file. Contains the pattern string, matcher type, file path, line number,
and the AST node.

### `StepMatch`

The result of matching a feature step against all step definitions.
Contains the matched definition (or `None` if undefined), whether the match
is ambiguous, and the extracted parameters.

### `DependencyGraph`

A directed graph of module imports. Nodes are Python modules under
`features/steps/`. Edges represent `import` statements. Used by BD501
(circular dependency detection) and the `graph` command.

### `Diagnostic`

A single finding produced by a rule. Contains the rule ID, severity,
category, message, file, line, optional suggestion, and optional metadata.

### `ProjectReport`

The final output of a scan. Contains all diagnostics, statistics, the exit
code, and the scan duration.

### `Rule` (ABC)

The abstract base class for all rules. Each rule implements a `check()`
method that receives a `RuleContext` (containing the project, step
definitions, dependency graph, and config) and yields `Diagnostic` objects.

### `RuleContext`

The input passed to each rule. Contains:

- `project` — the parsed Behave project (features, scenarios, steps).
- `step_definitions` — all step definitions found.
- `dependency_graph` — the dependency graph.
- `config` — the merged configuration.

## Scan pipeline

The `core.py` orchestrator runs the following steps:

1. **Load config** — `DoctorConfig.from_pyproject()` reads
   `[tool.behave-doctor]` from `pyproject.toml`, with CLI overrides applied
   on top.
2. **Scan project** — `scan_features()` uses `behave-model` to parse
   `.feature` files into a project AST.
3. **Scan steps** — `StepScanner` uses Python's `ast` module to extract
   `@given`/`@when`/`@then` decorators from `.py` files without importing
   them.
4. **Build graph** — `GraphBuilder` matches feature steps against step
   definitions and records module imports.
5. **Run rules** — `run_rules()` instantiates all enabled rules and calls
   each rule's `check()` method with a `RuleContext`.
6. **Filter** — Diagnostics are filtered by severity and rule selection.
7. **Report** — The selected reporter formats the diagnostics and writes
   them to stdout or a file.

## Design principles

- **No execution** — behave-doctor never imports or executes step modules.
  All analysis is static (AST-based).
- **No side effects** — scanning a project produces no writes, no network
  calls, no state changes.
- **Minimal dependencies** — beyond `behave-model` (parsing) and `typer`
  (CLI), behave-doctor has no runtime dependencies. It uses only the Python
  standard library for everything else.
- **Stable rule IDs** — Rule IDs (BD101-503) are stable and will never
  change, making them safe for CI configs and `pyproject.toml` overrides.
- **Lazy rule loading** — Rules are loaded lazily via the registry, so only
  enabled rules are imported.
- **Fully typed** — The entire codebase passes `mypy --strict` with no
  errors. All public APIs have type hints.

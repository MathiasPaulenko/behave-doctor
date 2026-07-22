# Dependency Rules (BD501-503)

Analyze import dependencies between step modules.

## BD501 — circular-dependency

Detects circular import dependencies between step modules using DFS.
Circular imports cause `ImportError` at runtime in Python.

| Attribute   | Value          |
| ----------- | -------------- |
| Severity    | error          |
| Category    | Dependency     |
| Configurable| No             |

## BD502 — unused-import

Detects imports in step modules that are never referenced in the file body.
Uses AST analysis — does not execute the module.

| Attribute   | Value          |
| ----------- | -------------- |
| Severity    | warning        |
| Category    | Dependency     |
| Configurable| No             |

## BD503 — missing-step-module

Detects feature steps with no matching definition and reports whether the
steps directory is empty/missing or whether specific steps lack definitions.

| Attribute   | Value          |
| ----------- | -------------- |
| Severity    | error          |
| Category    | Dependency     |
| Configurable| No             |

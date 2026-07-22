# behave-doctor

**Static analysis and diagnostics for Behave BDD suites.**

behave-doctor inspects your Behave `.feature` files and Python step
definitions **without executing them**, surfacing issues like unused step
definitions, undefined steps, oversized features, inconsistent tags, and
circular import dependencies.

## Why?

Behave suites grow organically. Over time, step definitions drift from
feature files, tags accumulate without consistency, and features balloon
in size. behave-doctor catches these problems early — in CI, in pre-commit
hooks, or on the command line — before they slow down your test suite or
confuse your team.

## Features

- **18 diagnostic rules** across 5 categories (structure, quality, coverage,
  complexity, dependencies).
- **3 output formats**: human-readable text, JSON, and SARIF 2.1.0 for
  GitHub Code Scanning.
- **Zero runtime dependencies** beyond `behave-model` — pure Python,
  fully typed, mypy --strict clean.
- **Configurable** via `[tool.behave-doctor]` in `pyproject.toml`.
- **Python API** for embedding in custom tooling.

## Quick example

```bash
behave-doctor scan path/to/project --format text
```

```text
Scanning path/to/project...
Found 12 features, 47 scenarios, 213 steps, 89 step definitions.

BD301  WARNING   Unused step definition: "the user clicks submit"  (features/steps/auth.py:42)
BD302  ERROR      Undefined step: "Given the database is seeded"   (features/login.feature:18)

1 errors, 1 warnings in 0.42s
```

## Next steps

- [Installation](installation.md)
- [Quick Start](quickstart.md)
- [CLI reference](cli.md)
- [Rules](rules/index.md)

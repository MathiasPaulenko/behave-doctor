# behave-doctor

**Static analysis and diagnostics for Behave BDD suites.**

behave-doctor inspects your Behave `.feature` files and Python step
definitions **without executing them**, surfacing issues like unused step
definitions, undefined steps, oversized features, inconsistent tags, and
circular import dependencies — before they slow down your test suite or
confuse your team.

---

## Why behave-doctor?

Behave suites grow organically. Over time:

- **Step definitions drift** from feature files — unused definitions pile up,
  undefined steps cause runtime failures.
- **Tags accumulate** without consistency — `@SmokeTest`, `@smoke_test`, and
  `@smoke-test` all coexist, breaking tag filters.
- **Features balloon** in size — 50-scenario features become impossible to
  review or maintain.
- **Circular imports** between step modules cause `ImportError` at runtime.
- **No visibility** into suite health — how many steps are defined? How many
  are actually used? How complex are your scenarios?

behave-doctor catches all of these **statically** — no test execution
required, no side effects, no network calls. It parses `.feature` files with
[`behave-model`](https://pypi.org/project/behave-model/) and analyzes Python
step definitions with the AST — never importing or executing them.

## Features

- **18 diagnostic rules** across 5 categories:
  - **Structure** (BD101-104) — feature, scenario, step, and tag counts.
  - **Quality** (BD201-204) — duplicate definitions, missing tags, oversized
    features, inconsistent tag casing.
  - **Coverage** (BD301-304) — unused step definitions, undefined steps,
    unused tags, orphan scenarios.
  - **Complexity** (BD401-403) — scenario step count, step parameter count,
    feature file size.
  - **Dependencies** (BD501-503) — circular imports, unused imports, missing
    step modules.
- **3 output formats**: human-readable text (with ANSI colors), JSON, and
  SARIF 2.1.0 for GitHub Code Scanning.
- **Zero runtime dependencies** beyond `behave-model` — pure Python, fully
  typed, `mypy --strict` clean, `ruff` clean.
- **Configurable** via `[tool.behave-doctor]` in `pyproject.toml` — per-rule
  thresholds, enable/disable, severity filtering, tag exclusions.
- **Python API** for embedding in custom tooling, IDE plugins, or CI
  integrations.
- **CLI** with `scan`, `list-rules`, `explain`, `stats`, and `graph`
  subcommands.
- **95% test coverage** — 128 tests across unit and integration suites.

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

Exit codes: `0` = clean, `1` = issues found, `2` = scan error.

## How it works

behave-doctor never executes your code. It works in four phases:

1. **Scan** — `behave-model` parses `.feature` files into an AST. The step
   scanner uses Python's `ast` module to extract `@given`/`@when`/`@then`
   decorators from step modules — without importing them.
2. **Match** — Each feature step is matched against step definitions using
   the matcher type (`re`, `parse`, `cfparse`, or `behave`'s default). The
   dependency graph records which definitions are used and which are not.
3. **Analyze** — 18 rules visit the project, step definitions, and
   dependency graph to produce diagnostics.
4. **Report** — Diagnostics are formatted as text, JSON, or SARIF and written
   to stdout or a file.

## Next steps

- [Installation](installation.md) — get behave-doctor running in 30 seconds.
- [Quick Start](quickstart.md) — scan a project, filter rules, explore stats.
- [CLI Reference](cli.md) — every command, flag, and option.
- [Rules](rules/index.md) — detailed documentation for all 18 rules.
- [Configuration](configuration.md) — customize thresholds and behavior.
- [Reporters](reporters.md) — text, JSON, and SARIF output formats.
- [Python API](python-api.md) — use behave-doctor as a library.
- [CI/CD](ci-cd.md) — integrate with GitHub Actions, pre-commit, and more.
- [Architecture](architecture.md) — internal design and data flow.
- [FAQ](faq.md) — common questions and troubleshooting.

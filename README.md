# behave-doctor

**Lint, diagnose, and analyze the impact of changes in your Behave BDD test suites — without running a single test.**

[![CI](https://github.com/MathiasPaulenko/behave-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/MathiasPaulenko/behave-doctor/actions/workflows/ci.yml)
[![Docs](https://github.com/MathiasPaulenko/behave-doctor/actions/workflows/docs.yml/badge.svg)](https://mathiaspaulenko.github.io/behave-doctor/)
[![PyPI](https://img.shields.io/pypi/v/behave-doctor)](https://pypi.org/project/behave-doctor/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen)](https://github.com/MathiasPaulenko/behave-doctor)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000)](https://docs.astral.sh/ruff/)
[![Types: mypy](https://img.shields.io/badge/types-mypy%20strict-blue)](https://mypy-lang.org/)

behave-doctor inspects your Behave `.feature` files and Python step
definitions **without executing them**, surfacing issues like unused step
definitions, undefined steps, oversized features, inconsistent tags, and
circular import dependencies — before they slow down your test suite or
confuse your team.

It also includes an **impact analysis** command: tell it which files you
changed, and it tells you exactly which scenarios are affected — so you can
run only the tests that matter instead of the full suite.

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

- **19 diagnostic rules** across 5 categories:
  - **Structure** (BD101-104) — feature, scenario, step, and tag counts.
  - **Quality** (BD201-205) — duplicate definitions, missing tags, oversized
    features, inconsistent tag casing, ambiguous step matches.
  - **Coverage** (BD301-304) — unused step definitions, undefined steps,
    unused tags, orphan scenarios.
  - **Complexity** (BD401-403) — scenario step count, step parameter count,
    feature file size.
  - **Dependencies** (BD501-503) — circular imports, unused imports, missing
    step modules.
- **Impact analysis** — given a list of changed `.py` or `.feature` files,
  determines which scenarios are affected and outputs names suitable for
  `behave --name`, JSON, or human-readable text.
- **4 output formats**: human-readable text (with ANSI colors), JSON, SARIF
  2.1.0 for GitHub Code Scanning, and `names` for impact analysis.
- **Minimal runtime dependencies** — only `behave-model` (parsing) and
  `typer` (CLI). Pure Python, fully typed, `mypy --strict` clean, `ruff`
  clean.
- **Configurable** via `[tool.behave-doctor]` in `pyproject.toml` — per-rule
  thresholds, enable/disable, severity filtering, tag exclusions.
- **Python API** for embedding in custom tooling, IDE plugins, or CI
  integrations.
- **CLI** with `scan`, `impact`, `list-rules`, `explain`, `stats`, and
  `graph` subcommands.
- **95% test coverage** — 270 tests across unit and integration suites.

## Installation

```bash
pip install behave-doctor
```

**Requirements**: Python 3.11+. The `behave-model` package (for `.feature`
parsing) and `typer` (for the CLI) are installed automatically.

## Quick start

```bash
behave-doctor scan .
```

```text
Scanning . ...
Found 12 features, 47 scenarios, 213 steps, 89 step definitions.

BD101  INFO      12 features found
BD102  INFO      47 scenarios found
BD103  INFO      213 steps found
BD201  ERROR     Duplicate step definition for pattern 'the user is logged in' in: ...
BD301  WARNING   Unused step definition: "the user clicks submit"  (features/steps/auth.py:42)
BD302  ERROR     Undefined step: "Given the database is seeded"  (features/login.feature:18)

3 errors, 1 warning in 0.42s
```

Exit codes: `0` = clean, `1` = issues found, `2` = scan error.

## Impact analysis

Tell behave-doctor which files you changed, and it tells you which scenarios
are affected — so you can run only the tests that matter.

```bash
# Which scenarios are affected by changes to login_steps.py?
behave-doctor impact . --changed-files features/steps/login_steps.py
```

```text
Impact analysis: 1 changed files

Changed files:
  - /path/to/features/steps/login_steps.py (4 step definitions)

Affected scenarios (4):
  /path/to/features/login.feature:3  Successful login
  /path/to/features/login.feature:11  Failed login
  /path/to/features/search.feature:5  Search by keyword
  /path/to/features/search.feature:12  Search with filter

Affected features (2):
  /path/to/features/login.feature
  /path/to/features/search.feature
```

Get scenario names for `behave --name`:

```bash
behave-doctor impact . --changed-files features/steps/login_steps.py --format names
```

```text
Successful login
Failed login
Search by keyword
Search with filter
```

Pipe directly to Behave:

```bash
behave-doctor impact . --changed-files features/steps/login_steps.py --format names | xargs -I{} behave --name "{}"
```

JSON output for CI integration:

```bash
behave-doctor impact . --changed-files features/steps/login_steps.py --format json
```

Impact analysis understands **Background steps** — if a changed step
definition is used in a feature's Background, all scenarios in that feature
are affected.

## Rules

| ID    | Name                        | Severity | Category     | Configurable                                       |
| ----- | --------------------------- | -------- | ------------ | -------------------------------------------------- |
| BD101 | feature-count               | info     | Structure    | No                                                 |
| BD102 | scenario-count              | info     | Structure    | No                                                 |
| BD103 | step-count                  | info     | Structure    | No                                                 |
| BD104 | tag-coverage                | info     | Structure    | No                                                 |
| BD201 | duplicate-step-defs         | error    | Quality      | No                                                 |
| BD202 | scenario-no-tags            | warning  | Quality      | No                                                 |
| BD203 | feature-too-many-scenarios  | warning  | Quality      | `max_scenarios` (default 20)                       |
| BD204 | inconsistent-tag-casing     | warning  | Quality      | No                                                 |
| BD205 | ambiguous-step-match        | error    | Quality      | No                                                 |
| BD301 | unused-step-def             | warning  | Coverage     | No                                                 |
| BD302 | undefined-step              | error    | Coverage     | No                                                 |
| BD303 | unused-tag                  | info     | Coverage     | `exclude_tags` (global)                            |
| BD304 | orphan-scenario             | warning  | Coverage     | No                                                 |
| BD401 | scenario-too-many-steps     | warning  | Complexity   | `max_steps` (default 10)                           |
| BD402 | step-too-many-params        | warning  | Complexity   | `max_params` (default 5)                           |
| BD403 | feature-too-large           | warning  | Complexity   | `max_lines` (default 300)                          |
| BD501 | circular-dependency         | error    | Dependency   | No                                                 |
| BD502 | unused-import               | warning  | Dependency   | No                                                 |
| BD503 | missing-step-module         | error    | Dependency   | No                                                 |

Explore rules from the CLI:

```bash
behave-doctor list-rules          # list all 19 rules
behave-doctor explain BD301       # explain a specific rule
```

## Configuration

All options have sensible defaults — configuration is optional.

```toml
# pyproject.toml
[tool.behave-doctor]
features_dir = "features/"          # default: features/
steps_dir = "features/steps/"       # default: features/steps/
min_severity = "info"               # default: info (show errors, warnings, and info)
exclude_tags = ["@smoke", "@wip"]   # tags excluded from BD303

[tool.behave-doctor.rules.BD101]    # disable a rule
enabled = false

[tool.behave-doctor.rules.BD203]    # adjust a threshold
max_scenarios = 15

[tool.behave-doctor.rules.BD401]
max_steps = 8

[tool.behave-doctor.rules.BD402]
max_params = 3

[tool.behave-doctor.rules.BD403]
max_lines = 200
```

CLI flags override config file values:

```bash
behave-doctor scan . --severity error --rules BD301,BD302 --exclude-rules BD101
```

## Output formats

```bash
# Human-readable (default, with ANSI colors)
behave-doctor scan . --format text

# JSON for CI integration and custom tooling
behave-doctor scan . --format json

# SARIF 2.1.0 for GitHub Code Scanning
behave-doctor scan . --format sarif -o behave-doctor.sarif
```

## Python API

### Scanning

```python
from behave_doctor import scan_project, Severity

report = scan_project("path/to/project")

# Filter diagnostics by severity
errors = [d for d in report.diagnostics if d.severity is Severity.ERROR]
for d in errors:
    print(f"{d.rule_id}: {d.message} at {d.file}:{d.line}")

# Access statistics
stats = report.statistics
print(f"{stats.features} features, {stats.scenarios} scenarios")
print(f"{stats.unused_step_definitions} unused, {stats.undefined_steps} undefined")

# Exit code: 0 = clean, 1 = issues found
print(f"Exit code: {report.exit_code}")
```

Custom configuration:

```python
from behave_doctor import scan_project, DoctorConfig, Severity

config = DoctorConfig(
    features_dir="my_features",
    steps_dir="my_steps",
    min_severity=Severity.WARNING,
    rules={"BD101": {"enabled": False}, "BD401": {"max_steps": 5}},
)
report = scan_project("path/to/project", config=config)
```

### Impact analysis

```python
from behave_doctor import impact_analysis, format_impact

result = impact_analysis(
    "path/to/project",
    changed_files=["features/steps/login_steps.py"],
)

# Affected scenario names (suitable for behave --name)
for name in result.scenario_names:
    print(name)

# Summary counts
print(f"{result.summary.scenarios_affected} scenarios affected")
print(f"{result.summary.features_affected} features affected")

# Format as text, JSON, or names
print(format_impact(result, "text"))
print(format_impact(result, "json"))
print(format_impact(result, "names"))
```

## CI/CD

### GitHub Actions (basic lint)

```yaml
- run: pip install behave-doctor
- run: behave-doctor scan . --no-color
```

### GitHub Code Scanning (SARIF)

```yaml
- run: pip install behave-doctor
- run: behave-doctor scan . --format sarif -o behave-doctor.sarif
  continue-on-error: true
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: behave-doctor.sarif
```

### Pre-commit hook

```yaml
repos:
  - repo: https://github.com/MathiasPaulenko/behave-doctor
    rev: v1.3.0
    hooks:
      - id: behave-doctor
        args: ["scan", "--severity", "warning", "--no-color"]
```

## How it works

behave-doctor never executes your code. It works in four phases:

1. **Scan** — `behave-model` parses `.feature` files into an AST. The step
   scanner uses Python's `ast` module to extract `@given`/`@when`/`@then`
   decorators from step modules — without importing them.
2. **Match** — Each feature step is matched against step definitions using
   the matcher type (`re`, `parse`, `cfparse`, or `behave`'s default). The
   dependency graph records which definitions are used and which are not.
3. **Analyze** — 19 rules visit the project, step definitions, and
   dependency graph to produce diagnostics.
4. **Report** — Diagnostics are formatted as text, JSON, or SARIF and written
   to stdout or a file.

## Documentation

Full documentation at **<https://mathiaspaulenko.github.io/behave-doctor/>**:

- [Installation](https://mathiaspaulenko.github.io/behave-doctor/installation/)
- [Quick Start](https://mathiaspaulenko.github.io/behave-doctor/quickstart/)
- [CLI Reference](https://mathiaspaulenko.github.io/behave-doctor/cli/)
- [Rules](https://mathiaspaulenko.github.io/behave-doctor/rules/)
- [Configuration](https://mathiaspaulenko.github.io/behave-doctor/configuration/)
- [Reporters](https://mathiaspaulenko.github.io/behave-doctor/reporters/)
- [Python API](https://mathiaspaulenko.github.io/behave-doctor/python-api/)
- [CI/CD](https://mathiaspaulenko.github.io/behave-doctor/ci-cd/)
- [Architecture](https://mathiaspaulenko.github.io/behave-doctor/architecture/)
- [FAQ](https://mathiaspaulenko.github.io/behave-doctor/faq/)

## Supply chain & trust

- **Trusted Publishing (OIDC)** — releases to PyPI use
  [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) via GitHub
  Actions OIDC. No long-lived API tokens are stored in secrets.
- **Pinned actions** — all GitHub Actions are pinned to specific versions
  (e.g. `@v4`, `@v1.12.4`).
- **Minimal dependencies** — only `behave-model` (parsing) and `typer` (CLI)
  at runtime. No transitive dependency tree to audit.
- **No code execution** — behave-doctor never imports or executes your step
  definitions. It uses Python's `ast` module for static analysis only.
- **`py.typed` marker** — the package ships with inline type hints.
- **Reproducible builds** — `hatchling` build backend with no dynamic metadata.

## Development

```bash
git clone https://github.com/MathiasPaulenko/behave-doctor.git
cd behave-doctor
pip install -e ".[dev]"
pre-commit install
```

| Command             | Description                                  |
| ------------------- | -------------------------------------------- |
| `make help`         | Show all available targets.                  |
| `make dev`          | Install with dev extras.                     |
| `make lint`         | Run `ruff check` + `mypy --strict`.          |
| `make lint-fix`     | Auto-fix lint issues.                        |
| `make format`       | Format the code with `ruff format`.          |
| `make format-check` | Verify formatting without changes.           |
| `make test`         | Run the test suite.                          |
| `make test-cov`     | Run tests with coverage (fail under 90%).    |
| `make check`        | Full pre-commit check (lint + format + test).|
| `make build`        | Build sdist + wheel into `dist/`.            |
| `make docs-serve`   | Serve documentation locally.                 |
| `make clean`        | Remove build artifacts and caches.           |

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

## License

[MIT](LICENSE) — © Mathias Paulenko

## Acknowledgements

- [`behave-model`](https://pypi.org/project/behave-model/) — the `.feature` file
  parser that powers behave-doctor's analysis.
- [`typer`](https://typer.tiangolo.com/) — the CLI framework that makes
  behave-doctor's command-line interface clean and ergonomic.
- [`ruff`](https://docs.astral.sh/ruff/) and
  [`mypy`](https://mypy-lang.org/) — the tools that keep behave-doctor's
  codebase clean and fully typed.

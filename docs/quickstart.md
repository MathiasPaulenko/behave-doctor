# Quick Start

This guide walks you through scanning a Behave project, filtering rules,
exploring statistics, and using the Python API.

## Scan a project

From the root of your Behave project (the directory containing `features/`):

```bash
behave-doctor scan .
```

behave-doctor will:

1. Discover `.feature` files under `features/`.
2. Parse Python step definitions under `features/steps/` using the AST —
   **without importing or executing them**.
3. Build a dependency graph (step matches + module imports).
4. Run all 18 diagnostic rules.
5. Print a human-readable report to stdout.

### What you'll see

```text
Scanning . ...
Found 12 features, 47 scenarios, 213 steps, 89 step definitions.

BD101  INFO      12 features found
BD102  INFO      47 scenarios found
BD103  INFO      213 steps found
BD104  INFO      8 unique tags, 34 total tag usages
BD201  ERROR     Duplicate step definition for pattern 'the user is logged in' in: features/steps/auth.py:10, features/steps/login.py:15
BD301  WARNING   Unused step definition: "the user clicks submit"
      (features/steps/auth.py:42)
BD302  ERROR     Undefined step: "Given the database is seeded"
      (features/login.feature:18)

3 errors, 1 warning in 0.42s
```

### Exit codes

| Code | Meaning                              |
| ---- | ------------------------------------ |
| 0    | No errors or warnings found.         |
| 1    | One or more errors/warnings found.   |
| 2    | Scan failed (missing features dir).  |

## Output formats

```bash
# Human-readable (default, with ANSI colors)
behave-doctor scan . --format text

# JSON for CI integration and custom tooling
behave-doctor scan . --format json

# SARIF 2.1.0 for GitHub Code Scanning
behave-doctor scan . --format sarif -o behave-doctor.sarif
```

See [Reporters](reporters.md) for detailed output examples.

## Filter rules

### Run only specific rules

```bash
behave-doctor scan . --rules BD301,BD302
```

### Exclude rules

```bash
behave-doctor scan . --exclude-rules BD101,BD102,BD103,BD104
```

### Set minimum severity

```bash
# Only show errors
behave-doctor scan . --severity error

# Show errors and warnings
behave-doctor scan . --severity warning

# Show errors, warnings, and info
behave-doctor scan . --severity info
```

Severity hierarchy: `error` > `warning` > `info` > `hint`. The default is
`info` (show errors, warnings, and info).

## Explore rules

### List all available rules

```bash
behave-doctor list-rules
```

```text
BD101  INFO      structure     feature-count  -  Report total feature count.
BD102  INFO      structure     scenario-count  -  Report total scenario count.
...
BD503  ERROR     dependency   missing-step-module  -  Feature references steps from non-existent module.
```

### Explain a specific rule

```bash
behave-doctor explain BD301
```

```text
ID:          BD301
Name:        unused-step-def
Severity:    warning
Category:    coverage
Description: Step definition never matched by any feature step.
```

## Statistics

Print project statistics only (no diagnostics):

```bash
behave-doctor stats .
```

```text
Features:                12
Scenarios:               47
Steps:                   213
Step definitions:        89
Tags:                    8
Total tag usages:        34
Avg steps/scenario:      4.5
Unused step definitions: 3
Undefined steps:         1
```

## Dependency graph

Output the module dependency graph in DOT format (for Graphviz):

```bash
behave-doctor graph .
```

Render it to an image:

```bash
behave-doctor graph . | dot -Tpng -o deps.png
```

Or to SVG:

```bash
behave-doctor graph . | dot -Tsvg -o deps.svg
```

## Python API

behave-doctor can be used as a library:

```python
from behave_doctor import scan_project, Severity

report = scan_project("path/to/project")

# Iterate over diagnostics
for d in report.diagnostics:
    print(f"{d.rule_id}: {d.message} at {d.file}:{d.line}")

# Filter by severity
errors = [d for d in report.diagnostics if d.severity is Severity.ERROR]

# Access statistics
stats = report.statistics
print(f"{stats.features} features, {stats.scenarios} scenarios")
print(f"{stats.unused_step_definitions} unused step definitions")
print(f"{stats.undefined_steps} undefined steps")

# Exit code: 0 = clean, 1 = issues found
print(f"Exit code: {report.exit_code}")
```

See [Python API](python-api.md) for the full reference.

## Next steps

- [CLI Reference](cli.md) — every command, flag, and option.
- [Rules](rules/index.md) — detailed documentation for all 18 rules.
- [Configuration](configuration.md) — customize thresholds via
  `pyproject.toml`.
- [CI/CD](ci-cd.md) — integrate with GitHub Actions and pre-commit.

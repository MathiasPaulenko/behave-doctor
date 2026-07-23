# CLI Reference

## Synopsis

```text
behave-doctor [--version] {scan,list-rules,explain,stats,graph} ...
```

When no subcommand is given, `scan` is implied. For example,
`behave-doctor .` is equivalent to `behave-doctor scan .`.

## Global options

| Option         | Description                          |
| -------------- | ------------------------------------ |
| `--version`    | Show version and exit.               |
| `-h`, `--help` | Show help message and exit.          |

## `scan`

Run all enabled rules against a Behave project and print a diagnostic report.

### Usage

```text
behave-doctor scan [PATH] [OPTIONS]
```

### Arguments

| Argument | Default | Description                                      |
| -------- | ------- | ------------------------------------------------ |
| `PATH`   | `.`     | Project root directory (must contain `features/`). |

### Options

| Option                 | Default            | Description                                              |
| ---------------------- | ------------------ | -------------------------------------------------------- |
| `--features-dir DIR`   | `features/`        | Relative path to the features directory.                 |
| `--steps-dir DIR`      | `features/steps/`  | Relative path to the step definitions directory.         |
| `--config FILE`        | auto-detected      | Path to a `pyproject.toml` config file.                  |
| `--format FORMAT`      | `text`             | Output format: `text`, `json`, or `sarif`.               |
| `-o`, `--output FILE`  | stdout             | Write report to a file instead of stdout.                |
| `--rules IDS`          | all enabled        | Comma-separated rule IDs to run (overrides config).      |
| `--exclude-rules IDS`  | none               | Comma-separated rule IDs to skip.                        |
| `--severity LEVEL`     | `info`             | Minimum severity: `error`, `warning`, `info`, `hint`.    |
| `--no-color`           | off                | Disable ANSI color codes (text format only).             |
| `-q`, `--quiet`        | off                | Only show errors (text format only).                     |
| `-v`, `--verbose`      | off                | Show suggestions and metadata per issue (text only).     |

### Exit codes

| Code | Meaning                                      |
| ---- | -------------------------------------------- |
| 0    | No errors or warnings found.                 |
| 1    | One or more errors or warnings found.        |
| 2    | Scan failed (e.g. missing features directory).|

### Examples

```bash
# Scan the current directory (default subcommand)
behave-doctor .

# Scan a specific project
behave-doctor scan /path/to/project

# Only show errors, no colors (good for CI logs)
behave-doctor scan . --severity error --no-color

# Run only coverage rules
behave-doctor scan . --rules BD301,BD302,BD303,BD304

# Exclude structure rules (they're informational)
behave-doctor scan . --exclude-rules BD101,BD102,BD103,BD104

# Write SARIF output to a file
behave-doctor scan . --format sarif -o behave-doctor.sarif

# Write JSON output to a file
behave-doctor scan . --format json -o report.json

# Verbose output with suggestions
behave-doctor scan . --verbose

# Quiet mode — only errors
behave-doctor scan . --quiet

# Custom features/steps directories
behave-doctor scan . --features-dir my_features --steps-dir my_features/steps
```

## `list-rules`

List all available diagnostic rules with their ID, severity, category, and
name.

```bash
behave-doctor list-rules
```

```text
BD101  INFO      structure     feature-count  -  Report total feature count.
BD102  INFO      structure     scenario-count  -  Report total scenario count.
BD103  INFO      structure     step-count  -  Report total step count.
BD104  INFO      structure     tag-coverage  -  Report tag usage distribution.
BD201  ERROR     quality       duplicate-step-defs  -  Same pattern registered multiple times.
BD202  WARNING   quality       scenario-no-tags  -  Scenario has no tags.
BD203  WARNING   quality       feature-too-many-scenarios  -  Feature has more than N scenarios (default 20).
BD204  WARNING   quality       inconsistent-tag-casing  -  Tags with inconsistent casing (e.g. @SmokeTest vs @smoke_test).
BD301  WARNING   coverage     unused-step-def  -  Step definition never matched by any feature step.
BD302  ERROR     coverage     undefined-step  -  Step in feature has no matching definition.
BD303  INFO      coverage     unused-tag  -  Tag defined but never used in CI filters.
BD304  WARNING   coverage     orphan-scenario  -  Scenario never selected by any tag filter (all tags unique).
BD401  WARNING   complexity   scenario-too-many-steps  -  Scenario has more than N steps (default 10).
BD402  WARNING   complexity   step-too-many-params  -  Step pattern has more than N parameters (default 5).
BD403  WARNING   complexity   feature-too-large  -  Feature file has more than N lines (default 300).
BD501  ERROR     dependency   circular-dependency  -  Circular import dependency between step modules.
BD502  WARNING   dependency   unused-import  -  Import in step module not used.
BD503  ERROR     dependency   missing-step-module  -  Feature references steps from a non-existent or empty module.
```

## `explain`

Show detailed information about a specific rule, including its description,
severity, category, and configuration options.

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

## `stats`

Print project statistics only — no diagnostics. Useful for dashboards or
quick health checks.

```bash
behave-doctor stats [PATH]
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

Accepts the same `--features-dir` and `--steps-dir` options as `scan`.

## `graph`

Output the module dependency graph in [DOT](https://graphviz.org/doc/info/lang.html)
format for rendering with [Graphviz](https://graphviz.org/).

```bash
behave-doctor graph [PATH]
```

Render to PNG:

```bash
behave-doctor graph . | dot -Tpng -o deps.png
```

Render to SVG:

```bash
behave-doctor graph . | dot -Tsvg -o deps.svg
```

The graph shows import relationships between step modules. Each node is a
Python module under `features/steps/`, and edges represent `import`
statements between them. This is useful for visualizing BD501 (circular
dependencies) and BD502 (unused imports).

Accepts the same `--features-dir` and `--steps-dir` options as `scan`.

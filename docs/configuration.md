# Configuration

behave-doctor reads configuration from `[tool.behave-doctor]` in
`pyproject.toml`. All options have sensible defaults — configuration is
**optional**.

## Configuration file

behave-doctor looks for `pyproject.toml` in the following order:

1. The path specified by `--config` on the CLI.
2. `pyproject.toml` in the project root (the `PATH` argument to `scan`).
3. `pyproject.toml` in the current working directory.

If no config file is found, all defaults are used.

## Full example

```toml
[tool.behave-doctor]
features_dir = "features"
steps_dir = "features/steps"
min_severity = "hint"
exclude_tags = ["@smoke", "@wip"]

# Disable a rule entirely
[tool.behave-doctor.rules.BD101]
enabled = false

# Adjust a threshold
[tool.behave-doctor.rules.BD203]
enabled = true
max_scenarios = 15

[tool.behave-doctor.rules.BD401]
max_steps = 8

[tool.behave-doctor.rules.BD402]
max_params = 3

[tool.behave-doctor.rules.BD403]
max_lines = 200
```

## Top-level options

| Option          | Type     | Default          | Description                                          |
| --------------- | -------- | ---------------- | ---------------------------------------------------- |
| `features_dir`  | string   | `features`       | Relative path to the features directory.             |
| `steps_dir`     | string   | `features/steps` | Relative path to the step definitions directory.     |
| `min_severity`  | string   | `hint`           | Minimum severity to report (see below).              |
| `exclude_tags`  | list     | `[]`             | Tags excluded from BD303 (unused-tag) analysis.      |

### `features_dir`

Relative path from the project root to the directory containing `.feature`
files. Defaults to `features` (the Behave convention).

```toml
features_dir = "tests/features"
```

### `steps_dir`

Relative path from the project root to the directory containing Python step
definitions. Defaults to `features/steps` (the Behave convention).

```toml
steps_dir = "tests/steps"
```

### `min_severity`

Controls the minimum severity of diagnostics to report. Diagnostics below
this level are suppressed.

```toml
min_severity = "warning"  # only show errors and warnings
```

### `exclude_tags`

A list of tags to exclude from BD303 (unused-tag) analysis. Tags listed here
are considered "intentionally unused" and will not be flagged.

```toml
exclude_tags = ["@smoke", "@wip", "@manual"]
```

## Per-rule options

Every rule accepts an `enabled` boolean:

```toml
[tool.behave-doctor.rules.BD101]
enabled = false
```

Rules with thresholds accept additional numeric options:

| Rule  | Option          | Type | Default | Description                                    |
| ----- | --------------- | ---- | ------- | ---------------------------------------------- |
| BD203 | `max_scenarios` | int  | 20      | Maximum scenarios per feature.                 |
| BD401 | `max_steps`     | int  | 10      | Maximum steps per scenario.                    |
| BD402 | `max_params`    | int  | 5       | Maximum parameters in a step pattern.          |
| BD403 | `max_lines`     | int  | 300     | Maximum lines per feature file.                |

### Example: strict mode

```toml
[tool.behave-doctor]
min_severity = "warning"

[tool.behave-doctor.rules.BD203]
max_scenarios = 10

[tool.behave-doctor.rules.BD401]
max_steps = 5

[tool.behave-doctor.rules.BD402]
max_params = 3

[tool.behave-doctor.rules.BD403]
max_lines = 150
```

### Example: disable informational rules

```toml
[tool.behave-doctor.rules.BD101]
enabled = false

[tool.behave-doctor.rules.BD102]
enabled = false

[tool.behave-doctor.rules.BD103]
enabled = false

[tool.behave-doctor.rules.BD104]
enabled = false
```

Or simply set `min_severity = "warning"` to suppress all `info` diagnostics.

## Severity values

| Value     | Meaning                                          |
| --------- | ------------------------------------------------ |
| `error`   | Only errors.                                     |
| `warning` | Errors and warnings.                             |
| `info`    | Errors, warnings, and info.                      |
| `hint`    | Everything (default).                            |

Severity hierarchy: `error` > `warning` > `info` > `hint`.

## CLI overrides

CLI flags override config file values. This lets you have a strict config
for local development while relaxing rules in CI (or vice versa).

```bash
# Override severity
behave-doctor scan . --severity error

# Override directories
behave-doctor scan . --features-dir my_features --steps-dir my_steps

# Run only specific rules (ignores enabled/disabled config)
behave-doctor scan . --rules BD301,BD302

# Exclude specific rules
behave-doctor scan . --exclude-rules BD101,BD102

# Use a specific config file
behave-doctor scan . --config /path/to/custom-pyproject.toml
```

## Environment variables

behave-doctor does not read environment variables. All configuration is done
via `pyproject.toml` or CLI flags.

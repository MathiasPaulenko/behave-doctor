# Configuration

behave-doctor reads configuration from `[tool.behave-doctor]` in
`pyproject.toml`. All options have sensible defaults — configuration is
optional.

## Full example

```toml
[tool.behave-doctor]
features_dir = "features"
steps_dir = "features/steps"
min_severity = "hint"
exclude_tags = ["@smoke", "@wip"]

[tool.behave-doctor.rules.BD101]
enabled = false

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

| Option          | Type     | Default          | Description                          |
| --------------- | -------- | ---------------- | ------------------------------------ |
| `features_dir`  | string   | `features`       | Relative path to features directory. |
| `steps_dir`     | string   | `features/steps` | Relative path to step definitions.   |
| `min_severity`  | string   | `hint`           | Minimum severity to report.          |
| `exclude_tags`  | list     | `[]`             | Tags excluded from BD303.            |

## Per-rule options

Every rule accepts an `enabled` boolean. Rules with thresholds accept
additional numeric options:

| Rule  | Option          | Type | Default |
| ----- | --------------- | ---- | ------- |
| BD203 | `max_scenarios` | int  | 20      |
| BD401 | `max_steps`     | int  | 10      |
| BD402 | `max_params`    | int  | 5       |
| BD403 | `max_lines`     | int  | 300     |

## Severity values

| Value     | Meaning                                          |
| --------- | ------------------------------------------------ |
| `error`   | Only errors.                                     |
| `warning` | Errors and warnings.                             |
| `info`    | Errors, warnings, and info.                      |
| `hint`    | Everything (default).                            |

## CLI overrides

CLI flags override config file values:

```bash
behave-doctor scan . --severity error --features-dir my_features
```

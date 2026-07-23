# Rules Overview

behave-doctor ships with **18 diagnostic rules** across **5 categories**.
Each rule has a stable ID (e.g. `BD301`), a severity, a category, and
optionally configurable thresholds.

## Categories

| Code prefix | Category     | Description                                              |
| ----------- | ------------ | -------------------------------------------------------- |
| BD1xx       | Structure    | Informational metrics about the project.                 |
| BD2xx       | Quality      | Suite quality issues (duplicates, tags, feature size).   |
| BD3xx       | Coverage     | Unused / undefined steps and tags.                       |
| BD4xx       | Complexity   | Size and complexity limits.                              |
| BD5xx       | Dependency   | Import and module dependency analysis.                   |

## Severities

| Severity  | Meaning                                          |
| --------- | ------------------------------------------------ |
| `error`   | Must fix — the suite is broken or unsafe.        |
| `warning` | Should fix — quality or maintainability issue.   |
| `info`    | Informational — no action required.              |
| `hint`    | Suggestion — optional improvement.               |

## Rule list

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

## Detailed documentation

- [Structure (BD101-104)](structure.md)
- [Quality (BD201-204)](quality.md)
- [Coverage (BD301-304)](coverage.md)
- [Complexity (BD401-403)](complexity.md)
- [Dependencies (BD501-503)](dependencies.md)

## Configuration

Rules can be enabled/disabled and configured via `pyproject.toml`:

```toml
# Disable a rule
[tool.behave-doctor.rules.BD101]
enabled = false

# Adjust a threshold
[tool.behave-doctor.rules.BD203]
max_scenarios = 15

[tool.behave-doctor.rules.BD401]
max_steps = 8

[tool.behave-doctor.rules.BD403]
max_lines = 200
```

See [Configuration](../configuration.md) for all options.

## Running specific rules

### From the CLI

```bash
# Run only specific rules
behave-doctor scan . --rules BD301,BD302

# Exclude specific rules
behave-doctor scan . --exclude-rules BD101,BD102,BD103,BD104

# Run only errors
behave-doctor scan . --severity error
```

### From the Python API

```python
from behave_doctor import scan_project, DoctorConfig

config = DoctorConfig(
    rules={
        "BD101": {"enabled": False},
        "BD401": {"max_steps": 5},
    }
)
report = scan_project("path/to/project", config=config)
```

## Rule IDs

Rule IDs are stable and will never change. They follow the pattern
`BD{category}{number}`:

- `BD1xx` — Structure
- `BD2xx` — Quality
- `BD3xx` — Coverage
- `BD4xx` — Complexity
- `BD5xx` — Dependency

This makes them safe to reference in CI configurations, pre-commit hooks,
and `pyproject.toml` overrides.

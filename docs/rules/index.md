# Rules Overview

behave-doctor ships with **18 diagnostic rules** across **5 categories**.
Each rule has a stable ID (e.g. `BD301`), a severity, and a category.

## Categories

| Code prefix | Category     | Description                                      |
| ----------- | ------------ | ------------------------------------------------ |
| BD1xx       | Structure    | Informational metrics about the project.         |
| BD2xx       | Quality      | Suite quality issues (duplicates, tags).         |
| BD3xx       | Coverage     | Unused / undefined steps and tags.               |
| BD4xx       | Complexity   | Size and complexity limits.                      |
| BD5xx       | Dependency   | Import and module dependency analysis.           |

## Severities

| Severity  | Meaning                                          |
| --------- | ------------------------------------------------ |
| `error`   | Must fix — the suite is broken or unsafe.        |
| `warning` | Should fix — quality or maintainability issue.   |
| `info`    | Informational — no action required.              |
| `hint`    | Suggestion — optional improvement.               |

## Rule list

| ID    | Name                        | Severity | Category     |
| ----- | --------------------------- | -------- | ------------ |
| BD101 | feature-count               | info     | Structure    |
| BD102 | scenario-count              | info     | Structure    |
| BD103 | step-count                  | info     | Structure    |
| BD104 | tag-coverage                | info     | Structure    |
| BD201 | duplicate-step-defs         | error    | Quality      |
| BD202 | scenario-no-tags            | warning  | Quality      |
| BD203 | feature-too-many-scenarios  | warning  | Quality      |
| BD204 | inconsistent-tag-casing     | warning  | Quality      |
| BD301 | unused-step-def             | warning  | Coverage     |
| BD302 | undefined-step              | error    | Coverage     |
| BD303 | unused-tag                  | info     | Coverage     |
| BD304 | orphan-scenario             | warning  | Coverage     |
| BD401 | scenario-too-many-steps     | warning  | Complexity   |
| BD402 | step-too-many-params        | warning  | Complexity   |
| BD403 | feature-too-large           | warning  | Complexity   |
| BD501 | circular-dependency         | error    | Dependency   |
| BD502 | unused-import               | warning  | Dependency   |
| BD503 | missing-step-module         | error    | Dependency   |

## Configuration

Rules can be enabled/disabled and configured via `pyproject.toml`:

```toml
[tool.behave-doctor.rules.BD203]
enabled = true
max_scenarios = 15

[tool.behave-doctor.rules.BD401]
max_steps = 8

[tool.behave-doctor.rules.BD403]
max_lines = 200
```

See [Configuration](../configuration.md) for all options.

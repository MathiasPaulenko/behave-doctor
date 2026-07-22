# Complexity Rules (BD401-403)

Enforce size and complexity limits on scenarios, step definitions, and
feature files.

## BD401 — scenario-too-many-steps

Finds scenarios with more than `max_steps` steps (default 10). Long
scenarios are hard to read, slow to debug, and often violate the
"one behavior per scenario" principle.

| Attribute   | Value              |
| ----------- | ------------------ |
| Severity    | warning            |
| Category    | Complexity         |
| Configurable| `max_steps` (int)  |

```toml
[tool.behave-doctor.rules.BD401]
max_steps = 8
```

## BD402 — step-too-many-params

Finds step definitions whose pattern has more than `max_params` parameters
(default 5). Step patterns with many parameters are fragile and hard to
read.

| Attribute   | Value                |
| ----------- | -------------------- |
| Severity    | warning              |
| Category    | Complexity           |
| Configurable| `max_params` (int)   |

```toml
[tool.behave-doctor.rules.BD402]
max_params = 3
```

## BD403 — feature-too-large

Finds feature files with more than `max_lines` lines (default 300). Large
feature files are hard to navigate and review.

| Attribute   | Value              |
| ----------- | ------------------ |
| Severity    | warning            |
| Category    | Complexity         |
| Configurable| `max_lines` (int)  |

```toml
[tool.behave-doctor.rules.BD403]
max_lines = 200
```

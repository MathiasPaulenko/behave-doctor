# Python API

behave-doctor can be used as a library for custom tooling, IDE plugins, CI
integrations, or anything that needs programmatic access to Behave suite
diagnostics.

## Installation

```bash
pip install behave-doctor
```

No extra dependencies are needed — the library API is part of the core
package.

## `scan_project`

The high-level entry point. Scans a Behave project and returns a
`ProjectReport` with diagnostics, statistics, and an exit code.

::: behave_doctor.scan_project
    options:
      show_root_heading: true

### Example: basic scan

```python
from behave_doctor import scan_project

report = scan_project("path/to/project")

for d in report.diagnostics:
    print(f"{d.rule_id}: {d.message} at {d.file}:{d.line}")

print(f"Exit code: {report.exit_code}")
```

### Example: with custom config

```python
from behave_doctor import scan_project, DoctorConfig, Severity

config = DoctorConfig(
    features_dir="my_features",
    steps_dir="my_steps",
    min_severity=Severity.WARNING,
    rules={
        "BD101": {"enabled": False},
        "BD401": {"max_steps": 5},
        "BD203": {"max_scenarios": 10},
    },
)
report = scan_project("path/to/project", config=config)
```

### Example: filter by severity

```python
from behave_doctor import scan_project, Severity

report = scan_project("path/to/project")

errors = [d for d in report.diagnostics if d.severity is Severity.ERROR]
warnings = [d for d in report.diagnostics if d.severity is Severity.WARNING]

print(f"{len(errors)} errors, {len(warnings)} warnings")
```

## `ProjectReport`

The result of a `scan_project` call. Contains diagnostics, statistics, and
an exit code.

::: behave_doctor.ProjectReport
    options:
      show_root_heading: true

### Attributes

| Attribute          | Type                  | Description                              |
| ------------------ | --------------------- | ---------------------------------------- |
| `diagnostics`      | `list[Diagnostic]`    | All diagnostics found during the scan.   |
| `statistics`       | `ProjectStatistics`   | Aggregate statistics about the project.  |
| `exit_code`        | `int`                 | 0 = clean, 1 = issues found.             |
| `scan_duration_ms` | `int`                 | Scan duration in milliseconds.           |
| `scanned_at`       | `datetime`            | Timestamp of the scan.                   |
| `project_path`     | `Path`                | Root path of the scanned project.        |

## `Diagnostic`

A single diagnostic finding produced by a rule.

::: behave_doctor.Diagnostic
    options:
      show_root_heading: true

### Attributes

| Attribute    | Type           | Description                                                            |
| ------------ | -------------- | ---------------------------------------------------------------------- |
| `rule_id`    | `str`          | Rule identifier (e.g. `"BD301"`).                                      |
| `rule_name`  | `str`          | Human-readable rule name (e.g. `"unused-step-def"`).                   |
| `severity`   | `Severity`     | One of `ERROR`, `WARNING`, `INFO`, `HINT`.                             |
| `category`   | `Category`     | One of `STRUCTURE`, `QUALITY`, `COVERAGE`, `COMPLEXITY`, `DEPENDENCY`. |
| `message`    | `str`          | Human-readable description of the issue.                               |
| `file`       | `Path \| None` | File path where the issue was found.                                   |
| `line`       | `int \| None`  | Line number (1-based), if applicable.                                  |
| `suggestion` | `str \| None`  | Optional fix suggestion.                                               |
| `metadata`   | `dict`         | Optional rule-specific metadata.                                       |

## `Severity`

Enum of diagnostic severity levels.

::: behave_doctor.Severity
    options:
      show_root_heading: true

| Value      | Description                              |
| ---------- | ---------------------------------------- |
| `ERROR`    | Must fix — the suite is broken or unsafe.|
| `WARNING`  | Should fix — quality or maintainability. |
| `INFO`     | Informational — no action required.      |
| `HINT`     | Suggestion — optional improvement.       |

## `Category`

Enum of diagnostic categories.

::: behave_doctor.Category
    options:
      show_root_heading: true

| Value         | Description                                      |
| ------------- | ------------------------------------------------ |
| `STRUCTURE`   | Informational metrics (BD101-104).               |
| `QUALITY`     | Suite quality issues (BD201-204).                |
| `COVERAGE`    | Unused/undefined steps and tags (BD301-304).     |
| `COMPLEXITY`  | Size and complexity limits (BD401-403).          |
| `DEPENDENCY`  | Import and module analysis (BD501-503).          |

## `DoctorConfig`

Configuration for a scan. All fields have defaults.

::: behave_doctor.DoctorConfig
    options:
      show_root_heading: true

### Attributes

| Attribute         | Type                  | Default            | Description                          |
| ----------------- | --------------------- | ------------------ | ------------------------------------ |
| `features_dir`    | `str`                 | `"features/"`      | Relative path to features.           |
| `steps_dir`       | `str`                 | `"features/steps/"`| Relative path to step definitions.   |
| `min_severity`    | `Severity`            | `Severity.INFO`    | Minimum severity to report.          |
| `exclude_tags`    | `list[str]`           | `[]`               | Tags excluded from BD303.            |
| `exclude_paths`   | `list[str]`           | `[]`               | Glob patterns to exclude from scan.  |
| `rules`           | `dict[str, dict]`     | `{}`               | Per-rule configuration.              |

### Loading from `pyproject.toml`

```python
from behave_doctor import DoctorConfig

config = DoctorConfig.from_pyproject("path/to/project/pyproject.toml")
```

## `ProjectStatistics`

Aggregate statistics about the scanned project.

::: behave_doctor.ProjectStatistics
    options:
      show_root_heading: true

### Attributes

| Attribute                    | Type     | Description                                |
| ---------------------------- | -------- | ------------------------------------------ |
| `features`                   | `int`    | Total number of features.                  |
| `scenarios`                  | `int`    | Total number of scenarios.                 |
| `steps`                      | `int`    | Total number of steps.                     |
| `step_definitions`           | `int`    | Total number of step definitions.          |
| `tags`                       | `int`    | Number of unique tags.                     |
| `total_tag_usages`           | `int`    | Total tag usages across all scenarios.     |
| `average_steps_per_scenario` | `float`  | Average steps per scenario.                |
| `unused_step_definitions`    | `int`    | Step definitions never matched.            |
| `undefined_steps`            | `int`    | Steps with no matching definition.         |

## Example: custom reporter

```python
import json
from behave_doctor import scan_project, Severity

report = scan_project("path/to/project")

output = {
    "errors": [],
    "warnings": [],
    "stats": {
        "features": report.statistics.features,
        "scenarios": report.statistics.scenarios,
        "unused_step_definitions": report.statistics.unused_step_definitions,
        "undefined_steps": report.statistics.undefined_steps,
    },
}

for d in report.diagnostics:
    entry = {
        "rule": d.rule_id,
        "message": d.message,
        "file": d.file,
        "line": d.line,
    }
    if d.severity is Severity.ERROR:
        output["errors"].append(entry)
    elif d.severity is Severity.WARNING:
        output["warnings"].append(entry)

print(json.dumps(output, indent=2))
```

## Example: IDE plugin integration

```python
from behave_doctor import scan_project, Severity

def on_save(project_path: str) -> list[dict]:
    """Run behave-doctor on save and return diagnostics for the editor."""
    report = scan_project(project_path)

    return [
        {
            "file": d.file,
            "line": d.line,
            "severity": d.severity.name.lower(),
            "message": f"[{d.rule_id}] {d.message}",
            "source": "behave-doctor",
        }
        for d in report.diagnostics
        if d.severity in (Severity.ERROR, Severity.WARNING)
    ]
```

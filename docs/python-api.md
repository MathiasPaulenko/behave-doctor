# Python API

behave-doctor can be used as a library for custom tooling, IDE plugins, or
CI integrations.

## `scan_project`

The high-level entry point:

::: behave_doctor.scan_project
    options:
      show_root_heading: true

## `ProjectReport`

::: behave_doctor.ProjectReport
    options:
      show_root_heading: true

## `Diagnostic`

::: behave_doctor.Diagnostic
    options:
      show_root_heading: true

## `DoctorConfig`

::: behave_doctor.DoctorConfig
    options:
      show_root_heading: true

## Example: custom filtering

```python
from behave_doctor import scan_project, Severity

report = scan_project("path/to/project")

# Only show errors
errors = [d for d in report.diagnostics if d.severity is Severity.ERROR]
for d in errors:
    print(f"{d.rule_id}: {d.message} at {d.file}:{d.line}")

# Exit code: 0 if clean, 1 if errors/warnings, 2 if scan failed
print(f"Exit code: {report.exit_code}")
```

## Example: custom config

```python
from behave_doctor import scan_project, DoctorConfig

config = DoctorConfig(
    features_dir="my_features",
    steps_dir="my_steps",
    min_severity="warning",
    rules={"BD101": {"enabled": False}, "BD401": {"max_steps": 5}},
)
report = scan_project("path/to/project", config=config)
```

## Example: access statistics

```python
from behave_doctor import scan_project

report = scan_project("path/to/project")
stats = report.statistics
print(f"{stats.features} features, {stats.scenarios} scenarios")
print(f"{stats.unused_step_definitions} unused step definitions")
print(f"{stats.undefined_steps} undefined steps")
```

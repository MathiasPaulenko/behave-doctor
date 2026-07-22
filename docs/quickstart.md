# Quick Start

## Scan a project

From the root of your Behave project:

```bash
behave-doctor scan .
```

behave-doctor will:

1. Discover `.feature` files under `features/`.
2. Parse Python step definitions under `features/steps/`.
3. Build a dependency graph (step matches + module imports).
4. Run all 15 diagnostic rules.
5. Print a human-readable report.

## Output formats

```bash
# Human-readable (default)
behave-doctor scan . --format text

# JSON for CI integration
behave-doctor scan . --format json

# SARIF 2.1.0 for GitHub Code Scanning
behave-doctor scan . --format sarif -o behave-doctor.sarif
```

## Filter rules

Run only specific rules:

```bash
behave-doctor scan . --rules BD301,BD302
```

Exclude rules:

```bash
behave-doctor scan . --exclude-rules BD101,BD102
```

Set minimum severity:

```bash
behave-doctor scan . --severity error
```

## Explore rules

List all available rules:

```bash
behave-doctor list-rules
```

Explain a specific rule:

```bash
behave-doctor explain BD301
```

## Statistics

```bash
behave-doctor stats .
```

```
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

## Python API

```python
from behave_doctor import scan_project

report = scan_project("path/to/project")
for d in report.diagnostics:
    print(f"{d.rule_id}: {d.message} at {d.file}:{d.line}")
print(f"Exit code: {report.exit_code}")
```

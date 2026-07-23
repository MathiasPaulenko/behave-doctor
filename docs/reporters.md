# Reporters

behave-doctor supports three output formats. Use `--format` to select one.

## Text (default)

Human-readable console output with optional ANSI colors. This is the
default format and is designed for developer terminals and CI logs.

```bash
behave-doctor scan . --format text
behave-doctor scan . --format text --no-color
behave-doctor scan . --format text --quiet
behave-doctor scan . --format text --verbose
```

### Flags

| Flag         | Description                                            |
| ------------ | ------------------------------------------------------ |
| `--no-color` | Disable ANSI color codes (recommended for CI logs).    |
| `--quiet`    | Only show errors (suppress warnings and info).         |
| `--verbose`  | Show suggestions and metadata per issue.               |

### Default output

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

### Quiet output (`--quiet`)

Only errors are shown — warnings and info diagnostics are suppressed:

```text
Scanning . ...
Found 12 features, 47 scenarios, 213 steps, 89 step definitions.

BD201  ERROR     Duplicate step definition for pattern 'the user is logged in' in: features/steps/auth.py:10, features/steps/login.py:15
BD302  ERROR     Undefined step: "Given the database is seeded"
      (features/login.feature:18)

2 errors in 0.42s
```

### Verbose output (`--verbose`)

Each diagnostic includes metadata (and a suggestion when the rule provides one):

```text
BD301  WARNING   Unused step definition: "the user clicks submit"
      (features/steps/auth.py:42)
      Metadata: {"def_id": "steps.when_clicks_submit", "pattern": "the user clicks submit"}
```

### ANSI colors

When stdout is a terminal, behave-doctor uses ANSI colors:

- **Red** for errors
- **Yellow** for warnings
- **Cyan** for info

Use `--no-color` to disable colors (recommended for CI logs that don't
support ANSI).

## JSON

Structured JSON output for CI integration, custom tooling, and programmatic
consumption.

```bash
behave-doctor scan . --format json
```

### Schema

Top-level keys (sorted alphabetically):

```json
{
  "diagnostics": [...],
  "exit_code": 1,
  "project_path": "path/to/project",
  "scan_duration_ms": 420,
  "scanned_at": "2024-01-01T12:00:00.000000",
  "statistics": {...}
}
```

### Diagnostic object

Each entry in `diagnostics`:

```json
{
  "category": "coverage",
  "file": "features/steps/auth.py",
  "line": 42,
  "message": "Unused step definition: \"the user clicks submit\"",
  "metadata": {
    "def_id": "steps.when_clicks_submit",
    "pattern": "the user clicks submit"
  },
  "rule_id": "BD301",
  "rule_name": "unused-step-def",
  "severity": "warning",
  "suggestion": null
}
```

### Statistics object

```json
{
  "features": 12,
  "scenarios": 47,
  "steps": 213,
  "step_definitions": 89,
  "tags": 8,
  "total_tag_usages": 34,
  "average_steps_per_scenario": 4.5,
  "unused_step_definitions": 3,
  "undefined_steps": 1
}
```

### Writing to a file

```bash
behave-doctor scan . --format json -o report.json
```

### Parsing with Python

```python
import json
import subprocess

result = subprocess.run(
    ["behave-doctor", "scan", ".", "--format", "json"],
    capture_output=True, text=True,
)
data = json.loads(result.stdout)

for d in data["diagnostics"]:
    if d["severity"] == "error":
        print(f"{d['rule_id']}: {d['message']} ({d['file']}:{d['line']})")
```

### Parsing with jq

```bash
# Count errors
behave-doctor scan . --format json | jq '[.diagnostics[] | select(.severity == "error")] | length'

# List all undefined steps
behave-doctor scan . --format json | jq '[.diagnostics[] | select(.rule_id == "BD302")]'

# Show statistics
behave-doctor scan . --format json | jq '.statistics'
```

## SARIF 2.1.0

[SARIF](https://sarifweb.azurewebsites.net/) (Static Analysis Results
Interchange Format) is an industry-standard format for static analysis
output. behave-doctor produces SARIF 2.1.0 output compatible with GitHub
Code Scanning, Azure DevOps, and other SARIF-consuming tools.

```bash
behave-doctor scan . --format sarif -o behave-doctor.sarif
```

### GitHub Code Scanning integration

Upload SARIF results to GitHub Code Scanning in a workflow:

```yaml
name: behave-doctor
on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install behave-doctor
      - run: behave-doctor scan . --format sarif -o behave-doctor.sarif
        continue-on-error: true
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: behave-doctor.sarif
```

The `continue-on-error: true` ensures the SARIF file is uploaded even when
behave-doctor finds issues (exit code 1).

### SARIF structure

The output follows the [SARIF 2.1.0 specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html):

```json
{
  "$schema": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/cs01/schemas/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [
    {
      "tool": {
        "driver": {
          "name": "behave-doctor",
          "version": "1.1.0",
          "rules": [...]
        }
      },
      "results": [...]
    }
  ]
}
```

Each rule is declared in `tool.driver.rules` with its ID, name, severity
level, and description. Each finding is a `results[]` entry with the rule
ID, message, location (file + line), and severity level.

### Severity mapping

| behave-doctor | SARIF level   |
| ------------- | ------------- |
| error         | `error`       |
| warning       | `warning`     |
| info          | `note`        |
| hint          | `none`        |

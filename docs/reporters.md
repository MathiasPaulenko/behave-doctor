# Reporters

behave-doctor supports three output formats. Use `--format` to select one.

## Text (default)

Human-readable console output with optional ANSI colors.

```bash
behave-doctor scan . --format text
behave-doctor scan . --format text --no-color
behave-doctor scan . --format text --quiet
behave-doctor scan . --format text --verbose
```

| Flag         | Description                              |
| ------------ | ---------------------------------------- |
| `--no-color` | Disable ANSI color codes.                |
| `--quiet`    | Only show errors.                        |
| `--verbose`  | Show suggestions and metadata per issue. |

Example output:

```
Scanning path/to/project...
Found 12 features, 47 scenarios, 213 steps, 89 step definitions.

BD301  WARNING   Unused step definition: "the user clicks submit"  (features/steps/auth.py:42)
BD302  ERROR      Undefined step: "Given the database is seeded"   (features/login.feature:18)

1 errors, 1 warnings in 0.42s
```

## JSON

Structured JSON for CI integration and custom tooling.

```bash
behave-doctor scan . --format json
```

Top-level keys (sorted alphabetically):

```json
{
  "diagnostics": [...],
  "project_path": "path/to/project",
  "scan_duration_ms": 420,
  "scanned_at": "2024-01-01T12:00:00",
  "statistics": {...}
}
```

Each diagnostic has:

```json
{
  "rule_id": "BD301",
  "rule_name": "unused-step-def",
  "severity": "warning",
  "category": "coverage",
  "message": "Unused step definition: \"...\"",
  "file": "features/steps/auth.py",
  "line": 42,
  "suggestion": null,
  "metadata": {...}
}
```

## SARIF 2.1.0

For GitHub Code Scanning and other SARIF-compatible tools.

```bash
behave-doctor scan . --format sarif -o behave-doctor.sarif
```

Upload to GitHub Code Scanning in a workflow:

```yaml
- name: Run behave-doctor
  run: behave-doctor scan . --format sarif -o behave-doctor.sarif

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: behave-doctor.sarif
```

# CI/CD Integration

## GitHub Actions

### Basic lint step

```yaml
name: CI
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install behave-doctor
      - run: behave-doctor scan . --no-color
```

### GitHub Code Scanning (SARIF)

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

### Fail on errors only

```yaml
- run: behave-doctor scan . --severity error --no-color
```

## Pre-commit hook

```yaml
repos:
  - repo: https://github.com/MathiasPaulenko/behave-doctor
    rev: v0.1.0
    hooks:
      - id: behave-doctor
        args: ["scan", "--severity", "warning", "--no-color"]
```

## Other CI systems

behave-doctor is a standard CLI tool. In any CI system:

1. Install with `pip install behave-doctor`.
2. Run `behave-doctor scan . --no-color`.
3. Check the exit code: `0` = clean, `1` = issues found, `2` = scan error.

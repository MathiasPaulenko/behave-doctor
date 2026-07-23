# CI/CD Integration

behave-doctor is designed to run in CI pipelines. It is fast (typically
under 1 second for medium projects), produces no side effects, and uses
standard exit codes.

## Exit codes

| Code | Meaning                                      |
| ---- | -------------------------------------------- |
| 0    | No errors or warnings found.                 |
| 1    | One or more errors or warnings found.        |
| 2    | Scan failed (e.g. missing features directory).|

Most CI systems treat exit code 1 as a failure, which is the desired
behavior — issues in the Behave suite should block the pipeline.

## GitHub Actions

### Basic lint step

Add behave-doctor as a lint step in your CI workflow:

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

### Fail on errors only

If you want the pipeline to fail only on errors (not warnings):

```yaml
- run: behave-doctor scan . --severity error --no-color
```

### Fail on errors and warnings

```yaml
- run: behave-doctor scan . --severity warning --no-color
```

### GitHub Code Scanning (SARIF)

Upload results to GitHub Code Scanning for inline annotations in pull
requests:

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
behave-doctor finds issues (exit code 1). The `security-events: write`
permission is required for SARIF upload.

### Full CI example

A complete CI workflow with lint, test, and behave-doctor:

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

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install -e ".[dev]"
      - run: pytest

  code-scanning:
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

## Pre-commit hook

Add behave-doctor to your `.pre-commit-config.yaml` to run it on every
commit:

```yaml
repos:
  - repo: https://github.com/MathiasPaulenko/behave-doctor
    rev: v1.1.0
    hooks:
      - id: behave-doctor
        args: ["scan", "--severity", "warning", "--no-color"]
```

The hook scans `.feature` and `.py` files. It runs from the repository root
so it can build the full dependency graph.

### Configuration options for pre-commit

| `args` value              | Effect                                           |
| ------------------------- | ------------------------------------------------ |
| `--severity error`        | Only fail on errors (suppress warnings).         |
| `--severity warning`      | Fail on errors and warnings (recommended).       |
| `--no-color`              | Disable ANSI colors (recommended for CI logs).   |
| `--exclude-rules BD101`   | Skip specific rules.                             |
| `--format sarif -o out`   | Write SARIF output to a file.                    |

## GitLab CI

```yaml
behave-doctor:
  stage: lint
  image: python:3.13-slim
  script:
    - pip install behave-doctor
    - behave-doctor scan . --no-color
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

## CircleCI

```yaml
version: 2.1
jobs:
  behave-doctor:
    docker:
      - image: cimg/python:3.13
    steps:
      - checkout
      - run: pip install behave-doctor
      - run: behave-doctor scan . --no-color
workflows:
  version: 2
  lint:
    jobs:
      - behave-doctor
```

## Jenkins

```groovy
pipeline {
    agent any
    stages {
        stage('behave-doctor') {
            steps {
                sh 'pip install behave-doctor'
                sh 'behave-doctor scan . --no-color'
            }
        }
    }
}
```

## Other CI systems

behave-doctor is a standard CLI tool. In any CI system:

1. Install with `pip install behave-doctor`.
2. Run `behave-doctor scan . --no-color`.
3. Check the exit code: `0` = clean, `1` = issues found, `2` = scan error.

The `--no-color` flag is recommended for CI logs that don't support ANSI
escape codes.

## Caching

To speed up CI runs, cache the pip package:

### GitHub Actions

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.13"
    cache: pip
    cache-dependency-path: requirements.txt
- run: pip install behave-doctor
```

### Pre-commit autoupdate

To keep the pre-commit hook version up to date:

```bash
pre-commit autoupdate
```

This updates `rev:` in `.pre-commit-config.yaml` to the latest tag.

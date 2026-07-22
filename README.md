# behave-doctor

**Static analysis and diagnostics for Behave BDD suites.**

[![CI](https://github.com/MathiasPaulenko/behave-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/MathiasPaulenko/behave-doctor/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen)](https://github.com/MathiasPaulenko/behave-doctor)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/behave-doctor)](https://pypi.org/project/behave-doctor/)

behave-doctor inspects your Behave `.feature` files and Python step
definitions **without executing them**, surfacing issues like unused step
definitions, undefined steps, oversized features, inconsistent tags, and
circular import dependencies.

## Features

- **18 diagnostic rules** across 5 categories (structure, quality, coverage,
  complexity, dependencies).
- **3 output formats**: human-readable text, JSON, and SARIF 2.1.0 for
  GitHub Code Scanning.
- **Zero runtime dependencies** beyond `behave-model` — pure Python,
  fully typed, mypy --strict clean.
- **Configurable** via `[tool.behave-doctor]` in `pyproject.toml`.
- **Python API** for embedding in custom tooling.

## Quick start

```bash
pip install behave-doctor
behave-doctor scan .
```

```
Scanning . ...
Found 12 features, 47 scenarios, 213 steps, 89 step definitions.

BD301  WARNING   Unused step definition: "the user clicks submit"  (features/steps/auth.py:42)
BD302  ERROR      Undefined step: "Given the database is seeded"   (features/login.feature:18)

1 errors, 1 warnings in 0.42s
```

## Rules

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

```toml
# pyproject.toml
[tool.behave-doctor]
features_dir = "features"
steps_dir = "features/steps"
min_severity = "hint"
exclude_tags = ["@smoke", "@wip"]

[tool.behave-doctor.rules.BD203]
max_scenarios = 15

[tool.behave-doctor.rules.BD401]
max_steps = 8
```

## Python API

```python
from behave_doctor import scan_project

report = scan_project("path/to/project")
for d in report.diagnostics:
    print(f"{d.rule_id}: {d.message} at {d.file}:{d.line}")
print(f"Exit code: {report.exit_code}")
```

## CI/CD

```yaml
- run: pip install behave-doctor
- run: behave-doctor scan . --format sarif -o behave-doctor.sarif
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: behave-doctor.sarif
```

## Documentation

Full documentation at <https://mathiaspaulenko.github.io/behave-doctor/>.

## License

[MIT](LICENSE)

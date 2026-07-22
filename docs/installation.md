# Installation

## Requirements

- Python **3.11** or newer
- `behave-model >= 1.0` (installed automatically)

## From PyPI

```bash
pip install behave-doctor
```

## From source

```bash
git clone https://github.com/MathiasPaulenko/behave-doctor.git
cd behave-doctor
pip install .
```

## Development install

```bash
git clone https://github.com/MathiasPaulenko/behave-doctor.git
cd behave-doctor
pip install -e ".[dev]"
pre-commit install
```

## Verify

```bash
behave-doctor --version
```

## Pre-commit hook

Add behave-doctor to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/MathiasPaulenko/behave-doctor
    rev: v0.1.0
    hooks:
      - id: behave-doctor
        args: ["scan", "--format", "sarif", "-o", "behave-doctor.sarif"]
```

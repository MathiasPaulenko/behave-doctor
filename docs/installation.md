# Installation

## Requirements

- Python **3.11** or newer (tested on 3.11, 3.12, and 3.13)
- `behave-model >= 1.0` (installed automatically as a dependency)
- `typer >= 0.12` (installed automatically as a dependency)

behave-doctor has **minimal runtime dependencies** — only `behave-model`
(for `.feature` file parsing) and `typer` (for the CLI). It is pure Python,
fully typed (`mypy --strict` clean), and works on Linux, macOS, and Windows.

## From PyPI

The recommended way to install behave-doctor:

```bash
pip install behave-doctor
```

To upgrade:

```bash
pip install --upgrade behave-doctor
```

### With pipx (isolated environment)

If you prefer to keep behave-doctor isolated from your project's virtual
environment:

```bash
pipx install behave-doctor
```

### With uv

```bash
uv pip install behave-doctor
```

## From source

```bash
git clone https://github.com/MathiasPaulenko/behave-doctor.git
cd behave-doctor
pip install .
```

## Development install

For contributors who want to run tests, linting, and pre-commit hooks:

```bash
git clone https://github.com/MathiasPaulenko/behave-doctor.git
cd behave-doctor
pip install -e ".[dev]"
pre-commit install
```

The `[dev]` extra installs `pytest`, `pytest-cov`, `ruff`, `mypy`, `build`,
and `pre-commit`.

## Verify the installation

```bash
behave-doctor --version
```

```text
1.0.0
```

You can also verify the Python API is importable:

```bash
python -c "import behave_doctor; print(behave_doctor.__version__)"
```

## Pre-commit hook

behave-doctor ships a [pre-commit](https://pre-commit.com/) hook that runs
`behave-doctor scan` on every commit.

Add this to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/MathiasPaulenko/behave-doctor
    rev: v1.1.0
    hooks:
      - id: behave-doctor
        args: ["scan", "--severity", "warning", "--no-color"]
```

The hook scans `.feature` and `.py` files. It runs from the repository root
(`pass_filenames: false`) so it can build the full dependency graph.

### Pre-commit configuration options

| `args` value              | Effect                                           |
| ------------------------- | ------------------------------------------------ |
| `--severity error`        | Only fail on errors (suppress warnings).         |
| `--severity warning`      | Fail on errors and warnings (recommended).       |
| `--no-color`              | Disable ANSI colors (recommended for CI logs).   |
| `--exclude-rules BD101`   | Skip specific rules.                             |
| `--format sarif -o out`   | Write SARIF output to a file.                    |

## Uninstall

```bash
pip uninstall behave-doctor
```

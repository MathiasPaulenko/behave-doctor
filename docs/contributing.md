# Contributing

Contributions are welcome! See
[CONTRIBUTING.md](https://github.com/MathiasPaulenko/behave-doctor/blob/main/CONTRIBUTING.md)
in the repository for full guidelines.

## Quick reference

```bash
# Clone and install with dev extras
git clone https://github.com/MathiasPaulenko/behave-doctor.git
cd behave-doctor
pip install -e ".[dev]"
pre-commit install

# Day-to-day commands
make lint          # ruff check + mypy --strict
make lint-fix      # auto-fix lint issues
make format        # ruff format
make format-check  # verify formatting
make test          # pytest
make test-cov      # pytest with >= 90% coverage
make build         # build sdist + wheel
make clean         # remove build artifacts
```

## Adding a new rule

1. Choose a rule ID following the `BD{category}{number}` pattern.
2. Implement the rule in the appropriate `rules/{category}.py` file.
3. Register it in `rules/__init__.py`.
4. Add a test fixture and unit test.
5. Document it in `docs/rules/{category}.md`.
6. Update `docs/rules/index.md` and `README.md`.

See [Architecture](architecture.md) for the internal design and key
abstractions.

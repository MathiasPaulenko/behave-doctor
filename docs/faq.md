# FAQ

Common questions and troubleshooting for behave-doctor.

## General

### Does behave-doctor execute my tests?

**No.** behave-doctor performs purely static analysis. It parses `.feature`
files with `behave-model` and analyzes Python step definitions with the
AST — never importing or executing them. There are no side effects, no
network calls, and no state changes.

### Does behave-doctor depend on Behave?

**No.** behave-doctor's only runtime dependency is `behave-model`, which
provides the `.feature` file parser. behave-doctor does not import or
require the `behave` package itself. You can use behave-doctor on a project
that uses any version of Behave (or even a project that doesn't use Behave
at all but has `.feature` files).

### What Python versions are supported?

Python 3.11, 3.12, and 3.13. The CI pipeline tests all three versions on
Ubuntu, macOS, and Windows.

### Is behave-doctor fast?

Yes. behave-doctor typically completes in under 1 second for medium
projects (50-100 feature files). The scan duration is printed at the end of
the text report.

## Rules

### How do I disable a specific rule?

Via `pyproject.toml`:

```toml
[tool.behave-doctor.rules.BD101]
enabled = false
```

Or via the CLI:

```bash
behave-doctor scan . --exclude-rules BD101
```

### How do I disable all informational rules?

Set `min_severity` to `"warning"` to suppress all `info` diagnostics:

```toml
[tool.behave-doctor]
min_severity = "warning"
```

Or via the CLI:

```bash
behave-doctor scan . --severity warning
```

### How do I change a rule's threshold?

Via `pyproject.toml`:

```toml
[tool.behave-doctor.rules.BD401]
max_steps = 5  # default: 10
```

See [Configuration](configuration.md#per-rule-options) for all configurable
thresholds.

### Can I run only specific rules?

Yes:

```bash
behave-doctor scan . --rules BD301,BD302
```

### Are rule IDs stable?

**Yes.** Rule IDs (BD101-503) are stable and will never change. They are
safe to reference in CI configurations, pre-commit hooks, and
`pyproject.toml` overrides.

## Configuration

### Where does behave-doctor look for `pyproject.toml`?

1. The path specified by `--config` on the CLI.
2. `pyproject.toml` in the project root (the `PATH` argument to `scan`).
3. `pyproject.toml` in the current working directory.

If no config file is found, all defaults are used.

### Can I use a different config file name?

Yes, with `--config`:

```bash
behave-doctor scan . --config /path/to/my-config.toml
```

The file must be a valid TOML file with a `[tool.behave-doctor]` section.

### Do CLI flags override config file values?

**Yes.** CLI flags always take precedence over `pyproject.toml` values.

## Integration

### Does behave-doctor work with pre-commit?

**Yes.** See [CI/CD > Pre-commit hook](ci-cd.md#pre-commit-hook) for
configuration.

### Does behave-doctor produce SARIF output?

**Yes.** Use `--format sarif`:

```bash
behave-doctor scan . --format sarif -o behave-doctor.sarif
```

See [Reporters > SARIF](reporters.md#sarif-210) for details.

### Can I use behave-doctor as a Python library?

**Yes.** See [Python API](python-api.md) for the full reference.

## Troubleshooting

### "No step definitions found in features/steps/"

This is BD503. It means the steps directory is empty, missing, or contains
no files with `@given`/`@when`/`@then` decorators.

**Fixes:**

1. Verify `steps_dir` in your config points to the correct directory.
2. Ensure your step files use `@given`, `@when`, or `@then` decorators
   (not `@step` or custom decorators).
3. Check that the `.py` files are in the right location.

### "Scan failed: features directory not found"

This produces exit code 2. It means the `features_dir` path doesn't exist.

**Fixes:**

1. Verify `features_dir` in your config points to the correct directory.
2. Pass the correct project path: `behave-doctor scan /path/to/project`.
3. Use `--features-dir` to override: `behave-doctor scan . --features-dir my_features`.

### behave-doctor doesn't find my step definitions

**Possible causes:**

1. **Wrong `steps_dir`** — Check that `steps_dir` points to the directory
   containing your `.py` step files.
2. **Custom decorators** — behave-doctor only recognizes `@given`,
   `@when`, `@then`, and their aliases (`@step`, `@Given`, `@When`,
   `@Then`). If you use custom decorators, they won't be detected.
3. **Dynamic step registration** — Steps registered at runtime (e.g. via
   `behave.register_type` or dynamic `step_matcher` changes) cannot be
   detected statically.

### The SARIF file is empty or has no results

**Possible causes:**

1. **No issues found** — If the scan is clean, the SARIF file will contain
   the tool definition but no results. This is correct behavior.
2. **Severity filtering** — If `min_severity` is set to `error` and there
   are only warnings, no results will be produced.
3. **All rules disabled** — Check that rules aren't disabled in your
   `pyproject.toml`.

### behave-doctor is not detecting circular imports

**Possible causes:**

1. **Imports outside `features/steps/`** — behave-doctor only analyzes
   imports between modules in the steps directory. Imports from outside
   (e.g. `from myapp.models import User`) are not part of the dependency
   graph.
2. **Dynamic imports** — `importlib.import_module()` or `__import__()`
   calls are not detected by AST analysis.

## Performance

### How can I speed up behave-doctor?

behave-doctor is already fast (typically under 1 second). If you have a
very large project:

1. **Disable informational rules** — Set `min_severity = "warning"` to
   skip BD101-104 and BD303.
2. **Run only the rules you care about** — Use `--rules BD301,BD302`.
3. **Exclude `@wip` tags** — Use `exclude_tags` to skip work-in-progress
   scenarios.

### Does behave-doctor cache results?

No. behave-doctor performs a fresh scan on every run. This ensures
deterministic results and avoids stale cache issues in CI.

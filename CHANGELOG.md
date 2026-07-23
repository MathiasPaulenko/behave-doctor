# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2026-07-23

### Fixed

- **Step decorator keyword argument**: `scan_steps` now discovers patterns passed
  as `@given(pattern="...")`, `@when(pattern="...")`, etc.
- **Keyword-aware step matching and duplicate detection**: `Given`/`When`/`Then`
  steps only match definitions registered for that keyword or universal
  `@step` definitions; `And`/`But`/`*` inherit the previous step type.
- **Typed parse/cfparse placeholders**: patterns like `{name:d}` are now
  compiled and their parameters extracted correctly.
- **Scenario and step count expansion**: `ProjectStatistics`, `BD102`,
  `BD103` and `BD203` now count each `Scenario Outline` example row as a
  generated scenario/step, matching Behave's runtime model.
- **CLI `--format` case sensitivity**: `--format JSON`, `--format Sarif`, etc.
  are now accepted.
- **Step matching false positives**: `_match_step` now uses `.fullmatch()`
  instead of `.match()`, preventing exact step patterns from partially matching
  longer feature step text (e.g. `"the user is logged in"` no longer matches
  `"the user is logged in and does more stuff"`).
- **BD503/BD302 duplicate diagnostics**: BD503 (MissingStepModule) now only
  fires when zero step definitions exist. When definitions exist but some
  steps don't match, BD302 already reports them — BD503 no longer duplicates.
- **BD502 `__future__` import false positive**: `from __future__ import
  annotations` is no longer flagged as an unused import. String type
  annotations (forward references) are now checked for imported names.
- **CLI invalid `--severity` traceback**: Invalid severity values now produce
  a clean error message and exit code 2 instead of an unhandled `ValueError`
  traceback.
- **CLI invalid `--format` traceback**: Invalid format values now produce a
  clean error message and exit code 2 instead of an unhandled `ValueError`
  traceback.
- **`main()` exit code propagation**: `main()` now correctly captures the
  return value of `app(standalone_mode=False)` so that `typer.Exit(code=2)`
  raised inside subcommands produces the correct exit code.
- **`detect_cycles` recursion limit**: Converted recursive DFS to iterative
  DFS to prevent `RecursionError` on very large module dependency graphs.
- **JSON reporter missing `exit_code`**: The JSON output now includes the
  `exit_code` field for CI integration.
- **`scan_project(None)` unhelpful error**: Now raises `TypeError` with a
  clear message instead of an obscure internal `TypeError`.
- **`scan_project(nonexistent)` unhelpful error**: Now raises
  `FileNotFoundError` with the path instead of a confusing `ScanError`.
- **`from_pyproject(None)` unhelpful error**: Now raises `TypeError` instead
  of `AttributeError`.
- **`from_pyproject(directory)` unhelpful error**: Now raises
  `IsADirectoryError` instead of `PermissionError`.
- **Config `exclude` as non-dict crash**: `exclude = "string"` in TOML no
  longer crashes — non-dict values are treated as empty.
- **Config `exclude.paths`/`exclude.tags` as non-list crash**: Non-list
  values no longer crash — treated as empty lists.
- **UTF-8 BOM not stripped**: All file reads now use `utf-8-sig` encoding
  to transparently handle BOM-prefixed `.feature` and `.py` files.
- **DOT output injection**: `to_dot` now escapes backslashes, double quotes,
  and newlines in module names to prevent invalid DOT syntax.
- **BD502 string annotation false positive**: String annotations with
  bracketed generics (e.g. `'List[int]'`, `'Optional[str]'`) are now
  correctly parsed for imported names using identifier extraction.
- **Invalid config int values crash rules**: BD401/BD402/BD403/BD203 with
  non-integer config values (e.g. `max_steps = "bad"`) now fall back to
  defaults instead of crashing with `ValueError`.
- **`_extract_module_imports` OSError crash**: Now catches `OSError`
  (permission denied, file not found) in addition to `SyntaxError`.
- **BD403 file read race condition**: `FeatureTooLarge` now catches `OSError`
  when reading feature files, preventing crashes from deleted/locked files.
- **`normalize_step_text` tab handling**: Tabs between keyword and step text
  are now correctly handled (previously only spaces were recognized).
- **JSON reporter non-serializable metadata**: `Path` and `set` objects in
  diagnostic metadata no longer crash the JSON reporter — they are serialized
  via a custom `default` handler.
- **BD502 type comment false positive**: Imports used in `# type: ...`
  comments are now detected via `type_comments=True` in `ast.parse`.
- **`scan_steps` OSError crash**: Now catches `OSError` (permission denied,
  directory with `.py` extension) in addition to `SyntaxError`.
- **`_module_dotted_path` ValueError on symlinks**: Files outside the steps
  directory (via symlinks) are now skipped instead of crashing.

### Changed

- Extracted `location_path` utility into `behave_doctor.model.location` to
  eliminate duplication across 4 rule modules (DRY).
- Extracted `SEVERITY_ORDER` into `behave_doctor.model.enums` to eliminate
  duplication between `core.py` and `reporters/text.py` (DRY).
- Removed dead code: `_decorator_name` function and unused `behave_imported`
  parameter from `step_scanner.py`.
- `detect_cycles` now uses `collections.deque` for O(1) neighbour popping
  instead of `list.pop(0)` which was O(n).
- Added `_get_int_override` helper in `rules/base.py` for safe config int
  extraction with fallback to defaults.

### Added

- `behave_doctor.model.location.location_path` — shared utility for
  extracting a `Path` from a behave-model location object.
- `SEVERITY_ORDER` constant in `behave_doctor.model.enums` — canonical
  severity ordering for filtering and sorting.
- 35 new edge case and regression tests covering step matching, BD502/BD503
  behavior, CLI error handling, empty projects, Unicode features, SARIF
  edge cases, and deep cycle detection.
- 20 additional regression tests for input validation, BOM handling, DOT
  escaping, string annotation parsing, invalid config values, and file
  read error handling.
- 7 more regression tests for tab handling, JSON reporter serialization,
  type comment support, and scan_steps error handling.
- Python 3.14 classifier added to `pyproject.toml`.

### Changed (production readiness)

- **Logging replaces `print` to stderr**: `scan_features` and `scan_steps`
  now use the `logging` module instead of direct `print(..., file=sys.stderr)`
  calls, enabling proper log level control and structured output.
- **`RuleContext` is now frozen**: Prevents accidental mutation during rule
  execution, ensuring immutable scan context.
- **Typing improvements**: `JsonReporter._serialize_diag` and
  `SarifReporter._build_result` now accept `Diagnostic` instead of `Any`.
  `DuplicateStepDefs` uses `dict[str, list[StepDefinition]]` instead of
  `dict[str, list[Any]]`.
- **PyPI metadata enhanced**: Added `Documentation` URL, `OS Independent`
  and `Quality Assurance` classifiers, `license-files` field, and `docs`
  optional dependencies group.
- **Pre-commit hooks updated**: `pre-commit-hooks` to v5.0.0, `ruff` to
  v0.8.0. Added `check-json`, `check-merge-conflict`, and
  `detect-private-key` hooks.
- **CI matrix expanded**: Added Python 3.14 to the test matrix.
- **Release workflow**: Pinned `pypa/gh-action-pypi-publish` to v1.12.4 and
  `softprops/action-gh-release` to v2.2.2 for reproducibility.
- **Docs dependencies**: Moved from inline `pip install` in CI to
  `[project.optional-dependencies.docs]` in `pyproject.toml`.

### Fixed (documentation)

- Corrected `min_severity` default from `"hint"` to `"info"` across README,
  docs/index.md, docs/configuration.md, docs/cli.md, and docs/python-api.md.
- Fixed `ProjectReport` attributes in docs/python-api.md: `scan_duration` →
  `scan_duration_ms`, added `scanned_at` and `project_path`.
- Fixed `Diagnostic` attribute types in docs/python-api.md: `file` is
  `Path | None` (not `str`), `line` is `int | None` (not `int`).
- Fixed `DoctorConfig.min_severity` type from `str` to `Severity` in
  docs/python-api.md, and added `exclude_paths` attribute.
- Fixed `ProjectStatistics` field name from `avg_steps_per_scenario` to
  `average_steps_per_scenario` in docs/python-api.md and docs/reporters.md.
- Fixed `exit_code` description: Python API returns 0 or 1 only (not 2).
- Fixed diagnostic message formats in docs/quickstart.md, docs/rules/*.md,
  and docs/reporters.md to match actual rule output.
- Fixed `list-rules` and `explain` output examples in docs/cli.md and
  docs/quickstart.md to match actual CLI output.
- Fixed SARIF output example: removed non-existent `informationUri` field,
  updated version to 1.1.0.
- Fixed JSON output schema: added missing `exit_code` field.
- Fixed `CONTRIBUTING.md`: `master` → `main` branch reference.
- Updated LICENSE copyright to `2024-present`.
- Fixed diagnostic message formats in docs/rules/dependencies.md (BD501,
  BD502, BD503) and docs/rules/complexity.md (BD402, BD403) to match
  actual rule output.
- Fixed diagnostic message format in docs/rules/coverage.md (BD304) to
  match actual rule output.
- Fixed coverage badge from 96% to 95% in README.md.
- Fixed Python API example to use `Severity.WARNING` enum instead of
  string `"warning"` for `min_severity`.
- Fixed quick start output examples to include BD101-103 info diagnostics
  and correct grammar ("1 error, 1 warning" → "3 errors, 1 warning").
- Updated `docs/installation.md` Python version list to include 3.14.
- Updated `docs/faq.md` Python version list to include 3.14.
- Updated `docs/architecture.md` `RuleContext` attribute name from `graph`
  to `dependency_graph`.
- Fixed `docs/architecture.md` module structure: `diagnostic.py` no longer
  lists `Severity`/`Category` (they live in `enums.py`), added `location.py`.
- Fixed `DoctorConfig.from_pyproject()` to read `exclude_tags` and
  `exclude_paths` from the top level of `[tool.behave-doctor]` in addition
  to the `[tool.behave-doctor.exclude]` sub-table. Previously, top-level
  `exclude_tags` was silently ignored.
- Downgraded `actions/setup-python` from v7 to v5 in all workflows (v7 was
  released 3 days prior and had not been vetted).
- Downgraded `codecov/codecov-action` from v7 to v5 in ci.yml.
- Fixed verbose output example in `docs/reporters.md` to match actual
  metadata format (BD301 has no suggestion, metadata includes `def_id`).
- Fixed JSON diagnostic example in `docs/reporters.md` to match actual
  output (fields sorted alphabetically, `suggestion: null`, correct
  metadata keys).
- Fixed SARIF `$schema` URL in `docs/reporters.md` to match actual output.
- Fixed `docs/configuration.md` `features_dir` and `steps_dir` defaults to
  include trailing slashes.
- Added `min_severity` valid values table to `docs/configuration.md`.

### Added (production readiness)

- **Acknowledgements section** in README.md crediting `behave-model`,
  `typer`, `ruff`, and `mypy`.
- **`make help` target** showing all available Makefile targets.
- **`make check` target** running lint + format-check + test in one command.
- **`make docs` and `make docs-serve` targets** for documentation builds.
- **Cross-platform `make clean`** using Python instead of Unix-only `find`.
- **`.gitignore`** added `.DS_Store` and `Thumbs.db` patterns.
- **`Reporter.format` protocol method docstring** added.
- **`docs/contributing.md`** updated with new Makefile targets.

## [1.1.0] - 2026-07-23

### Changed

- Migrated CLI from `argparse` to `Typer` for richer help output, typed
  command definitions, and better developer experience. All subcommands
  (`scan`, `list-rules`, `explain`, `stats`, `graph`), flags, and exit codes
  remain identical — the migration is fully backwards-compatible.
- Updated PyPI classifier from `Development Status :: 3 - Alpha` to
  `Development Status :: 5 - Production/Stable`.
- Updated documentation navigation from top tabs to expandable sidebar
  (`navigation.sections` + `navigation.expand`) with grouped sections
  (Guide, Rules, Reference, Integrations).
- Updated documentation with comprehensive detail across all pages:
  architecture page, FAQ page, per-rule examples with "What it detects" /
  "How to fix" sections, full CLI reference, JSON/SARIF schemas, and CI/CD
  examples for GitLab, CircleCI, and Jenkins.

### Added

- `typer>=0.12` as a runtime dependency.
- `docs/architecture.md` — internal design, data flow, module structure,
  key abstractions, and design principles.
- `docs/faq.md` — 20+ frequently asked questions covering general usage,
  rules, configuration, integration, and troubleshooting.
- MkDocs extensions: `attr_list`, `md_in_html`, `def_list`, `footnotes`,
  `pymdownx.emoji`.

### Fixed

- GitHub Pages deployment switched from `peaceiris/actions-gh-pages` to
  official GitHub Actions for Pages (`configure-pages`, `upload-pages-artifact`,
  `deploy-pages`).
- CI/docs/release workflows now trigger correctly via `workflow_dispatch`
  in addition to push events.
- Fixed `--version` flag interception by the scan-default logic.

## [1.0.0] - 2026-07-23

### Added

- Initial project scaffold with hatchling build system.
- Core dataclasses: `StepDefinition`, `StepMatch`, `DependencyGraph`,
  `ProjectReport`, `ProjectStatistics`, `DoctorConfig`, `Diagnostic`,
  `Severity`, `Category`.
- Configuration loader (`DoctorConfig.from_pyproject`).
- Project scanner and step scanner (AST-based static analysis).
- Dependency graph builder and circular dependency detection (DFS).
- Rule engine with abstract `Rule` base class and registry.
- 18 built-in diagnostic rules across 5 categories:
  - Structure (BD101-104)
  - Quality (BD201-204)
  - Coverage (BD301-304)
  - Complexity (BD401-403)
  - Dependencies (BD501-503)
- Three reporters: text (colored), JSON, and SARIF 2.1.0.
- Full CLI with `scan`, `list-rules`, `explain`, `stats`, and
  `graph` commands.
- Public Python API (`scan_project`, `ProjectReport`, etc.).
- GitHub Actions CI/CD workflows (ci, release, docs).
- Community files (LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY).
- MkDocs Material documentation site.

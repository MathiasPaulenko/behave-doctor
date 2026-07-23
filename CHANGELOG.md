# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

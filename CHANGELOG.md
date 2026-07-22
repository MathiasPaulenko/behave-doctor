# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- Full argparse CLI with `scan`, `list-rules`, `explain`, `stats`, and
  `graph` commands.
- Public Python API (`scan_project`, `ProjectReport`, etc.).
- GitHub Actions CI/CD workflows (ci, release, docs).
- Community files (LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY).
- MkDocs Material documentation site.

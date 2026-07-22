"""Argparse CLI for behave-doctor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from behave_doctor import __version__
from behave_doctor.cli.formatters import format_report
from behave_doctor.core import build_report
from behave_doctor.graph.builder import build_graph
from behave_doctor.graph.dot import to_dot
from behave_doctor.model.config import DoctorConfig
from behave_doctor.model.enums import Severity
from behave_doctor.rules import get_all_rules, get_rule
from behave_doctor.scanner.project_scanner import ScanError, scan_features
from behave_doctor.scanner.step_scanner import scan_steps

_KNOWN_COMMANDS = {"scan", "list-rules", "explain", "stats", "graph"}


def _add_common_scan_options(parser: argparse.ArgumentParser) -> None:
    """Add options shared by scan/stats/graph subcommands."""
    parser.add_argument("path", nargs="?", default=".", help="Project root directory.")
    parser.add_argument("--features-dir", default=None, help="Relative path to features directory.")
    parser.add_argument("--steps-dir", default=None, help="Relative path to step definitions.")
    parser.add_argument("--config", default=None, help="Path to config file (pyproject.toml).")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="behave-doctor",
        description="Static analysis and diagnostics for Behave BDD suites.",
    )
    parser.add_argument("--version", action="version", version=__version__)

    subparsers = parser.add_subparsers(dest="command")

    scan = subparsers.add_parser("scan", help="Run all rules and report diagnostics.")
    _add_common_scan_options(scan)
    scan.add_argument(
        "--format",
        dest="format",
        choices=["text", "json", "sarif"],
        default="text",
        help="Output format (default: text).",
    )
    scan.add_argument("--output", "-o", default=None, help="Write to file instead of stdout.")
    scan.add_argument("--rules", default=None, help="Comma-separated rule IDs to run.")
    scan.add_argument("--exclude-rules", default=None, help="Comma-separated rule IDs to skip.")
    scan.add_argument(
        "--severity",
        choices=["error", "warning", "info", "hint"],
        default=None,
        help="Minimum severity to report.",
    )
    scan.add_argument("--no-color", action="store_true", help="Disable colored output.")
    scan.add_argument("--quiet", "-q", action="store_true", help="Only show errors.")
    scan.add_argument("--verbose", "-v", action="store_true", help="Show extra context.")

    subparsers.add_parser("list-rules", help="List all available rules.")

    explain = subparsers.add_parser("explain", help="Explain a specific rule.")
    explain.add_argument("rule_id", help="Rule ID to explain.")

    stats = subparsers.add_parser("stats", help="Show project statistics only.")
    _add_common_scan_options(stats)

    graph = subparsers.add_parser("graph", help="Output dependency graph (DOT format).")
    _add_common_scan_options(graph)

    return parser


def _parse_id_list(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def _load_config(args: argparse.Namespace, project_path: Path) -> DoctorConfig:
    if getattr(args, "config", None):
        config = DoctorConfig.from_pyproject(Path(args.config))
    else:
        pyproject = project_path / "pyproject.toml"
        config = DoctorConfig.from_pyproject(pyproject) if pyproject.exists() else DoctorConfig()

    if getattr(args, "features_dir", None):
        config.features_dir = args.features_dir
    if getattr(args, "steps_dir", None):
        config.steps_dir = args.steps_dir
    return config


def _emit(output: str, args: argparse.Namespace) -> None:
    if getattr(args, "output", None):
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)


def _cmd_scan(args: argparse.Namespace) -> int:
    project_path = Path(args.path).resolve()
    config = _load_config(args, project_path)
    min_severity = Severity(args.severity) if args.severity else None

    try:
        report = build_report(
            project_path,
            config,
            rule_ids=_parse_id_list(args.rules),
            exclude_ids=_parse_id_list(args.exclude_rules),
            min_severity=min_severity,
        )
    except ScanError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    output = format_report(
        report,
        fmt=args.format,
        use_color=not args.no_color,
        quiet=args.quiet,
        verbose=args.verbose,
    )
    _emit(output, args)
    return report.exit_code


def _cmd_list_rules() -> int:
    lines: list[str] = []
    for rule in get_all_rules():
        lines.append(
            f"{rule.id}  {rule.severity.value.upper():<8}  "
            f"{rule.category.value:<12}  {rule.name}  -  {rule.description}"
        )
    print("\n".join(lines))
    return 0


def _cmd_explain(rule_id: str) -> int:
    rule = get_rule(rule_id)
    if rule is None:
        print(f"Unknown rule: {rule_id}", file=sys.stderr)
        return 2
    print(f"ID:          {rule.id}")
    print(f"Name:        {rule.name}")
    print(f"Severity:    {rule.severity.value}")
    print(f"Category:    {rule.category.value}")
    print(f"Description: {rule.description}")
    return 0


def _cmd_stats(args: argparse.Namespace) -> int:
    project_path = Path(args.path).resolve()
    config = _load_config(args, project_path)
    try:
        report = build_report(project_path, config)
    except ScanError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    stats = report.statistics
    print(f"Features:                {stats.features}")
    print(f"Scenarios:               {stats.scenarios}")
    print(f"Steps:                   {stats.steps}")
    print(f"Step definitions:        {stats.step_definitions}")
    print(f"Tags:                    {stats.tags}")
    print(f"Total tag usages:        {stats.total_tag_usages}")
    print(f"Avg steps/scenario:      {stats.average_steps_per_scenario}")
    print(f"Unused step definitions: {stats.unused_step_definitions}")
    print(f"Undefined steps:         {stats.undefined_steps}")
    return 0


def _cmd_graph(args: argparse.Namespace) -> int:
    project_path = Path(args.path).resolve()
    config = _load_config(args, project_path)
    try:
        project = scan_features(project_path, config)
    except ScanError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    steps = scan_steps((project_path / config.steps_dir).resolve(), config)
    graph = build_graph(project, steps)
    print(to_dot(graph))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the behave-doctor CLI and return the exit code."""
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)

    # Handle global flags before subcommand interception.
    if not argv or argv[0] in ("--version", "-h", "--help"):
        parser = _build_parser()
        args = parser.parse_args(argv)
        # --help and --version cause SystemExit inside parse_args; if we
        # reach here there's nothing else to do.
        return 0

    # Default to the "scan" subcommand when none is given.
    if argv[0] not in _KNOWN_COMMANDS:
        argv = ["scan", *argv]

    parser = _build_parser()
    args = parser.parse_args(argv)

    command = args.command
    if command == "list-rules":
        return _cmd_list_rules()
    if command == "explain":
        return _cmd_explain(args.rule_id)
    if command == "stats":
        return _cmd_stats(args)
    if command == "graph":
        return _cmd_graph(args)
    return _cmd_scan(args)

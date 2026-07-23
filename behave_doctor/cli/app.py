"""Typer CLI for behave-doctor."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

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

_KNOWN_COMMANDS = {"scan", "list-rules", "explain", "stats", "graph", "--help", "-h", "--version"}

app = typer.Typer(
    name="behave-doctor",
    help="Static analysis and diagnostics for Behave BDD suites.",
    no_args_is_help=False,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit


def _load_config(
    config_path: str | None,
    features_dir: str | None,
    steps_dir: str | None,
    project_path: Path,
) -> DoctorConfig:
    if config_path:
        config = DoctorConfig.from_pyproject(Path(config_path))
    else:
        pyproject = project_path / "pyproject.toml"
        config = DoctorConfig.from_pyproject(pyproject) if pyproject.exists() else DoctorConfig()

    if features_dir:
        config.features_dir = features_dir
    if steps_dir:
        config.steps_dir = steps_dir
    return config


def _parse_id_list(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def _emit(output: str, output_file: str | None) -> None:
    if output_file:
        Path(output_file).write_text(output, encoding="utf-8")
    else:
        typer.echo(output)


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = False,
) -> None:
    """Static analysis and diagnostics for Behave BDD suites."""
    if ctx.invoked_subcommand is None:
        ctx.exit(0)


@app.command()
def scan(
    path: Annotated[Path, typer.Argument(help="Project root directory.")] = Path("."),
    features_dir: Annotated[
        str | None, typer.Option("--features-dir", help="Relative path to features directory.")
    ] = None,
    steps_dir: Annotated[
        str | None, typer.Option("--steps-dir", help="Relative path to step definitions.")
    ] = None,
    config: Annotated[
        str | None, typer.Option("--config", help="Path to config file (pyproject.toml).")
    ] = None,
    fmt: Annotated[
        str,
        typer.Option("--format", help="Output format: text, json, sarif."),
    ] = "text",
    output: Annotated[
        str | None, typer.Option("--output", "-o", help="Write to file instead of stdout.")
    ] = None,
    rules: Annotated[
        str | None, typer.Option("--rules", help="Comma-separated rule IDs to run.")
    ] = None,
    exclude_rules: Annotated[
        str | None, typer.Option("--exclude-rules", help="Comma-separated rule IDs to skip.")
    ] = None,
    severity: Annotated[
        str | None,
        typer.Option("--severity", help="Minimum severity: error, warning, info, hint."),
    ] = None,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable colored output.")] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Only show errors.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show extra context.")] = False,
) -> None:
    """Run all rules and report diagnostics."""
    project_path = path.resolve()
    cfg = _load_config(config, features_dir, steps_dir, project_path)
    min_severity = Severity(severity) if severity else None

    try:
        report = build_report(
            project_path,
            cfg,
            rule_ids=_parse_id_list(rules),
            exclude_ids=_parse_id_list(exclude_rules),
            min_severity=min_severity,
        )
    except ScanError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    formatted = format_report(
        report,
        fmt=fmt,
        use_color=not no_color,
        quiet=quiet,
        verbose=verbose,
    )
    _emit(formatted, output)
    raise typer.Exit(code=report.exit_code)


@app.command("list-rules")
def list_rules() -> None:
    """List all available diagnostic rules."""
    for rule in get_all_rules():
        typer.echo(
            f"{rule.id}  {rule.severity.value.upper():<8}  "
            f"{rule.category.value:<12}  {rule.name}  -  {rule.description}"
        )


@app.command()
def explain(
    rule_id: Annotated[str, typer.Argument(help="Rule ID to explain.")],
) -> None:
    """Show details for a specific rule."""
    rule = get_rule(rule_id)
    if rule is None:
        typer.echo(f"Unknown rule: {rule_id}", err=True)
        raise typer.Exit(code=2)
    typer.echo(f"ID:          {rule.id}")
    typer.echo(f"Name:        {rule.name}")
    typer.echo(f"Severity:    {rule.severity.value}")
    typer.echo(f"Category:    {rule.category.value}")
    typer.echo(f"Description: {rule.description}")


@app.command()
def stats(
    path: Annotated[Path, typer.Argument(help="Project root directory.")] = Path("."),
    features_dir: Annotated[
        str | None, typer.Option("--features-dir", help="Relative path to features directory.")
    ] = None,
    steps_dir: Annotated[
        str | None, typer.Option("--steps-dir", help="Relative path to step definitions.")
    ] = None,
    config: Annotated[
        str | None, typer.Option("--config", help="Path to config file (pyproject.toml).")
    ] = None,
) -> None:
    """Show project statistics only (no diagnostics)."""
    project_path = path.resolve()
    cfg = _load_config(config, features_dir, steps_dir, project_path)

    try:
        report = build_report(project_path, cfg)
    except ScanError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    s = report.statistics
    typer.echo(f"Features:                {s.features}")
    typer.echo(f"Scenarios:               {s.scenarios}")
    typer.echo(f"Steps:                   {s.steps}")
    typer.echo(f"Step definitions:        {s.step_definitions}")
    typer.echo(f"Tags:                    {s.tags}")
    typer.echo(f"Total tag usages:        {s.total_tag_usages}")
    typer.echo(f"Avg steps/scenario:      {s.average_steps_per_scenario}")
    typer.echo(f"Unused step definitions: {s.unused_step_definitions}")
    typer.echo(f"Undefined steps:         {s.undefined_steps}")


@app.command()
def graph(
    path: Annotated[Path, typer.Argument(help="Project root directory.")] = Path("."),
    features_dir: Annotated[
        str | None, typer.Option("--features-dir", help="Relative path to features directory.")
    ] = None,
    steps_dir: Annotated[
        str | None, typer.Option("--steps-dir", help="Relative path to step definitions.")
    ] = None,
    config: Annotated[
        str | None, typer.Option("--config", help="Path to config file (pyproject.toml).")
    ] = None,
) -> None:
    """Output the module dependency graph in DOT format."""
    project_path = path.resolve()
    cfg = _load_config(config, features_dir, steps_dir, project_path)

    try:
        project = scan_features(project_path, cfg)
    except ScanError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    steps = scan_steps((project_path / cfg.steps_dir).resolve(), cfg)
    dep_graph = build_graph(project, steps)
    typer.echo(to_dot(dep_graph))


def main(argv: list[str] | None = None) -> int:
    """Run the behave-doctor CLI and return the exit code."""
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)

    # Default to the "scan" subcommand when none is given.
    if not argv or argv[0] not in _KNOWN_COMMANDS:
        argv = ["scan", *argv]

    try:
        app(args=argv, standalone_mode=False)
    except typer.Exit as exc:
        code = getattr(exc, "exit_code", getattr(exc, "code", None))
        return int(code) if code is not None else 0
    except SystemExit as exc:
        code = getattr(exc, "code", None)
        return int(code) if code is not None else 0
    return 0

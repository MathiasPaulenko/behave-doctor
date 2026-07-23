from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from behave_doctor.cli.app import app, main

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
SAMPLE_PROJECT = FIXTURES / "sample_project"

runner = CliRunner()


def _run(argv: list[str]) -> tuple[int, str, str]:
    """Run the CLI via CliRunner and return (exit_code, stdout, stderr)."""
    result = runner.invoke(app, argv, catch_exceptions=False)
    return result.exit_code, result.stdout, (result.stderr or "")


def _run_main(argv: list[str]) -> int:
    """Run the CLI via main() and return the exit code."""
    return main(argv)


def test_scan_text_report() -> None:
    code, out, _ = _run(["scan", str(SAMPLE_PROJECT), "--no-color"])
    assert code in (0, 1)
    assert "Scanning" in out
    assert "Found" in out


def test_scan_json_format() -> None:
    code, out, _ = _run(["scan", str(SAMPLE_PROJECT), "--format", "json"])
    data = json.loads(out)
    assert "diagnostics" in data
    assert "statistics" in data


def test_scan_sarif_format() -> None:
    code, out, _ = _run(["scan", str(SAMPLE_PROJECT), "--format", "sarif"])
    data = json.loads(out)
    assert data["version"] == "2.1.0"


def test_scan_output_to_file(tmp_path: Path) -> None:
    out_file = tmp_path / "report.txt"
    code, _, _ = _run(["scan", str(SAMPLE_PROJECT), "--no-color", "--output", str(out_file)])
    assert out_file.exists()
    assert "Scanning" in out_file.read_text(encoding="utf-8")


def test_scan_rules_filter() -> None:
    code, out, _ = _run(["scan", str(SAMPLE_PROJECT), "--no-color", "--rules", "BD101"])
    assert "BD101" in out
    assert "BD102" not in out


def test_scan_exclude_rules() -> None:
    code, out, _ = _run(["scan", str(SAMPLE_PROJECT), "--no-color", "--exclude-rules", "BD101"])
    assert "BD101" not in out


def test_scan_severity_filter() -> None:
    code, out, _ = _run(["scan", str(SAMPLE_PROJECT), "--no-color", "--severity", "error"])
    assert "BD101" not in out


def test_list_rules() -> None:
    code, out, _ = _run(["list-rules"])
    assert "BD101" in out
    assert "BD501" in out


def test_explain_rule() -> None:
    code, out, _ = _run(["explain", "BD301"])
    assert "BD301" in out
    assert "unused-step-def" in out


def test_explain_unknown_rule() -> None:
    code, out, err = _run(["explain", "BD999"])
    assert code == 2
    assert "Unknown rule" in (out + err)


def test_stats() -> None:
    code, out, _ = _run(["stats", str(SAMPLE_PROJECT)])
    assert "Features:" in out
    assert "Scenarios:" in out


def test_graph() -> None:
    code, out, _ = _run(["graph", str(SAMPLE_PROJECT)])
    assert "digraph" in out


def test_scan_missing_features_dir_exit_code_two(tmp_path: Path) -> None:
    code, out, err = _run(["scan", str(tmp_path)])
    assert code == 2
    assert "Error:" in (out + err)


def test_scan_default_path_is_cwd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When no subcommand is given, scan is implied with the remaining args."""
    monkeypatch.chdir(SAMPLE_PROJECT)
    code = _run_main(["--no-color"])
    assert code in (0, 1)


def test_version_flag() -> None:
    code, out, _ = _run(["--version"])
    assert code == 0
    assert "1.0.0" in out


def test_main_returns_exit_code() -> None:
    """main() returns an int exit code without calling sys.exit."""
    code = main(["scan", str(SAMPLE_PROJECT), "--no-color"])
    assert isinstance(code, int)
    assert code in (0, 1)

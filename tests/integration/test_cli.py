from __future__ import annotations

import json
from pathlib import Path

import pytest

from behave_doctor.cli.app import main

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
SAMPLE_PROJECT = FIXTURES / "sample_project"


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_scan_text_report(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run([str(SAMPLE_PROJECT), "--no-color"], capsys)
    assert code in (0, 1)
    assert "Scanning" in out
    assert "Found" in out


def test_scan_json_format(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run([str(SAMPLE_PROJECT), "--format", "json"], capsys)
    data = json.loads(out)
    assert "diagnostics" in data
    assert "statistics" in data


def test_scan_sarif_format(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run([str(SAMPLE_PROJECT), "--format", "sarif"], capsys)
    data = json.loads(out)
    assert data["version"] == "2.1.0"


def test_scan_output_to_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_file = tmp_path / "report.txt"
    code, _, _ = _run([str(SAMPLE_PROJECT), "--no-color", "--output", str(out_file)], capsys)
    assert out_file.exists()
    assert "Scanning" in out_file.read_text(encoding="utf-8")


def test_scan_rules_filter(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run([str(SAMPLE_PROJECT), "--no-color", "--rules", "BD101"], capsys)
    # Only BD101 should appear in the output.
    assert "BD101" in out
    assert "BD102" not in out


def test_scan_exclude_rules(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run([str(SAMPLE_PROJECT), "--no-color", "--exclude-rules", "BD101"], capsys)
    assert "BD101" not in out


def test_scan_severity_filter(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run([str(SAMPLE_PROJECT), "--no-color", "--severity", "error"], capsys)
    # No errors in the clean sample project -> no diagnostics lines.
    assert "BD101" not in out


def test_list_rules(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["list-rules"], capsys)
    assert "BD101" in out
    assert "BD501" in out


def test_explain_rule(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["explain", "BD301"], capsys)
    assert "BD301" in out
    assert "unused-step-def" in out


def test_explain_unknown_rule(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = _run(["explain", "BD999"], capsys)
    assert code == 2
    assert "Unknown rule" in err


def test_stats(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["stats", str(SAMPLE_PROJECT)], capsys)
    assert "Features:" in out
    assert "Scenarios:" in out


def test_graph(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["graph", str(SAMPLE_PROJECT)], capsys)
    assert "digraph" in out


def test_scan_missing_features_dir_exit_code_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, _, err = _run([str(tmp_path)], capsys)
    assert code == 2
    assert "Error:" in err


def test_scan_default_path_is_cwd(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(SAMPLE_PROJECT)
    code, out, _ = _run(["--no-color"], capsys)
    assert "Scanning" in out


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    import pytest as _pytest

    with _pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "1.0.0" in out

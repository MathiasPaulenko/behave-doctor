"""SARIF 2.1.0 reporter for GitHub Code Scanning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from behave_doctor import __version__
from behave_doctor.model.diagnostic import Diagnostic
from behave_doctor.model.enums import Severity
from behave_doctor.model.project_report import ProjectReport
from behave_doctor.rules import get_all_rules

_SARIF_SCHEMA = (
    "https://docs.oasis-open.org/sarif/sarif/v2.1.0/cs01/schemas/sarif-schema-2.1.0.json"
)

_SEVERITY_TO_LEVEL: dict[Severity, str] = {
    Severity.ERROR: "error",
    Severity.WARNING: "warning",
    Severity.INFO: "note",
    Severity.HINT: "none",
}


class SarifReporter:
    """Reporter that emits SARIF 2.1.0 JSON for GitHub Code Scanning."""

    def format(self, report: ProjectReport) -> str:
        """Format a ``ProjectReport`` as a SARIF 2.1.0 JSON string."""
        rules = self._build_rules()
        results = [self._build_result(d, report.project_path) for d in report.diagnostics]

        payload: dict[str, Any] = {
            "$schema": _SARIF_SCHEMA,
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "behave-doctor",
                            "version": __version__,
                            "rules": rules,
                        }
                    },
                    "results": results,
                }
            ],
        }
        return json.dumps(payload, indent=2)

    @staticmethod
    def _build_rules() -> list[dict[str, Any]]:
        rules: list[dict[str, Any]] = []
        for rule in get_all_rules():
            rules.append(
                {
                    "id": rule.id,
                    "name": rule.name,
                    "shortDescription": {"text": rule.description},
                    "defaultConfiguration": {"level": _SEVERITY_TO_LEVEL[rule.severity]},
                }
            )
        return rules

    @staticmethod
    def _build_result(diag: Diagnostic, project_path: Path) -> dict[str, Any]:
        uri: str | None = None
        if isinstance(diag.file, Path):
            try:
                uri = diag.file.relative_to(project_path).as_posix()
            except ValueError:
                uri = diag.file.as_posix()

        location: dict[str, Any] = {
            "physicalLocation": {
                "artifactLocation": {"uri": uri or ""},
            }
        }
        if diag.line is not None:
            location["physicalLocation"]["region"] = {"startLine": diag.line}

        return {
            "ruleId": diag.rule_id,
            "level": _SEVERITY_TO_LEVEL[diag.severity],
            "message": {"text": diag.message},
            "locations": [location],
        }

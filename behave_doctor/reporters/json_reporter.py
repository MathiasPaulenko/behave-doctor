"""JSON reporter — structured JSON output for CI integration."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from behave_doctor.model.project_report import ProjectReport


class JsonReporter:
    """Reporter that emits a stable JSON document for CI integration."""

    def format(self, report: ProjectReport) -> str:
        """Format a ``ProjectReport`` as a stable JSON string."""
        payload: dict[str, Any] = {
            "project_path": str(report.project_path),
            "scanned_at": report.scanned_at.isoformat(),
            "scan_duration_ms": report.scan_duration_ms,
            "statistics": asdict(report.statistics),
            "diagnostics": [self._serialize_diag(d) for d in report.diagnostics],
        }
        return json.dumps(payload, sort_keys=True, indent=2)

    @staticmethod
    def _serialize_diag(diag: Any) -> dict[str, Any]:
        return {
            "rule_id": diag.rule_id,
            "rule_name": diag.rule_name,
            "severity": diag.severity.value,
            "category": diag.category.value,
            "message": diag.message,
            "file": diag.file.as_posix() if isinstance(diag.file, Path) else diag.file,
            "line": diag.line,
            "suggestion": diag.suggestion,
            "metadata": diag.metadata,
        }

# C:\MyCode\AbstractWiki\abstract-wiki-architect\tools\language_health\reporting.py
"""
Compatibility + convenience re-exports for the language_health tool.

This project has multiple generations of the language health tooling:
- New modular layout:
    - models.py   (dataclasses)
    - report.py   (cache/report writers + human/json summaries)
    - compile_audit.py / api_runtime.py (audits)
    - cli.py      (orchestrator)

Some older modules historically imported types/utilities from `reporting.py`.
To keep those imports stable (and to offer a single "public surface"),
this module re-exports the canonical symbols from the split modules.

Prefer importing directly from:
  - tools.language_health.models
  - tools.language_health.report
"""

from __future__ import annotations

from .models import CompileResult, HealthRow, OverallStatus, RuntimeResult
from .paths import CACHE_PATH, REPORT_PATH, REPO_ROOT, rel, rel_to_repo
from .report import (
    human_stream,
    print_json_summary,
    print_verbose_start,
    redact_args_for_print,
    save_report,
)

__all__ = [
    # models
    "CompileResult",
    "RuntimeResult",
    "HealthRow",
    "OverallStatus",
    # paths
    "REPO_ROOT",
    "CACHE_PATH",
    "REPORT_PATH",
    "rel_to_repo",
    "rel",
    # reporting utilities
    "redact_args_for_print",
    "human_stream",
    "print_verbose_start",
    "print_json_summary",
    "save_report",
]
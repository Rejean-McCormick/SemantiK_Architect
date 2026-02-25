from __future__ import annotations

from typing import Dict, Sequence

from .config import DEFAULT_TIMEOUT_SEC, PYTHON_EXE
from .models import ToolSpec


def py_script(
    tool_id: str,
    rel_script: str,
    description: str,
    *,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    allow_args: bool = False,
    allowed_flags: Sequence[str] = (),
    allow_positionals: bool = False,
    requires_ai_enabled: bool = False,
    flags_with_value: Sequence[str] = (),
    flags_with_multi_value: Sequence[str] = (),
) -> ToolSpec:
    return ToolSpec(
        tool_id=tool_id,
        description=description,
        rel_target=rel_script,
        cmd=(PYTHON_EXE, "-u", "{target}"),
        timeout_sec=timeout_sec,
        allow_args=allow_args,
        allowed_flags=tuple(allowed_flags),
        allow_positionals=allow_positionals,
        requires_ai_enabled=requires_ai_enabled,
        flags_with_value=tuple(flags_with_value),
        flags_with_multi_value=tuple(flags_with_multi_value),
    )


def maintenance_registry() -> Dict[str, ToolSpec]:
    language_health_timeout = max(DEFAULT_TIMEOUT_SEC, 1800)

    return {
        # --- MAINTENANCE ---
        "language_health": py_script(
            "language_health",
            "tools/language_health.py",
            "Language health/diagnostics utility (status checks and reporting).",
            timeout_sec=language_health_timeout,
            allow_args=True,
            allowed_flags=(
                "--mode",
                "--fast",
                "--parallel",
                "--api-url",
                # NOTE: no --api-key (env-only secret handling)
                "--timeout",
                "--limit",
                "--langs",
                "--no-disable-script",
                "--verbose",
                "--json",
            ),
            allow_positionals=False,
            flags_with_value=(
                "--mode",
                "--parallel",
                "--api-url",
                "--timeout",
                "--limit",
            ),
            flags_with_multi_value=("--langs",),
        ),
        "diagnostic_audit": py_script(
            "diagnostic_audit",
            "tools/diagnostic_audit.py",
            "Forensics audit for stale artifacts / zombie outputs.",
            timeout_sec=DEFAULT_TIMEOUT_SEC,
            allow_args=True,
            allowed_flags=("--verbose", "--json"),
        ),
        "cleanup_root": py_script(
            "cleanup_root",
            "tools/cleanup_root.py",
            "Cleans root artifacts and moves loose GF files into expected folders.",
            timeout_sec=DEFAULT_TIMEOUT_SEC,
            allow_args=True,
            allowed_flags=("--dry-run", "--verbose", "--json"),
        ),
        # --- HEALTH & DEBUGGING ---
        "profiler": py_script(
            "profiler",
            "tools/health/profiler.py",
            "Benchmarks Grammar Engine performance (TPS, Latency, Memory).",
            timeout_sec=300,
            allow_args=True,
            allowed_flags=("--lang", "--iterations", "--update-baseline", "--threshold", "--verbose"),
            allow_positionals=False,
            flags_with_value=("--lang", "--iterations", "--threshold"),
        ),
        "visualize_ast": py_script(
            "visualize_ast",
            "tools/debug/visualize_ast.py",
            "Generates JSON Abstract Syntax Tree from sentence or intent.",
            timeout_sec=60,
            allow_args=True,
            allowed_flags=("--lang", "--sentence", "--ast", "--pgf"),
            allow_positionals=False,
            flags_with_value=("--lang", "--sentence", "--ast", "--pgf"),
        ),
    }
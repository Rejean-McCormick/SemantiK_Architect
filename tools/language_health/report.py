# tools/language_health/report.py
#
# Reporting utilities for the language health tool:
#  - writes compile cache + combined report JSON
#  - prints human summary
#  - optional JSON summary emitter
#  - optional "disable broken compile" bash script generator

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO

from .models import HealthRow
from .paths import CACHE_PATH, REPORT_PATH, REPO_ROOT


def redact_args_for_print(args: argparse.Namespace) -> dict:
    """
    Return a dict version of args suitable for logging.
    Redacts any obvious secret-bearing fields.
    """
    d = dict(vars(args))
    for k in list(d.keys()):
        if k in {"api_key", "token", "secret"} or k.endswith("_key") or k.endswith("_token") or k.endswith("_secret"):
            if d.get(k):
                d[k] = "***redacted***"
    return d


def human_stream(json_mode: bool) -> TextIO:
    """
    In JSON mode, STDOUT must remain valid JSON only.
    """
    return sys.stderr if json_mode else sys.stdout


def print_verbose_start(
    *,
    args: argparse.Namespace,
    trace_id: str,
    compile_src_dir: Path,
    iso_map_path: Optional[Path],
    gf_path: str,
    stream: TextIO,
    api_key_source: Optional[str] = None,
) -> None:
    print("=== LANGUAGE HEALTH CHECKER STARTED ===", file=stream)
    print(f"Trace ID: {trace_id}", file=stream)
    print(f"Args: {redact_args_for_print(args)}", file=stream)
    print(f"CWD: {os.getcwd()}", file=stream)
    print(f"Repo Root: {REPO_ROOT}", file=stream)
    try:
        print(f"Compile Src: {compile_src_dir.relative_to(REPO_ROOT)}", file=stream)
    except Exception:
        print(f"Compile Src: {compile_src_dir}", file=stream)

    if iso_map_path:
        try:
            print(f"ISO Map: {iso_map_path.relative_to(REPO_ROOT)}", file=stream)
        except Exception:
            print(f"ISO Map: {iso_map_path}", file=stream)
    else:
        print("ISO Map: None", file=stream)

    print(f"GF -path: {gf_path}", file=stream)
    print(f"Python: {sys.version.split()[0]}", file=stream)
    if api_key_source:
        print(f"[INFO] API key source: {api_key_source}", file=stream)
    print("-" * 40, file=stream)


def print_json_summary(rows: List[HealthRow], trace_id: str) -> None:
    """
    IMPORTANT: JSON-only output to STDOUT (no banners, no extra lines).
    """
    compile_valid = sum(1 for r in rows if r.compile and r.compile.status == "VALID")
    compile_skipped = sum(1 for r in rows if r.compile and r.compile.status == "SKIPPED")
    compile_broken = sum(1 for r in rows if r.compile and r.compile.status == "BROKEN")
    runtime_pass = sum(1 for r in rows if r.runtime and r.runtime.status == "PASS")
    runtime_fail = sum(1 for r in rows if r.runtime and r.runtime.status == "FAIL")

    summary = {
        "trace_id": trace_id,
        "total_checked": len(rows),
        "paths": {
            "repo_root": str(REPO_ROOT),
            "cache_path": str(CACHE_PATH),
            "report_path": str(REPORT_PATH),
        },
        "status_counts": {
            "OK": sum(1 for r in rows if r.overall_status() == "OK"),
            "FAIL": sum(1 for r in rows if r.overall_status() == "FAIL"),
            "SKIPPED": sum(1 for r in rows if r.overall_status() == "SKIPPED"),
        },
        "compile": {"VALID": compile_valid, "SKIPPED": compile_skipped, "BROKEN": compile_broken},
        "runtime": {"PASS": runtime_pass, "FAIL": runtime_fail},
        "failures": [
            {
                "lang": (r.api_lang or r.gf_lang),
                "reason": (
                    r.compile.error
                    if r.compile and r.compile.status == "BROKEN"
                    else (r.runtime.error if r.runtime else "Unknown")
                ),
            }
            for r in rows
            if r.overall_status() == "FAIL"
        ],
    }
    print(json.dumps(summary, indent=2))


def save_report(
    *,
    rows: List[HealthRow],
    old_compile_cache: Dict[str, Dict[str, Any]],
    write_disable_script: bool,
    stream: TextIO,
    cache_path: Path = CACHE_PATH,
    report_path: Path = REPORT_PATH,
) -> None:
    compile_valid = sum(1 for r in rows if r.compile and r.compile.status in ("VALID", "SKIPPED"))
    compile_broken = sum(1 for r in rows if r.compile and r.compile.status == "BROKEN")
    runtime_pass = sum(1 for r in rows if r.runtime and r.runtime.status == "PASS")
    runtime_fail = sum(1 for r in rows if r.runtime and r.runtime.status == "FAIL")

    new_cache = dict(old_compile_cache or {})
    for row in rows:
        if not row.compile:
            continue
        c = row.compile

        # Don't cache missing sources (avoids "sticky" broken state if file later appears).
        if c.status == "BROKEN":
            err = (c.error or "").strip().lower()
            if err.startswith("source missing"):
                continue

        new_cache[c.filename] = {
            "status": "VALID" if c.status in ("VALID", "SKIPPED") else "BROKEN",
            "hash": c.file_hash,
            "last_check": time.time(),
        }

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    cache_path.write_text(json.dumps(new_cache, indent=2), encoding="utf-8")

    report_obj = {
        "generated_at": time.time(),
        "repo_root": str(REPO_ROOT),
        "summary": {
            "compile_valid_or_skipped": compile_valid,
            "compile_broken": compile_broken,
            "runtime_pass": runtime_pass,
            "runtime_fail": runtime_fail,
            "overall_ok": sum(1 for r in rows if r.overall_status() == "OK"),
            "overall_fail": sum(1 for r in rows if r.overall_status() == "FAIL"),
        },
        "results": [
            {
                "gf_lang": row.gf_lang,
                "api_lang": row.api_lang,
                "overall": row.overall_status(),
                "compile": asdict(row.compile) if row.compile else None,
                "runtime": asdict(row.runtime) if row.runtime else None,
            }
            for row in rows
        ],
    }

    report_path.write_text(json.dumps(report_obj, indent=2), encoding="utf-8")

    print("\n" + "=" * 70, file=stream)
    print("LANGUAGE HEALTH SUMMARY", file=stream)
    print("=" * 70, file=stream)
    print(f"✅ Compile VALID/SKIPPED: {compile_valid}", file=stream)
    print(f"❌ Compile BROKEN       : {compile_broken}", file=stream)
    print(f"✅ Runtime PASS         : {runtime_pass}", file=stream)
    print(f"❌ Runtime FAIL         : {runtime_fail}", file=stream)
    try:
        print(f"📄 Report written to    : {report_path.relative_to(REPO_ROOT)}", file=stream)
    except Exception:
        print(f"📄 Report written to    : {report_path}", file=stream)

    if write_disable_script:
        broken_compile = [r.compile for r in rows if r.compile and r.compile.status == "BROKEN"]
        if broken_compile:
            script_path = REPO_ROOT / "disable_broken_compile.sh"
            with script_path.open("w", encoding="utf-8", newline="\n") as f:
                f.write("#!/bin/bash\n# Generated by tools/language_health\nset -e\n")
                f.write('cd "$(dirname "$0")"\n')
                for c in broken_compile:
                    file_q = shlex.quote(c.filename)
                    err = (c.error or "").strip()
                    # Keep the echo human-readable; mv needs shell-safe quoting.
                    f.write(f"echo 'Disabling {c.filename} ({err})'\n")
                    f.write(f"if [ -f {file_q} ]; then mv {file_q} {file_q}.SKIP; fi\n")
            try:
                os.chmod(script_path, 0o755)
            except Exception:
                pass
            print(f"👉 Compile disable script: {script_path.name}", file=stream)
# tools/language_health/cli.py
#
# Orchestrator CLI for language health checks (modular layout).
#
# What it does:
#   - Compile audit: delegates to tools/language_health/compile_audit.py
#   - Runtime audit: delegates to tools/language_health/api_runtime.py (HTTP client)
#   - Reporting: delegates to tools/language_health/report.py
#
# Outputs:
#   - data/indices/audit_cache.json   (compile cache)
#   - data/reports/audit_report.json  (combined report: compile + runtime)
#
# IMPORTANT:
#   - JSON mode prints *only JSON* to STDOUT.
#   - Human logs always go to STDERR when --json is set.

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False


from . import api_runtime, compile_audit, iso_map, models, paths, report


# -----------------------------------------------------------------------------
# API KEY RESOLUTION (ENV only; avoid leaking secrets)
# -----------------------------------------------------------------------------
def _resolve_api_key() -> tuple[Optional[str], str]:
    """
    Priority:
      1) env ARCHITECT_API_KEY
      2) env SKA_API_KEY
      3) env API_SECRET
      4) env API_KEY
    """
    for name in ("ARCHITECT_API_KEY", "SKA_API_KEY", "API_SECRET", "API_KEY"):
        v = os.environ.get(name)
        if v and v.strip():
            return v.strip(), f"env:{name}"
    return None, "none"


def _normalize_lang_filter(tokens: Optional[Sequence[str]]) -> Set[str]:
    return {t.strip().lower() for t in (tokens or []) if isinstance(t, str) and t.strip()}


def _check_pgf_staleness(stream: Any) -> None:
    """Warns the user if .gfo object caches are newer than the main .pgf binary."""
    from .paths import REPO_ROOT
    
    pgf_path = REPO_ROOT / "gf" / "AbstractWiki.pgf"
    gfo_dir = REPO_ROOT / "gf"
    
    if not pgf_path.exists():
        return

    pgf_mtime = pgf_path.stat().st_mtime
    
    newest_gfo_time = 0.0
    if gfo_dir.exists() and gfo_dir.is_dir():
        for p in gfo_dir.glob("*.gfo"):
            mtime = p.stat().st_mtime
            if mtime > newest_gfo_time:
                newest_gfo_time = mtime

    if newest_gfo_time > pgf_mtime:
        print("\n⚠️  [WARNING] STALE BINARY DETECTED!", file=stream)
        print("⚠️  You have compiled .gfo files that are NEWER than your AbstractWiki.pgf.", file=stream)
        print("⚠️  Runtime tests will not reflect your latest changes. Please run 'compile_pgf' first.\n", file=stream)


# -----------------------------------------------------------------------------
# Conversion helpers (until compile_audit/api_runtime fully adopt models.py)
# -----------------------------------------------------------------------------
def _to_model_compile(r: Any) -> models.CompileResult:
    # compile_audit.CompileResult and models.CompileResult share field names.
    if isinstance(r, models.CompileResult):
        return r
    d = asdict(r) if hasattr(r, "__dataclass_fields__") else dict(r)
    return models.CompileResult(
        gf_lang=str(d.get("gf_lang") or ""),
        filename=str(d.get("filename") or ""),
        status=d.get("status"),  # type: ignore[arg-type]
        error=d.get("error"),
        duration_s=float(d.get("duration_s") or 0.0),
        file_hash=str(d.get("file_hash") or ""),
        iso2=d.get("iso2"),
    )


def _to_model_runtime(r: Any) -> models.RuntimeResult:
    if isinstance(r, models.RuntimeResult):
        return r
    d = asdict(r) if hasattr(r, "__dataclass_fields__") else dict(r)
    return models.RuntimeResult(
        api_lang=str(d.get("api_lang") or ""),
        status=d.get("status"),  # type: ignore[arg-type]
        http_status=d.get("http_status"),
        duration_ms=float(d.get("duration_ms") or 0.0),
        error=d.get("error"),
        sample_text=d.get("sample_text"),
    )


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Hybrid language audit (compile + API runtime)")
    parser.add_argument("--mode", choices=["compile", "api", "both"], default="both")
    parser.add_argument("--fast", action="store_true", help="Compile mode: skip unchanged VALID files (cache).")
    parser.add_argument("--parallel", type=int, default=(os.cpu_count() or 4))
    parser.add_argument("--api-url", default=os.environ.get("ARCHITECT_API_URL", "http://localhost:8000"))
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--limit", type=int, default=0, help="Stop after N items (0 = all).")
    parser.add_argument("--langs", nargs="*", help="Optional subset (e.g. en fr)")
    parser.add_argument("--no-disable-script", action="store_true")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary to STDOUT (human logs to STDERR).")

    args = parser.parse_args(argv)

    trace_id = os.environ.get("TOOL_TRACE_ID", str(uuid.uuid4()))
    stream = report.human_stream(args.json)

    want_compile = args.mode in ("compile", "both")
    want_api = args.mode in ("api", "both")

    lang_filter = _normalize_lang_filter(args.langs)

    # ISO map is used for verbose display + API language fallback only.
    iso2_to_wiki, wiki_to_iso2, iso_map_path = iso_map.load_iso_to_wiki()

    # Resolve compile src dir and gf -path for verbose display.
    compile_src_dir, _label = paths.detect_compile_src_dir()
    gf_path = paths.build_gf_path(compile_src_dir)

    api_key, api_key_src = _resolve_api_key()

    if args.verbose:
        report.print_verbose_start(
            args=args,
            trace_id=trace_id,
            compile_src_dir=compile_src_dir,
            iso_map_path=iso_map_path,
            gf_path=gf_path,
            stream=stream,
            api_key_source=(api_key_src if want_api else None),
        )

    # -------------------------------------------------------------------------
    # COMPILE AUDIT (delegated)
    # -------------------------------------------------------------------------
    compile_rows: Dict[str, models.CompileResult] = {}
    old_cache: Dict[str, Dict[str, Any]] = {}

    if want_compile:
        # NOTE: compile_audit will re-discover paths internally; this is intentional for modularity.
        # The returned cache is the in-memory cache loaded by compile_audit.
        if args.verbose:
            print(
                f"🧱 Compile audit: fast={args.fast}, threads={args.parallel}, limit={args.limit or 'all'}",
                file=stream,
            )

        results_raw, cache_raw, gf_path_used = compile_audit.run_compile_audit(
            compile_src_dir=compile_src_dir,
            use_cache=args.fast,
            timeout_s=90,
            parallel=args.parallel,
            limit=args.limit,
            lang_filter=args.langs,
        )

        old_cache = cache_raw or {}
        if args.verbose and gf_path_used and gf_path_used != gf_path:
            print(f"[INFO] GF -path used by compile auditor: {gf_path_used}", file=stream)

        # Convert to canonical models.
        results = [_to_model_compile(r) for r in results_raw]

        # Stable keying: prefer iso2 (API-facing), else gf_lang.
        for r in results:
            key = (r.iso2 or r.gf_lang or "").strip().lower()
            if not key:
                key = r.filename.lower()
            compile_rows[key] = r

        if args.verbose:
            valid = sum(1 for r in results if r.status == "VALID")
            skipped = sum(1 for r in results if r.status == "SKIPPED")
            broken = sum(1 for r in results if r.status == "BROKEN")
            print(f"[INFO] Compile results: VALID={valid} SKIPPED={skipped} BROKEN={broken}", file=stream)
            for r in sorted(results, key=lambda x: (x.status, (x.iso2 or ""), x.gf_lang, x.filename)):
                icon = "✅" if r.status == "VALID" else "⏩" if r.status == "SKIPPED" else "❌"
                lang_label = (r.iso2 or r.gf_lang or "").ljust(5)
                print(f"   {icon} {lang_label} | {r.status:<7} | {r.filename}", file=stream)
                if r.error and r.status == "BROKEN":
                    print(f"      ERROR: {r.error}", file=stream)

    # -------------------------------------------------------------------------
    # RUNTIME AUDIT (delegated client + orchestrated concurrency here)
    # -------------------------------------------------------------------------
    runtime_rows: Dict[str, models.RuntimeResult] = {}
    api_codes: List[str] = []

    api_checker: Optional[api_runtime.ArchitectApiRuntimeChecker] = None
    if want_api:
        # --> INJECT THE WARNING CHECK HERE <--
        _check_pgf_staleness(stream)

        if args.verbose:
            print(f"🌐 Runtime audit: api_url={args.api_url}, threads={args.parallel}, limit={args.limit or 'all'}", file=stream)

        api_checker = api_runtime.ArchitectApiRuntimeChecker(
            api_url=args.api_url,
            api_key=api_key,
            timeout_s=args.timeout,
            trace_id=trace_id,
        )

        api_codes = api_checker.discover_languages()
        if not api_codes:
            # Fallback when /languages discovery fails.
            if iso2_to_wiki:
                api_codes = sorted(iso2_to_wiki.keys())
                if args.verbose:
                    print(
                        f"[WARN] API discovery returned no languages; falling back to iso_to_wiki.json ({len(api_codes)}).",
                        file=stream,
                    )
            elif args.verbose:
                print("[WARN] API discovery returned no languages and no iso_to_wiki.json found.", file=stream)

        runtime_targets = sorted(set(api_codes))
        if lang_filter:
            runtime_targets = [c for c in runtime_targets if c.lower() in lang_filter]
        if args.limit and args.limit > 0:
            runtime_targets = runtime_targets[: args.limit]

        payload = api_runtime.default_test_payload()

        if runtime_targets and api_checker:
            workers = max(1, int(args.parallel or 1))
            start = time.time()

            if workers == 1:
                for c in runtime_targets:
                    rr = _to_model_runtime(api_checker.check_language(c, payload))
                    runtime_rows[rr.api_lang] = rr
            else:
                with ThreadPoolExecutor(max_workers=workers) as ex:
                    futs = {ex.submit(api_checker.check_language, c, payload): c for c in runtime_targets}
                    for fut in as_completed(futs):
                        rr = _to_model_runtime(fut.result())
                        runtime_rows[rr.api_lang] = rr

            if args.verbose:
                dur_s = time.time() - start
                passed = sum(1 for r in runtime_rows.values() if r.status == "PASS")
                failed = sum(1 for r in runtime_rows.values() if r.status == "FAIL")
                print(f"[INFO] Runtime results: PASS={passed} FAIL={failed} ({dur_s:.2f}s)", file=stream)
                for r in sorted(runtime_rows.values(), key=lambda x: (x.status, x.api_lang)):
                    icon = "✅" if r.status == "PASS" else "❌"
                    print(f"   {icon} {r.api_lang:<5} | {r.status:<4} | {r.duration_ms:.2f}ms", file=stream)
                    if r.error and r.status == "FAIL":
                        print(f"      ERROR: {r.error}", file=stream)

    # -------------------------------------------------------------------------
    # MERGE (canonical HealthRow) + REPORT
    # -------------------------------------------------------------------------
    rows: List[models.HealthRow] = []
    used_api: Set[str] = set()

    # Join compile -> runtime (prefer iso2 as join key).
    for key, c in sorted(compile_rows.items(), key=lambda kv: kv[0]):
        api_lang = (c.iso2 or "").strip().lower() or None
        rt = runtime_rows.get(api_lang) if api_lang else None
        if rt and api_lang:
            used_api.add(api_lang)
        rows.append(models.HealthRow(gf_lang=c.gf_lang or None, api_lang=api_lang, compile=c, runtime=rt))

    # Add runtime-only.
    for api_lang, rt in sorted(runtime_rows.items(), key=lambda kv: kv[0]):
        if api_lang in used_api:
            continue
        rows.append(models.HealthRow(gf_lang=None, api_lang=api_lang, compile=None, runtime=rt))

    # Save report + optional disable script.
    report.save_report(
        rows=rows,
        old_compile_cache=old_cache,
        write_disable_script=(not args.no_disable_script),
        stream=stream,
        cache_path=paths.CACHE_PATH,
        report_path=paths.REPORT_PATH,
    )

    if args.json:
        report.print_json_summary(rows, trace_id)

    return 2 if any(r.overall_status() == "FAIL" for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
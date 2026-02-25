# tools/language_health/runtime_audit.py
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set, TextIO, Tuple

from .api_runtime import ArchitectApiRuntimeChecker, default_test_payload as _default_test_payload
from .models import RuntimeResult


def default_test_payload() -> Dict[str, Any]:
    """
    Compatibility wrapper.

    The authoritative payload shape + headers/response parsing behavior should live in
    tools/language_health/api_runtime.py. This function delegates to that module so
    runtime_audit stays thin.
    """
    return _default_test_payload()


def run_runtime_audit(
    *,
    api_url: str,
    api_key: Optional[str],
    timeout_s: int,
    trace_id: str,
    lang_filter: Set[str],
    parallel: int,
    limit: int,
    verbose: bool,
    stream: TextIO,
    allow_fallback_codes: Optional[List[str]] = None,
) -> Tuple[Dict[str, RuntimeResult], List[str]]:
    """
    Returns:
      - runtime_results: keyed by api_lang
      - api_codes: discovered languages (or fallback if provided and discovery empty)
    """
    if verbose:
        print(f"[INFO] Initializing API client against {api_url}", file=stream)

    api_checker = ArchitectApiRuntimeChecker(
        api_url=api_url,
        api_key=api_key,
        timeout_s=timeout_s,
        trace_id=trace_id,
    )

    api_codes = api_checker.discover_languages()
    if not api_codes and allow_fallback_codes:
        api_codes = list(allow_fallback_codes)

    runtime_targets = sorted(set(api_codes))

    # Normalize filters (runtime codes are typically lowercase, but be defensive)
    lf = {c.strip().lower() for c in (lang_filter or set()) if c and c.strip()}
    if lf:
        runtime_targets = [c for c in runtime_targets if c.lower() in lf]

    if limit and limit > 0:
        runtime_targets = runtime_targets[:limit]

    payload = default_test_payload()
    print(f"🌐 Runtime audit: {len(runtime_targets)} language(s) (threads={max(1, parallel)})", file=stream)

    runtime_results: Dict[str, RuntimeResult] = {}

    workers = max(1, int(parallel or 1))
    if not runtime_targets:
        return runtime_results, api_codes

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(api_checker.check_language, c, payload): c for c in runtime_targets}
        for i, fut in enumerate(as_completed(futs), start=1):
            res = fut.result()
            runtime_results[res.api_lang] = res
            icon = "✅" if res.status == "PASS" else "❌"

            if verbose:
                print(
                    f"   [{i}/{len(runtime_targets)}] {icon} {res.api_lang:<5} | {res.duration_ms:.2f}ms | {res.status}",
                    file=stream,
                )
                if res.error:
                    print(f"     ERROR: {res.error}", file=stream)
            else:
                stream.write(f"\r   [{i}/{len(runtime_targets)}] {icon} {res.api_lang:<5}")
                stream.flush()

    if not verbose:
        print(file=stream)

    return runtime_results, api_codes


__all__ = [
    "ArchitectApiRuntimeChecker",
    "RuntimeResult",
    "default_test_payload",
    "run_runtime_audit",
]
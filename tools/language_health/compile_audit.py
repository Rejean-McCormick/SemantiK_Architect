# tools/language_health/compile_audit.py
#
# Compile audit module (split from tools/language_health/cli.py)
#
# Responsibilities:
#   - Locate per-language Wiki*.gf modules across repo (generated/src, gf/, gf/generated/src)
#   - Load ISO2 <-> Wiki mapping (iso_to_wiki.json) when available
#   - Build a robust GF -path (Prelude.gf auto-discovery + RGL roots + sources)
#   - Compile individual per-language Wiki???.gf files (fast compile check)
#   - Provide compile results + compile target listing
#
# Notes:
#   - This module intentionally does NOT handle runtime/API checks or reporting.
#   - Cache read/write is exposed; higher-level orchestration decides how to merge/store it.

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .gf_path import is_language_wiki_file
from .iso_map import load_iso_to_wiki
from .models import CompileResult
from .paths import (
    CACHE_PATH,
    COMPILE_SRC_CANDIDATES,
    ISO_TO_WIKI_CANDIDATES,
    REPO_ROOT,
    build_gf_path,
    detect_compile_src_dir,
    rel_to_repo,
)

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
GF_BIN_DEFAULT = "gf"
GF_BIN = (os.environ.get("GF_BIN") or GF_BIN_DEFAULT).strip() or GF_BIN_DEFAULT

# Files marked as "disabled" for compile health.
SKIP_SUFFIXES: Tuple[str, ...] = (".SKIP", ".RGL_BROKEN")


# ---------------------------------------------------------------------------
# CACHE
# ---------------------------------------------------------------------------
def load_compile_cache(cache_path: Path = CACHE_PATH) -> Dict[str, Dict[str, Any]]:
    if not cache_path.exists():
        return {}
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_compile_cache(cache: Dict[str, Dict[str, Any]], cache_path: Path = CACHE_PATH) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------------
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    try:
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def first_real_error(text: str, *, max_lines: int = 80) -> str:
    """
    Return the first meaningful GF-ish error line; fallback to the first non-empty line.
    """
    lines = (text or "").splitlines()

    def score(s: str) -> int:
        sl = s.lower()
        if "error:" in sl:
            return 0
        if "syntax error" in sl or "parse error" in sl:
            return 1
        if "constant not found" in sl:
            return 2
        if "does not exist" in sl or "cannot find" in sl:
            return 3
        return 100

    best: Optional[str] = None
    best_score = 10_000

    for raw in lines[:max_lines]:
        s = raw.strip()
        if not s:
            continue
        sc = score(s)
        if sc < best_score:
            best = s
            best_score = sc
            if sc == 0:
                break

    if best:
        return best

    for raw in lines:
        s = raw.strip()
        if s:
            return s
    return "Unknown Error"


def canon_wiki_token(token: str) -> Optional[str]:
    """
    Normalize wiki tokens (Eng/Fre/Ger) from inputs like:
      "eng", "Eng", "WikiEng", "WikiEng.gf", "wikieng.gf"
    Returns canonical "Eng" style or None.
    """
    t = (token or "").strip()
    if not t:
        return None

    tl = t.lower()
    if tl.startswith("wiki"):
        t = t[4:]
    if t.lower().endswith(".gf"):
        t = t[:-3]
    t = t.strip()

    if len(t) != 3 or not t.isalpha():
        return None
    return t[0].upper() + t[1:].lower()


def _gf_lang_from_filename(filename: str) -> str:
    # expects WikiEng.gf -> Eng
    name = filename
    if name.startswith("Wiki"):
        name = name[4:]
    if name.endswith(".gf"):
        name = name[:-3]
    return name


def _dedupe_paths_in_order(paths: Sequence[Path]) -> List[Path]:
    out: List[Path] = []
    seen: set[Path] = set()
    for p in paths:
        try:
            pr = p.resolve()
        except Exception:
            pr = p
        if pr in seen:
            continue
        seen.add(pr)
        out.append(pr)
    return out


def _default_search_dirs(compile_src_dir: Path) -> List[Path]:
    """
    Where we look for Wiki*.gf in priority order.

    Resolution order:
      1) chosen compile_src_dir
      2) other well-known candidates (generated/src, gf/generated/src, gf/)
    """
    candidates: List[Path] = [compile_src_dir]
    for p in COMPILE_SRC_CANDIDATES:
        candidates.append(p)

    existing: List[Path] = []
    for p in candidates:
        try:
            if p.is_dir():
                existing.append(p)
        except Exception:
            continue

    return _dedupe_paths_in_order(existing)


def _resolve_wiki_module_path(wiki: str, search_dirs: Sequence[Path]) -> Tuple[Path, List[Path]]:
    """
    Returns (chosen_path, all_hits_in_priority_order).

    If nothing exists, chosen_path is the "expected" path in the first search dir.
    """
    fname = f"Wiki{wiki}.gf"
    hits: List[Path] = []
    for d in search_dirs:
        p = d / fname
        if p.exists():
            hits.append(p)
    if hits:
        return hits[0], hits

    base = search_dirs[0] if search_dirs else REPO_ROOT
    return (base / fname), []


def _parse_lang_filter(
    lang_filter: Optional[Iterable[str]],
    wiki_to_iso2: Dict[str, str],
) -> Tuple[Optional[set[str]], Optional[set[str]]]:
    """
    Returns (wanted_iso2, wanted_wiki) or (None,None) when no filter.
    """
    raw = [str(t).strip() for t in (lang_filter or []) if t and str(t).strip()]
    if not raw:
        return None, None

    wanted_iso2: set[str] = set()
    wanted_wiki: set[str] = set()

    for tok in raw:
        tl = tok.lower()
        if len(tl) == 2 and tl.isalpha():
            wanted_iso2.add(tl)
            continue
        wiki = canon_wiki_token(tok)
        if wiki:
            wanted_wiki.add(wiki)
            iso2 = wiki_to_iso2.get(wiki)
            if iso2:
                wanted_iso2.add(iso2)

    return wanted_iso2, wanted_wiki


# ---------------------------------------------------------------------------
# COMPILATION
# ---------------------------------------------------------------------------
class LanguageCompilerAuditor:
    """
    Fast per-module compile audit using:
      gf -batch -path <...> -c <WikiX.gf>
    """

    def __init__(
        self,
        compile_src_dir: Optional[Path] = None,
        *,
        use_cache: bool = False,
        cache_path: Path = CACHE_PATH,
        timeout_s: Optional[int] = 90,
        gf_bin: str = GF_BIN,
        search_dirs: Optional[Sequence[Path]] = None,
    ):
        self.repo_root = REPO_ROOT

        if compile_src_dir is None:
            compile_src_dir, _label = detect_compile_src_dir()
        self.compile_src_dir = compile_src_dir.resolve()

        self.search_dirs = _dedupe_paths_in_order(
            list(search_dirs) if search_dirs else _default_search_dirs(self.compile_src_dir)
        )

        self.use_cache = bool(use_cache)
        self.cache_path = cache_path
        self.timeout_s = timeout_s
        self.gf_bin = (gf_bin or GF_BIN_DEFAULT).strip() or GF_BIN_DEFAULT

        # Prelude + RGL + sources: include all search dirs so imports resolve regardless of module location.
        self.gf_path = build_gf_path(self.compile_src_dir, extra=self.search_dirs)

        self.cache: Dict[str, Dict[str, Any]] = load_compile_cache(cache_path)

    def update_cache(self, result: CompileResult) -> None:
        key = result.filename or ""
        if not key:
            return
        self.cache[key] = {
            "hash": result.file_hash,
            "status": "VALID" if result.status in ("VALID", "SKIPPED") else "BROKEN",
            "error": result.error or "",
            "duration_s": float(result.duration_s or 0.0),
            "iso2": result.iso2 or "",
            "gf_lang": result.gf_lang or "",
            "ts": int(time.time()),
        }

    def flush_cache(self) -> None:
        write_compile_cache(self.cache, self.cache_path)

    def check_file(self, iso2: Optional[str], file_path: Path) -> CompileResult:
        # Resolve missing source early (more informative; avoids calling gf with a non-existent file).
        if not file_path.exists():
            rel = rel_to_repo(file_path)
            res = CompileResult(
                gf_lang=_gf_lang_from_filename(file_path.name),
                filename=rel,
                status="BROKEN",
                error=f"Source missing: {rel}",
                file_hash="",
                iso2=iso2,
            )
            self.update_cache(res)
            return res

        filename = file_path.name
        gf_lang = _gf_lang_from_filename(filename)
        rel = rel_to_repo(file_path)
        file_hash = sha256_file(file_path)

        # Cache: skip unchanged VALID
        if self.use_cache:
            cached = self.cache.get(rel) or self.cache.get(filename)
            if isinstance(cached, dict) and cached.get("hash") == file_hash and cached.get("status") == "VALID":
                res = CompileResult(
                    gf_lang=gf_lang,
                    filename=rel,
                    status="SKIPPED",
                    file_hash=file_hash,
                    iso2=iso2,
                )
                self.update_cache(res)
                return res

        cmd = [self.gf_bin, "-batch", "-path", self.gf_path, "-c", rel]

        start = time.time()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_s if self.timeout_s else None,
                check=False,
            )
            dur = time.time() - start

            if proc.returncode == 0:
                res = CompileResult(
                    gf_lang=gf_lang,
                    filename=rel,
                    status="VALID",
                    duration_s=dur,
                    file_hash=file_hash,
                    iso2=iso2,
                )
                self.update_cache(res)
                return res

            merged = (proc.stderr or "") + "\n" + (proc.stdout or "")
            res = CompileResult(
                gf_lang=gf_lang,
                filename=rel,
                status="BROKEN",
                error=first_real_error(merged),
                duration_s=dur,
                file_hash=file_hash,
                iso2=iso2,
            )
            self.update_cache(res)
            return res

        except subprocess.TimeoutExpired:
            res = CompileResult(
                gf_lang=gf_lang,
                filename=rel,
                status="BROKEN",
                error=f"Timeout after {self.timeout_s}s" if self.timeout_s else "Timeout",
                file_hash=file_hash,
                iso2=iso2,
            )
            self.update_cache(res)
            return res
        except FileNotFoundError as e:
            res = CompileResult(
                gf_lang=gf_lang,
                filename=rel,
                status="BROKEN",
                error=f"Missing executable: {e}",
                file_hash=file_hash,
                iso2=iso2,
            )
            self.update_cache(res)
            return res
        except Exception as e:
            res = CompileResult(
                gf_lang=gf_lang,
                filename=rel,
                status="BROKEN",
                error=str(e),
                file_hash=file_hash,
                iso2=iso2,
            )
            self.update_cache(res)
            return res


# ---------------------------------------------------------------------------
# TARGET DISCOVERY
# ---------------------------------------------------------------------------
def list_compile_targets(
    compile_src_dir: Optional[Path] = None,
    lang_filter: Optional[Iterable[str]] = None,
    *,
    search_dirs: Optional[Sequence[Path]] = None,
) -> List[Tuple[Optional[str], Path]]:
    """
    Returns list of (iso2, path). iso2 may be None if mapping is unknown.

    lang_filter tokens may include:
      - ISO2: "en", "fr", "de"
      - Wiki codes: "eng", "fre", "ger"
      - Prefixed/suffixed: "WikiEng", "WikiEng.gf"
    """
    if compile_src_dir is None:
        compile_src_dir, _label = detect_compile_src_dir()
    compile_src_dir = compile_src_dir.resolve()

    iso2_to_wiki, wiki_to_iso2, _src = load_iso_to_wiki(candidates=ISO_TO_WIKI_CANDIDATES)
    wanted_iso2, wanted_wiki = _parse_lang_filter(lang_filter, wiki_to_iso2)

    dirs = _dedupe_paths_in_order(list(search_dirs) if search_dirs else _default_search_dirs(compile_src_dir))

    targets: List[Tuple[Optional[str], Path]] = []

    # If iso map exists, drive by iso2 (API-facing), but resolve actual module path across dirs.
    if iso2_to_wiki:
        for iso2, wiki_raw in sorted(iso2_to_wiki.items()):
            if wanted_iso2 is not None and iso2 not in wanted_iso2:
                continue

            wiki = canon_wiki_token(wiki_raw) or wiki_raw.strip()
            if not wiki:
                expected = (dirs[0] if dirs else compile_src_dir) / "Wiki???.gf"
                targets.append((iso2, expected))
                continue

            chosen, _hits = _resolve_wiki_module_path(wiki, dirs)

            # Honor wiki filter too (when provided)
            if wanted_wiki is not None:
                if (canon_wiki_token(wiki) or wiki) not in wanted_wiki:
                    # allow iso2 filter to include it; wiki filter alone shouldn't exclude
                    if wanted_iso2 is None or iso2 not in wanted_iso2:
                        continue

            targets.append((iso2, chosen))
        return targets

    # Fallback: discover Wiki???.gf across dirs in priority order
    picked: Dict[str, Path] = {}
    for d in dirs:
        try:
            for p in sorted(d.glob("Wiki*.gf")):
                # disabled files
                if any(p.name.endswith(suf) for suf in SKIP_SUFFIXES):
                    continue
                if not is_language_wiki_file(p):
                    continue
                wiki = _gf_lang_from_filename(p.name)  # Eng
                if wiki not in picked:
                    picked[wiki] = p
        except Exception:
            continue

    for wiki, p in sorted(picked.items(), key=lambda kv: kv[0]):
        iso2 = wiki_to_iso2.get(wiki)

        if wanted_iso2 is not None or wanted_wiki is not None:
            keep = False
            if iso2 and wanted_iso2 and iso2 in wanted_iso2:
                keep = True
            if wanted_wiki and wiki in wanted_wiki:
                keep = True
            if not keep:
                continue

        targets.append((iso2, p))

    return targets


# ---------------------------------------------------------------------------
# BATCH RUN (compile-only convenience for cli.py)
# ---------------------------------------------------------------------------
def run_compile_audit(
    *,
    compile_src_dir: Optional[Path] = None,
    use_cache: bool = False,
    timeout_s: Optional[int] = 90,
    gf_bin: str = GF_BIN,
    parallel: int = 4,
    limit: int = 0,
    lang_filter: Optional[Iterable[str]] = None,
) -> Tuple[List[CompileResult], Dict[str, Dict[str, Any]], str]:
    """
    Convenience helper for the CLI/orchestrator.

    Returns:
      - results: list of CompileResult
      - cache: current in-memory cache dict (caller decides write/merge)
      - gf_path: resolved GF -path used for compilation
    """
    auditor = LanguageCompilerAuditor(
        compile_src_dir=compile_src_dir,
        use_cache=use_cache,
        timeout_s=timeout_s,
        gf_bin=gf_bin,
    )

    targets = list_compile_targets(
        compile_src_dir=auditor.compile_src_dir,
        lang_filter=lang_filter,
        search_dirs=auditor.search_dirs,
    )
    if limit and limit > 0:
        targets = targets[:limit]

    workers = max(1, int(parallel or 1))
    results: List[CompileResult] = []

    if not targets:
        return results, auditor.cache, auditor.gf_path

    if workers == 1:
        for iso2, p in targets:
            results.append(auditor.check_file(iso2, p))
        return results, auditor.cache, auditor.gf_path

    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(auditor.check_file, iso2, p): (iso2, p) for iso2, p in targets}
        for fut in as_completed(futs):
            results.append(fut.result())

    return results, auditor.cache, auditor.gf_path


__all__ = [
    "LanguageCompilerAuditor",
    "list_compile_targets",
    "run_compile_audit",
    "load_compile_cache",
    "write_compile_cache",
]
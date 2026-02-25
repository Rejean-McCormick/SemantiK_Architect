# tools/language_health/paths.py
"""
Repo-relative paths and filesystem discovery helpers for language_health.

Goals:
- Keep this module lightweight and stable.
- Expose well-known repo-relative constants (cache/report paths, etc.).
- Provide discovery helpers that work from any CWD.
- Delegate GF-specific search-path construction to tools/language_health/gf_path.py.

Overrides:
- LANGUAGE_HEALTH_REPO_ROOT=/path/to/repo            (force repo root)
- LANGUAGE_HEALTH_COMPILE_SRC=/path/to/compile/src  (force compile source dir)
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

# -----------------------------------------------------------------------------
# Robust import of gf_path
#   - Works when imported as a package module (relative import)
#   - Works when executed in a script context (no parent package)
#   - Also tolerates accidental reuse of this module at tools/language_health.py
#     by searching tools/language_health/gf_path.py as a fallback.
# -----------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent

try:
    # Normal package import
    from .gf_path import (  # type: ignore
        build_gf_path as _build_gf_path,
        detect_repo_root as _detect_repo_root,
        find_prelude_dirs as _find_prelude_dirs,
        is_language_wiki_file as _is_language_wiki_file,
    )
except Exception:
    # Fallback: load gf_path.py by file path.
    # Primary: <this_dir>/gf_path.py
    # Secondary: <this_dir>/language_health/gf_path.py (for mislocated copies)
    _candidates = [
        _THIS_DIR / "gf_path.py",
        _THIS_DIR / "language_health" / "gf_path.py",
    ]
    _gf_path_file = next((p for p in _candidates if p.exists()), None)
    if _gf_path_file is None:
        raise

    _spec = importlib.util.spec_from_file_location("_language_health_gf_path", str(_gf_path_file))
    if _spec is None or _spec.loader is None:
        raise ImportError(f"Failed to load gf_path.py from {_gf_path_file}")

    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)  # type: ignore[attr-defined]

    _build_gf_path = getattr(_mod, "build_gf_path")
    _detect_repo_root = getattr(_mod, "detect_repo_root")
    _find_prelude_dirs = getattr(_mod, "find_prelude_dirs")
    _is_language_wiki_file = getattr(_mod, "is_language_wiki_file")


# -----------------------------------------------------------------------------
# REPO ROOT
# -----------------------------------------------------------------------------
def _resolve_repo_root() -> Path:
    """
    Resolve repo root with an explicit override:
      - LANGUAGE_HEALTH_REPO_ROOT=/path/to/repo

    Fallback:
      - heuristic detection via detect_repo_root()
    """
    override = (os.environ.get("LANGUAGE_HEALTH_REPO_ROOT") or "").strip()
    if override:
        p = Path(override).expanduser().resolve()
        if not p.exists():
            raise ValueError(f"LANGUAGE_HEALTH_REPO_ROOT does not exist: {p}")
        if not p.is_dir():
            raise ValueError(f"LANGUAGE_HEALTH_REPO_ROOT is not a directory: {p}")
        return p

    # Heuristic detection rooted at this module's directory
    return _detect_repo_root(_THIS_DIR)


REPO_ROOT: Path = _resolve_repo_root()


def detect_repo_root(start: Optional[Path] = None) -> Path:
    """
    Public wrapper for gf_path.detect_repo_root, rooted at REPO_ROOT by default.
    Useful for other modules that want consistent behavior.
    """
    return _detect_repo_root(start or REPO_ROOT)


def rel_to_repo(p: Path) -> str:
    """Return repo-relative string if possible, else absolute string."""
    try:
        return str(p.resolve().relative_to(REPO_ROOT.resolve()))
    except Exception:
        return str(p.resolve())


# Backwards compatibility alias (older code used rel()).
rel = rel_to_repo


# -----------------------------------------------------------------------------
# WELL-KNOWN PATHS
# -----------------------------------------------------------------------------
CACHE_PATH: Path = REPO_ROOT / "data" / "indices" / "audit_cache.json"
REPORT_PATH: Path = REPO_ROOT / "data" / "reports" / "audit_report.json"

ISO_TO_WIKI_CANDIDATES: List[Path] = [
    REPO_ROOT / "data" / "config" / "iso_to_wiki.json",
    REPO_ROOT / "config" / "iso_to_wiki.json",
]

# Prefer generated language modules; keep gf/ as a fallback.
COMPILE_SRC_CANDIDATES: List[Path] = [
    REPO_ROOT / "generated" / "src",
    REPO_ROOT / "gf" / "generated" / "src",
    REPO_ROOT / "gf",
]

RGL_ROOT: Path = REPO_ROOT / "gf-rgl" / "src"
RGL_API: Path = REPO_ROOT / "gf-rgl" / "src" / "api"


# -----------------------------------------------------------------------------
# DISCOVERY
# -----------------------------------------------------------------------------
def _compile_src_override() -> Optional[Path]:
    raw = (os.environ.get("LANGUAGE_HEALTH_COMPILE_SRC") or "").strip()
    if not raw:
        return None

    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    else:
        p = p.resolve()

    if not p.exists():
        raise ValueError(f"LANGUAGE_HEALTH_COMPILE_SRC does not exist: {p}")
    if not p.is_dir():
        raise ValueError(f"LANGUAGE_HEALTH_COMPILE_SRC is not a directory: {p}")

    return p


def _score_compile_dir(d: Path, glob_pattern: str) -> int:
    """
    Prefer directories that contain the most *per-language* Wiki???.gf modules.
    """
    try:
        if not d.is_dir():
            return 0
    except Exception:
        return 0

    score = 0
    try:
        for p in d.glob(glob_pattern):
            if not p.is_file():
                continue
            if glob_pattern == "Wiki*.gf":
                if _is_language_wiki_file(p):
                    score += 1
            else:
                score += 1
    except Exception:
        return 0
    return score


def detect_compile_src_dir(
    candidates: Optional[Iterable[Path]] = None,
    glob_pattern: str = "Wiki*.gf",
) -> Tuple[Path, str]:
    """
    Pick the best directory containing per-language Wiki*.gf files.

    Selection rules:
    1) If LANGUAGE_HEALTH_COMPILE_SRC is set, it must be valid and will be used.
    2) Otherwise, choose the candidate with the highest "coverage score"
       (count of per-language Wiki???.gf files).
    3) Fallback to <repo>/gf.

    Returns:
      (dir_path, label) where label is a repo-relative display path when possible.
    """
    forced = _compile_src_override()
    if forced is not None:
        return forced, rel_to_repo(forced)

    cand_list = list(candidates) if candidates is not None else list(COMPILE_SRC_CANDIDATES)

    best: Optional[Path] = None
    best_score = -1

    for d in cand_list:
        try:
            dd = (REPO_ROOT / d).resolve() if not d.is_absolute() else d.resolve()
        except Exception:
            continue

        s = _score_compile_dir(dd, glob_pattern)
        if s > best_score:
            best_score = s
            best = dd

    if best is not None and best_score > 0:
        return best, rel_to_repo(best)

    fallback = (REPO_ROOT / "gf").resolve()
    return fallback, rel_to_repo(fallback)


def find_prelude_dirs(max_hits: int = 5) -> List[Path]:
    """Find directories containing Prelude.gf under likely roots."""
    return _find_prelude_dirs(REPO_ROOT, max_hits=max_hits)


def build_gf_path(compile_src_dir: Path, extra: Optional[Iterable[Path]] = None) -> str:
    """
    Build a gf -path string that makes Prelude.gf and RGL imports discoverable.
    Delegates to gf_path.py to keep logic centralized.
    """
    extra_dirs: Optional[Sequence[Path]] = list(extra) if extra is not None else None
    return _build_gf_path(REPO_ROOT, compile_src_dir, extra_dirs=extra_dirs)


__all__ = [
    "REPO_ROOT",
    "detect_repo_root",
    "CACHE_PATH",
    "REPORT_PATH",
    "ISO_TO_WIKI_CANDIDATES",
    "COMPILE_SRC_CANDIDATES",
    "RGL_ROOT",
    "RGL_API",
    "rel_to_repo",
    "rel",
    "detect_compile_src_dir",
    "find_prelude_dirs",
    "build_gf_path",
]
# tools/language_health/gf_path.py
"""
GF path helpers for the language health tooling.

Centralizes:
  - repo root detection (robust across CWDs / CI)
  - compile source dir detection (generated/src vs gf/generated/src vs gf/)
  - Prelude.gf discovery (to make gf compilation succeed reliably)
  - building the GF -path string (os.pathsep-separated)

Key behaviors:
  - Prefer the *best* compile source dir by sampling/counting language-like Wiki???.gf modules.
  - Always include both repo_root/generated/src and repo_root/gf/generated/src on the GF path if present,
    to avoid "duplicate location" surprises during compilation/import resolution.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple, Union

# Environment overrides (useful in CI / when invoked from an installed package)
_REPO_ROOT_ENV_VARS: Tuple[str, ...] = ("LANGUAGE_HEALTH_REPO_ROOT", "REPO_ROOT")

# Canonical compile source candidates (repo-relative)
_DEFAULT_COMPILE_SRC_REL: Tuple[str, ...] = (
    "generated/src",      # canonical "repo_root/generated/src"
    "gf/generated/src",   # legacy / build-copied location
    "gf",                 # hand-maintained grammars live here too
)

# Roots to search for Prelude.gf if fast paths don’t hit
_DEFAULT_PRELUDE_SEARCH_REL: Tuple[str, ...] = (
    "gf-rgl",
    "gf",
    ".",
)


# ---------------------------------------------------------------------------
# SMALL UTILITIES
# ---------------------------------------------------------------------------
def _as_dir(p: Path) -> Path:
    """If p is a file path, return its parent directory; otherwise return p."""
    try:
        return p if p.is_dir() else p.parent
    except Exception:
        return p.parent


def _parse_path_list_env(var_name: str) -> List[Path]:
    """Parse an os.pathsep-separated env var into Paths. Empty/missing => []"""
    raw = (os.environ.get(var_name) or "").strip()
    if not raw:
        return []
    out: List[Path] = []
    for part in (s.strip() for s in raw.split(os.pathsep)):
        if not part:
            continue
        try:
            out.append(Path(part))
        except Exception:
            continue
    return out


def _rel(repo_root: Path, p: Path) -> str:
    try:
        return str(p.resolve().relative_to(repo_root.resolve()))
    except Exception:
        return str(p)


def is_language_wiki_file(path: Path) -> bool:
    """
    True for per-language Wiki modules like WikiEng.gf, WikiFre.gf, WikiAra.gf.
    False for shared/non-language modules like WikiLexicon.gf.
    """
    name = path.name
    if not (name.startswith("Wiki") and name.endswith(".gf")):
        return False
    core = name[len("Wiki") : -len(".gf")]
    # Project convention here is strict 3-letter alpha suffix (Eng/Fre/Ara/...)
    return len(core) == 3 and core.isalpha()


def _sample_language_module_count(dir_path: Path, cap: int = 200) -> int:
    """
    Count language-like modules in a directory, up to cap (fast).
    This avoids expensive full scans on huge dirs.
    """
    n = 0
    try:
        for p in dir_path.glob("Wiki*.gf"):
            if is_language_wiki_file(p):
                n += 1
                if n >= cap:
                    return cap
    except Exception:
        return n
    return n


# ---------------------------------------------------------------------------
# REPO ROOT DETECTION
# ---------------------------------------------------------------------------
def detect_repo_root(start: Optional[Path] = None) -> Path:
    """
    Detect repo root by walking upwards from `start`.

    Heuristics (first match wins):
      - env var LANGUAGE_HEALTH_REPO_ROOT / REPO_ROOT pointing to an existing dir
      - directory containing both "tools/" and "data/"
      - directory containing ".git"
      - directory containing "pyproject.toml"
      - fallback: parents[2] from this file (repo_root/tools/language_health/gf_path.py)

    Returns an absolute Path.
    """
    for var in _REPO_ROOT_ENV_VARS:
        v = (os.environ.get(var) or "").strip()
        if not v:
            continue
        p = Path(v).expanduser()
        if p.exists() and p.is_dir():
            return p.resolve()

    p0 = (start or Path(__file__)).expanduser()
    p = _as_dir(p0).resolve()

    for parent in [p, *p.parents]:
        try:
            if (parent / "tools").is_dir() and (parent / "data").is_dir():
                return parent
            if (parent / ".git").exists():
                return parent
            if (parent / "pyproject.toml").exists():
                return parent
        except Exception:
            continue

    try:
        return Path(__file__).resolve().parents[2]
    except Exception:
        return Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# COMPILE SRC DETECTION
# ---------------------------------------------------------------------------
def detect_compile_src_dir(
    repo_root: Path,
    candidates: Optional[Sequence[Union[Path, str]]] = None,
) -> Tuple[Path, str]:
    """
    Detect the directory that contains per-language Wiki???.gf modules.

    Returns:
      (compile_src_dir, label_relative_to_repo_root)

    Selection rule (validated against "duplicate gf files" situations):
      - Among candidates that exist, pick the one with the *most* language-like Wiki???.gf files.
      - Break ties by the canonical preference order:
          generated/src > gf/generated/src > gf
      - If nothing exists, fallback to repo_root/gf.
    """
    repo_root = repo_root.resolve()

    # Build candidate list in the canonical order (for tie-breaks).
    cands: List[Path] = []
    if candidates is None:
        cands = [(repo_root / rel).resolve() for rel in _DEFAULT_COMPILE_SRC_REL]
    else:
        for c in candidates:
            try:
                cands.append((repo_root / c).resolve() if isinstance(c, str) else c.resolve())
            except Exception:
                continue

    best: Optional[Path] = None
    best_score = -1

    for p in cands:
        if not p.exists() or not p.is_dir():
            continue
        score = _sample_language_module_count(p, cap=200)
        if score > best_score:
            best = p
            best_score = score

    if best is None:
        fallback = (repo_root / "gf").resolve()
        return fallback, _rel(repo_root, fallback)

    return best, _rel(repo_root, best)


# ---------------------------------------------------------------------------
# PRELUDE DISCOVERY
# ---------------------------------------------------------------------------
def _default_prelude_search_roots(repo_root: Path) -> List[Path]:
    return [(repo_root / rel).resolve() for rel in _DEFAULT_PRELUDE_SEARCH_REL]


@lru_cache(maxsize=16)
def _find_prelude_dirs_cached(repo_root_str: str, max_hits: int = 6) -> Tuple[str, ...]:
    """
    Cached Prelude.gf directory discovery.
    Returns tuple[str] of dir paths to keep cache keys stable.
    """
    repo_root = Path(repo_root_str).resolve()

    found: List[Path] = []
    seen: set[Path] = set()

    # Fast-path common locations in this repo layout.
    common = [
        repo_root / "gf-rgl" / "src" / "prelude" / "Prelude.gf",
        repo_root / "gf-rgl" / "src" / "Prelude.gf",
        repo_root / "gf" / "Prelude.gf",
    ]
    for prelude in common:
        try:
            if prelude.exists():
                d = prelude.parent.resolve()
                if d not in seen:
                    seen.add(d)
                    found.append(d)
        except Exception:
            continue

    if len(found) >= max_hits:
        return tuple(str(p) for p in found[:max_hits])

    # Bounded rglob over a few roots; keep max_hits low.
    for root in _default_prelude_search_roots(repo_root):
        if not root.exists():
            continue
        try:
            for prelude in root.rglob("Prelude.gf"):
                d = prelude.parent.resolve()
                if d not in seen:
                    seen.add(d)
                    found.append(d)
                if len(found) >= max_hits:
                    return tuple(str(p) for p in found[:max_hits])
        except Exception:
            continue

    return tuple(str(p) for p in found)


def find_prelude_dirs(repo_root: Path, max_hits: int = 6) -> List[Path]:
    """
    Public Prelude dir discovery.

    Env hinting:
      - GF_PRELUDE_DIRS: os.pathsep-separated list of directories to try first.

    Returns list[Path] (deduped, existing-only), priority order.
    """
    repo_root = repo_root.resolve()

    hinted = _parse_path_list_env("GF_PRELUDE_DIRS")
    out: List[Path] = []
    seen: set[Path] = set()

    def add_dir(d: Path) -> None:
        try:
            rp = d.expanduser().resolve()
        except Exception:
            return
        if rp in seen:
            return
        if not rp.exists() or not rp.is_dir():
            return
        seen.add(rp)
        out.append(rp)

    for d in hinted:
        add_dir(d)

    for s in _find_prelude_dirs_cached(str(repo_root), max_hits=max_hits):
        add_dir(Path(s))

    return out


# ---------------------------------------------------------------------------
# GF -path BUILDING
# ---------------------------------------------------------------------------
def build_gf_path(
    repo_root: Path,
    compile_src_dir: Path,
    extra_dirs: Optional[Iterable[Path]] = None,
    prelude_max_hits: int = 6,
) -> str:
    """
    Build the os.pathsep-separated GF -path string.

    Includes (in order):
      - discovered Prelude.gf parent dirs
      - gf-rgl/src/prelude (if present as a directory)
      - gf-rgl/src
      - gf-rgl/src/api
      - repo_root/generated/src (if present)
      - repo_root/gf/generated/src (if present)
      - repo_root/gf
      - compile_src_dir
      - repo_root
      - any caller-provided extra_dirs (appended)
      - env GF_PATH_EXTRA (os.pathsep-separated) appended last

    Only existing directories are included; duplicates removed preserving order.
    """
    repo_root = repo_root.resolve()
    compile_src_dir = compile_src_dir.resolve()

    rgl_root = (repo_root / "gf-rgl" / "src").resolve()
    rgl_api = (rgl_root / "api").resolve()
    rgl_prelude_dir = (rgl_root / "prelude").resolve()

    gen_src_root = (repo_root / "generated" / "src").resolve()
    gen_src_under_gf = (repo_root / "gf" / "generated" / "src").resolve()
    gf_dir = (repo_root / "gf").resolve()

    parts: List[Path] = []
    parts.extend(find_prelude_dirs(repo_root, max_hits=prelude_max_hits))

    # If the repo has gf-rgl/src/prelude as a directory, include it explicitly as well.
    parts.extend([rgl_prelude_dir, rgl_root, rgl_api])

    # Include both generated locations if they exist (this is the non-cheap “duplicates” guardrail).
    parts.extend([gen_src_root, gen_src_under_gf])

    # Always include gf + compile src + repo root
    parts.extend([gf_dir, compile_src_dir, repo_root])

    if extra_dirs:
        parts.extend([Path(p) for p in extra_dirs])

    parts.extend(_parse_path_list_env("GF_PATH_EXTRA"))

    out: List[str] = []
    seen: set[Path] = set()
    for p in parts:
        try:
            rp = p.expanduser().resolve()
        except Exception:
            continue
        if rp in seen:
            continue
        if not rp.exists() or not rp.is_dir():
            continue
        seen.add(rp)
        out.append(str(rp))

    return os.pathsep.join(out)
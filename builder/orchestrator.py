# builder/orchestrator.py
from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# --- Setup Paths ---
# builder/orchestrator.py -> builder/ -> repo root
ROOT_DIR = Path(__file__).resolve().parent.parent

# Add repo root to sys.path for imports from utils/, app/, etc.
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# --- Imports ---
try:
    from utils.grammar_factory import generate_safe_mode_grammar  # type: ignore
except Exception:
    generate_safe_mode_grammar = None

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout, force=True)
logger = logging.getLogger("Orchestrator")

# --- Configuration ---
GF_BIN = (os.getenv("GF_BIN", "gf") or "gf").strip()

GF_DIR = ROOT_DIR / "gf"
RGL_DIR = ROOT_DIR / "gf-rgl"
RGL_SRC = RGL_DIR / "src"
RGL_API = RGL_SRC / "api"

# Pinning strategy:
# - Prefer a pin file written by the alignment step (project-owned, deterministic)
# - Else allow env override
# - Else: do NOT hard-fail on an arbitrary baked-in hash
RGL_PIN_FILE = ROOT_DIR / "data" / "config" / "rgl_pin.json"

_ENV_RGL_REF = (os.getenv("ABSTRACTWIKI_RGL_REF") or os.getenv("ABSTRACTWIKI_RGL_COMMIT") or "").strip()
_ENV_ENFORCE = (os.getenv("ABSTRACTWIKI_ENFORCE_RGL_PIN", "") or "").strip().lower()
# If user explicitly sets enforce, honor it. Otherwise enforce only when we have a pin source.
ENFORCE_RGL_PIN: Optional[bool] = None
if _ENV_ENFORCE in ("1", "true", "yes", "on"):
    ENFORCE_RGL_PIN = True
elif _ENV_ENFORCE in ("0", "false", "no", "off"):
    ENFORCE_RGL_PIN = False

# IMPORTANT: there are commonly *two* generated/src locations in this repo layout.
# Canonical is repo_root/generated/src; legacy is repo_root/gf/generated/src.
GENERATED_SRC_ROOT = ROOT_DIR / "generated" / "src"  # canonical
GENERATED_SRC_GF = GF_DIR / "generated" / "src"      # legacy

# SAFE_MODE MUST be isolated to avoid reusing stale HIGH_ROAD Wiki*.gf that import SyntaxXXX.
_SAFE_OVERRIDE = (os.getenv("ABSTRACTWIKI_SAFE_MODE_SRC", "") or "").strip()
if _SAFE_OVERRIDE:
    p = Path(_SAFE_OVERRIDE)
    SAFE_MODE_SRC = (p if p.is_absolute() else (ROOT_DIR / p)).resolve()
else:
    SAFE_MODE_SRC = (ROOT_DIR / "generated" / "safe_mode" / "src").resolve()

SAFE_MODE_MARKER = "-- GENERATED_BY_ABSTRACTWIKI_SAFE_MODE"

# Default generated location (non-safe-mode; used for legacy search/import and some tool interop)
_GENERATED_OVERRIDE = (os.getenv("ABSTRACTWIKI_GENERATED_SRC", "") or "").strip()
if _GENERATED_OVERRIDE:
    p = Path(_GENERATED_OVERRIDE)
    GENERATED_SRC_DEFAULT = (p if p.is_absolute() else (ROOT_DIR / p)).resolve()
else:
    # Prefer canonical generated/src, keep gf/generated/src as fallback only.
    GENERATED_SRC_DEFAULT = GENERATED_SRC_ROOT

LOG_DIR = GF_DIR / "build_logs"

MATRIX_FILE = ROOT_DIR / "data" / "indices" / "everything_matrix.json"
ISO_MAP_FILE = ROOT_DIR / "data" / "config" / "iso_to_wiki.json"

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_SRC_ROOT.mkdir(parents=True, exist_ok=True)
GENERATED_SRC_GF.mkdir(parents=True, exist_ok=True)
GENERATED_SRC_DEFAULT.mkdir(parents=True, exist_ok=True)
SAFE_MODE_SRC.mkdir(parents=True, exist_ok=True)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _run(cmd: List[str], cwd: Path, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    """Run a command with consistent subprocess settings."""
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _relpath(from_dir: Path, target: Path) -> str:
    """Best-effort stable relative path for command arguments/logging."""
    try:
        return str(target.resolve().relative_to(from_dir.resolve()))
    except Exception:
        try:
            return os.path.relpath(str(target), start=str(from_dir))
        except Exception:
            return str(target)


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for s in items:
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _ensure_executable_exists(exe: str) -> None:
    """Fail fast if GF_BIN cannot be resolved."""
    if os.path.isabs(exe) or (Path(exe).exists() and Path(exe).is_file()):
        return
    if shutil.which(exe) is None:
        raise RuntimeError(
            f"GF binary '{exe}' not found on PATH. "
            f"Set GF_BIN or install GF."
        )


def _git_head(repo_dir: Path) -> Optional[str]:
    # Submodules often have .git as a file, not a directory.
    if not (repo_dir / ".git").exists():
        return None
    proc = _run(["git", "rev-parse", "HEAD"], cwd=repo_dir, timeout=10)
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip() or None


def _git_resolve_ref(repo_dir: Path, ref: str) -> Optional[str]:
    """
    Resolve a tag/branch/commit-ish to a full commit SHA.
    Returns None if resolution fails.
    """
    if not ref:
        return None
    if not (repo_dir / ".git").exists():
        return None
    proc = _run(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"], cwd=repo_dir, timeout=10)
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip() or None


def _git_list_tags(repo_dir: Path, limit: int = 30) -> List[str]:
    if not (repo_dir / ".git").exists():
        return []
    proc = _run(["git", "tag", "--list"], cwd=repo_dir, timeout=15)
    if proc.returncode != 0:
        return []
    tags = [t.strip() for t in (proc.stdout or "").splitlines() if t.strip()]
    # Sort "best-effort": keep stable deterministic order
    tags_sorted = sorted(tags, key=lambda s: s.lower())
    if limit > 0:
        return tags_sorted[-limit:]
    return tags_sorted


def _detect_gf_version() -> Optional[Tuple[int, int, int]]:
    """
    Try to parse `gf --version` output as (major, minor, patch).
    Returns None if parsing fails.
    """
    try:
        proc = _run([GF_BIN, "--version"], cwd=ROOT_DIR, timeout=10)
        txt = (proc.stdout or "") + "\n" + (proc.stderr or "")
    except Exception:
        return None

    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", txt)
    if not m:
        return None
    maj = int(m.group(1))
    minu = int(m.group(2))
    pat = int(m.group(3) or "0")
    return (maj, minu, pat)


def _parse_tag_version(tag: str) -> Optional[Tuple[int, int]]:
    """
    Extract (major, minor) from tags like:
      release-3.12, RELEASE-3.9, GF-3.10, gf-3.11, etc.
    """
    m = re.search(r"(?i)(?:release|gf)[-_]?(\d+)\.(\d+)", tag)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)))


def _choose_best_rgl_ref_from_tags(
    gf_ver: Optional[Tuple[int, int, int]],
    tags: List[str],
) -> Optional[str]:
    """
    If we have no explicit pin, we can still *suggest* a good ref:
      - Prefer exact match of installed GF (release-<M>.<m> / GF-<M>.<m>)
      - Else pick the highest <= installed (major, minor) among tags
      - Else pick the highest tag-version we can parse
    This does NOT imply enforcement unless the user configures enforcement.
    """
    if not tags:
        return None

    parsed: List[Tuple[Tuple[int, int], str]] = []
    for t in tags:
        tv = _parse_tag_version(t)
        if tv:
            parsed.append((tv, t))

    if not parsed:
        return None

    parsed.sort(key=lambda x: (x[0][0], x[0][1], x[1].lower()))

    if gf_ver:
        want = (gf_ver[0], gf_ver[1])

        # Exact match first (case-insensitive compare)
        for (tv, t) in reversed(parsed):
            if tv == want:
                return t

        # Best <= installed
        leq = [t for (tv, t) in parsed if tv <= want]
        if leq:
            return leq[-1]

    # Fallback: highest parseable version tag
    return parsed[-1][1]


def _load_rgl_pin_file() -> Dict[str, Any]:
    """
    Supported formats:

    New (preferred):
      {
        "ref": "GF-3.10",
        "resolved": "<full sha>",     # optional
        "updated_at": "YYYY-MM-DD..." # optional
      }

    Backward compat:
      { "commit": "<sha-or-ref>" }
    """
    if not RGL_PIN_FILE.exists():
        return {}
    try:
        data = json.loads(RGL_PIN_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _expected_rgl_pin() -> Tuple[Optional[str], Optional[str], bool, Optional[str]]:
    """
    Returns (expected_ref, expected_commit, enforce, note)

    - expected_ref: tag/branch/sha-ish (preferred human-readable)
    - expected_commit: resolved SHA if we can resolve now
    - enforce: whether to hard-fail on mismatch
    - note: optional informational note (e.g., suggested ref)
    """
    pin = _load_rgl_pin_file()

    ref: Optional[str] = None
    resolved: Optional[str] = None

    if pin:
        ref = str(pin.get("ref") or "").strip() or None
        resolved = str(pin.get("resolved") or "").strip() or None

        # Back-compat: allow "commit" to be a ref-ish as well
        if not ref:
            maybe = str(pin.get("commit") or "").strip()
            if maybe:
                ref = maybe

    # Env override wins (useful for CI)
    if _ENV_RGL_REF:
        ref = _ENV_RGL_REF

    # If we have a ref, resolve it now (authoritative)
    if ref:
        live = _git_resolve_ref(RGL_DIR, ref)
        if live:
            resolved = live

    note: Optional[str] = None

    # No pin configured: we can still *suggest* a likely-good ref from local tags
    if not ref and not resolved and RGL_DIR.exists():
        gf_ver = _detect_gf_version()
        tags = _git_list_tags(RGL_DIR, limit=200)  # get enough to pick best
        suggested = _choose_best_rgl_ref_from_tags(gf_ver, tags)
        if suggested:
            note = f"Suggested RGL ref from local tags: {suggested}"
            # IMPORTANT: suggestion does NOT imply enforcement
            ref = suggested
            # Try resolve, but do not require it
            resolved = _git_resolve_ref(RGL_DIR, suggested) or None

    # Decide enforcement
    if ENFORCE_RGL_PIN is not None:
        enforce = ENFORCE_RGL_PIN
    else:
        # Enforce only when the project has provided an explicit pin source (pin file or env).
        # A heuristic "suggestion" should not block builds.
        enforce = bool(pin) or bool(_ENV_RGL_REF)

    return ref, resolved, enforce, note


# -----------------------------------------------------------------------------
# ISO Map
# -----------------------------------------------------------------------------
def load_iso_map() -> Dict[str, object]:
    """Loads the authoritative ISO -> WikiCode mapping."""
    if not ISO_MAP_FILE.exists():
        logger.warning("⚠️ ISO Map not found. Falling back to TitleCase.")
        return {}
    try:
        data = json.loads(ISO_MAP_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            logger.warning("⚠️ ISO Map is not a JSON object. Falling back to TitleCase.")
            return {}
        return data
    except Exception as e:
        logger.error(f"❌ Failed to load ISO Map: {e}")
        return {}


ISO_MAP = load_iso_map()


def get_gf_name(code: str) -> str:
    """
    Standardizes naming using iso_to_wiki.json when present.
    Input:  'en' (ISO-2) OR 'eng' (legacy ISO-3-like token)
    Output: 'WikiEng.gf' (WikiCode module file)
    """
    if not code:
        return "WikiUnknown.gf"

    raw_val = ISO_MAP.get(code, ISO_MAP.get(code.lower()))
    suffix: Optional[str] = None

    if raw_val:
        if isinstance(raw_val, dict):
            val_str = str(raw_val.get("wiki", "") or "")
        else:
            val_str = str(raw_val)

        # Strip "Wiki" prefix to prevent "WikiWikiEng.gf"
        suffix = val_str.replace("Wiki", "").strip()

    if not suffix:
        suffix = code.title().strip()

    return f"Wiki{suffix}.gf"


def get_wiki_suffix(code: str) -> str:
    """Return 'Eng' from 'en' or 'eng' using ISO_MAP when available."""
    gf = get_gf_name(code)  # WikiEng.gf
    stem = Path(gf).stem    # WikiEng
    return stem.replace("Wiki", "").strip() or code.title().strip()


# -----------------------------------------------------------------------------
# Everything Matrix
# -----------------------------------------------------------------------------
def load_matrix() -> Dict[str, object]:
    if not MATRIX_FILE.exists():
        logger.warning("⚠️  Everything Matrix not found. Defaulting to empty.")
        return {}
    try:
        data = json.loads(MATRIX_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            logger.error("❌ Everything Matrix is not a JSON object. Cannot proceed.")
            return {}
        return data
    except json.JSONDecodeError:
        logger.error("❌ Corrupt Everything Matrix. Cannot proceed.")
        return {}
    except Exception as e:
        logger.error(f"❌ Failed to load Everything Matrix: {e}")
        return {}


# -----------------------------------------------------------------------------
# Cleaning
# -----------------------------------------------------------------------------
def _clean_dir_patterns(root: Path, patterns: Tuple[str, ...]) -> None:
    for pat in patterns:
        for p in root.glob(pat):
            try:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
            except Exception:
                pass


def clean_artifacts() -> None:
    """Best-effort clean of build artifacts across gf/ and generated sources."""
    logger.info("🧹 Cleaning build artifacts...")

    # Remove linked PGF
    pgf = GF_DIR / "AbstractWiki.pgf"
    if pgf.exists():
        try:
            pgf.unlink()
        except Exception:
            pass

    # Remove gfo + temp files from gf dir
    _clean_dir_patterns(GF_DIR, ("*.gfo", "*.log", "*.tmp"))

    # Remove gfo from generated dirs (all known locations)
    for gen_dir in (SAFE_MODE_SRC, GENERATED_SRC_ROOT, GENERATED_SRC_GF, GENERATED_SRC_DEFAULT):
        if gen_dir.exists():
            _clean_dir_patterns(gen_dir, ("*.gfo", "*.log", "*.tmp"))

    # Clear build logs (keep directory)
    if LOG_DIR.exists():
        for p in LOG_DIR.glob("*"):
            try:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
            except Exception:
                pass

    logger.info("🧹 Clean complete.")


# -----------------------------------------------------------------------------
# GF -path construction
# -----------------------------------------------------------------------------
def _discover_rgl_lang_dirs() -> List[Path]:
    """
    GF does not recurse into directories in -path.
    Include all first-level dirs under gf-rgl/src that contain any .gf file somewhere inside.
    """
    if not RGL_SRC.exists():
        return []

    def _has_gf_files(d: Path) -> bool:
        try:
            for _ in d.rglob("*.gf"):
                return True
        except Exception:
            return False
        return False

    dirs: List[Path] = []
    for p in sorted(RGL_SRC.iterdir(), key=lambda x: x.name):
        if not p.is_dir():
            continue
        if p.name == "api":
            continue
        if _has_gf_files(p):
            dirs.append(p)
    return dirs


_RGL_LANG_DIRS: List[Path] = _discover_rgl_lang_dirs()
_GF_PATH_CACHE: Optional[str] = None


def _generated_src_candidates() -> List[Path]:
    """
    Order matters for -path and file shadowing.

    Prefer canonical repo_root/generated/src over repo_root/gf/generated/src.
    SAFE_MODE is always first (isolated).
    """
    cands = [
        SAFE_MODE_SRC,
        GENERATED_SRC_DEFAULT,  # override or canonical root
        GENERATED_SRC_ROOT,     # canonical
        GENERATED_SRC_GF,       # legacy
    ]

    uniq: List[Path] = []
    seen: set[Path] = set()
    for p in cands:
        try:
            rp = p.resolve()
        except Exception:
            rp = p
        if rp in seen:
            continue
        seen.add(rp)
        uniq.append(rp)
    return uniq


def _gf_path_args() -> str:
    """
    CRITICAL: include:
      - gf-rgl/src + gf-rgl/src/api
      - all first-level language dirs under gf-rgl/src (Prelude/SyntaxXXX/etc)
      - gf/ (local modules like AbstractWiki.gf and Wiki*.gf)
      - generated/src dirs (SAFE_MODE + both legacy locations)
      - repo root (last resort)
    """
    global _GF_PATH_CACHE
    if _GF_PATH_CACHE is not None:
        return _GF_PATH_CACHE

    parts: List[str] = [
        str(RGL_SRC.resolve()) if RGL_SRC.exists() else str(RGL_SRC),
        str(RGL_API.resolve()) if RGL_API.exists() else str(RGL_API),
        *[str(d.resolve()) for d in _RGL_LANG_DIRS if d.exists()],
        str(GF_DIR.resolve()) if GF_DIR.exists() else str(GF_DIR),
        *[str(d) for d in _generated_src_candidates() if d.exists()],
        str(ROOT_DIR.resolve()),
    ]

    _GF_PATH_CACHE = os.pathsep.join(_dedupe_keep_order(parts))
    return _GF_PATH_CACHE


# -----------------------------------------------------------------------------
# Alignment / Preflight checks (no side effects)
# -----------------------------------------------------------------------------
def _index_rgl_grammars() -> Dict[str, Path]:
    """
    Build suffix -> Grammar*.gf path map by scanning RGL API + first-level language dirs.
    """
    idx: Dict[str, Path] = {}
    if not RGL_SRC.exists():
        return idx

    scan_roots: List[Path] = []
    if RGL_API.exists():
        scan_roots.append(RGL_API)
    scan_roots.extend([d for d in _RGL_LANG_DIRS if d.exists()])

    for root in scan_roots:
        try:
            for g in root.rglob("Grammar*.gf"):
                stem = g.stem  # GrammarEng
                suffix = stem.replace("Grammar", "").strip()
                if suffix and suffix not in idx:
                    idx[suffix] = g
        except Exception:
            continue

    return idx


_RGL_GRAMMAR_INDEX: Optional[Dict[str, Path]] = None


def _find_bridge_file(suffix: str, grammar_parent: Optional[Path]) -> Optional[Path]:
    """
    Bridge files may live:
      - in generated/src (current tools/bootstrap_tier1.py behavior; preferred)
      - OR next to Grammar*.gf (legacy)
    """
    filename = f"Syntax{suffix}.gf"

    # 1) generated candidates (preferred; project-owned)
    for d in _generated_src_candidates():
        p = d / filename
        if p.exists():
            return p

    # 2) next to the Grammar file (acceptable)
    if grammar_parent:
        p = grammar_parent / filename
        if p.exists():
            return p

    return None


def _require_alignment(tasks: List[Tuple[str, str]]) -> None:
    """
    Fail fast when HIGH_ROAD inputs are likely to fail due to missing RGL or missing Syntax bridges.
    Pin enforcement happens only when explicitly configured (pin file or env).
    """
    _ensure_executable_exists(GF_BIN)

    # Only check bridge existence for HIGH_ROAD tasks
    high_road = [code for (code, strat) in tasks if strat == "HIGH_ROAD"]
    if high_road:
        if not RGL_SRC.exists():
            raise RuntimeError(
                "gf-rgl/src not found.\n"
                f"Expected: {RGL_SRC}\n"
                "Fix:\n"
                "  - Ensure gf-rgl is cloned/available at repo_root/gf-rgl\n"
            )

    expected_ref, expected_commit, enforce_pin, note = _expected_rgl_pin()
    if note:
        logger.info(f"ℹ️  {note}")

    # Pin check (only if explicitly enforced)
    if enforce_pin:
        head = _git_head(RGL_DIR) if RGL_DIR.exists() else None
        if not head:
            raise RuntimeError(
                "gf-rgl HEAD cannot be read.\n"
                "Expected gf-rgl to be a git repository at repo_root/gf-rgl.\n"
            )

        if expected_commit:
            if head != expected_commit:
                tags = _git_list_tags(RGL_DIR, limit=12)
                tags_msg = ("\nRecent tags:\n  " + "\n  ".join(tags)) if tags else ""
                raise RuntimeError(
                    "gf-rgl is not pinned to the expected ref.\n"
                    f"  ref:      {expected_ref or '(none)'}\n"
                    f"  expected: {expected_commit}\n"
                    f"  actual:   {head}\n"
                    "Fix:\n"
                    "  1) run alignment, or\n"
                    f"  2) git -C gf-rgl fetch --tags --prune && git -C gf-rgl checkout {expected_ref or expected_commit}\n"
                    "  3) python tools/bootstrap_tier1.py --force\n"
                    f"{tags_msg}\n"
                )
        else:
            tags = _git_list_tags(RGL_DIR, limit=12)
            tags_msg = ("\nRecent tags:\n  " + "\n  ".join(tags)) if tags else ""
            raise RuntimeError(
                "gf-rgl pin ref cannot be resolved.\n"
                f"  ref: {expected_ref or '(none)'}\n"
                "Fix:\n"
                "  git -C gf-rgl fetch --tags --prune\n"
                "  (or set ABSTRACTWIKI_RGL_REF to a valid tag/branch/commit)\n"
                f"{tags_msg}\n"
            )
    else:
        # If user didn't configure a pin, do not block builds.
        if not (_ENV_RGL_REF or RGL_PIN_FILE.exists()):
            logger.warning(
                "⚠️  RGL pin not configured (no data/config/rgl_pin.json and no ABSTRACTWIKI_RGL_REF). "
                "Build will proceed without deterministic pin enforcement."
            )

    if not high_road:
        return

    global _RGL_GRAMMAR_INDEX
    if _RGL_GRAMMAR_INDEX is None:
        _RGL_GRAMMAR_INDEX = _index_rgl_grammars()

    missing_bridge: List[Tuple[str, str, Optional[Path]]] = []
    for code in high_road:
        suffix = get_wiki_suffix(code)
        grammar_path = _RGL_GRAMMAR_INDEX.get(suffix)
        grammar_parent = grammar_path.parent if grammar_path else None

        bridge = _find_bridge_file(suffix, grammar_parent)
        if not bridge:
            missing_bridge.append((code, suffix, grammar_parent))

    if missing_bridge:
        lines = ["Missing required Syntax bridge files for HIGH_ROAD languages:"]
        for code, suffix, parent in missing_bridge[:30]:
            if parent is None:
                lines.append(
                    f"  - {code}: cannot find Grammar{suffix}.gf in RGL scan; HIGH_ROAD likely unsupported for this suffix"
                )
            else:
                lines.append(
                    f"  - {code}: expected Syntax{suffix}.gf either in generated/src or next to {parent}"
                )
        lines.append("Fix:")
        lines.append("  python tools/bootstrap_tier1.py --force")
        raise RuntimeError("\n".join(lines))


# -----------------------------------------------------------------------------
# Source resolution
# -----------------------------------------------------------------------------
def _safe_mode_source_path(gf_filename: str) -> Path:
    return SAFE_MODE_SRC / gf_filename


def _is_safe_mode_file(p: Path) -> bool:
    try:
        if not p.exists():
            return False
        head = p.read_text(encoding="utf-8", errors="replace")[:4000]
        return SAFE_MODE_MARKER in head
    except Exception:
        return False


def ensure_source_exists(lang_code: str, strategy: str, *, regen_safe: bool = False) -> Path:
    """
    Ensures the .gf source file exists before compilation.
    Returns the path that will be compiled.

    HIGH_ROAD: must exist in gf/
    SAFE_MODE: always lives under SAFE_MODE_SRC to avoid stale HIGH_ROAD contamination.
    """
    gf_filename = get_gf_name(lang_code)

    if strategy == "HIGH_ROAD":
        p = GF_DIR / gf_filename
        if p.exists():
            return p
        raise FileNotFoundError(f"Missing HIGH_ROAD source: {p}")

    # SAFE_MODE: deterministic, isolated, and stamped.
    target_file = _safe_mode_source_path(gf_filename)

    if target_file.exists() and _is_safe_mode_file(target_file) and not regen_safe:
        return target_file

    if not generate_safe_mode_grammar:
        raise RuntimeError(f"Grammar Factory not imported. Cannot generate SAFE_MODE for {lang_code}.")

    logger.info(
        f"🔨 Generating SAFE_MODE grammar for {lang_code} -> {_relpath(ROOT_DIR, target_file)}"
    )

    code = generate_safe_mode_grammar(lang_code)
    stamped = (
        f"{SAFE_MODE_MARKER}\n"
        f"-- lang={lang_code}\n"
        f"-- generated_at={time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"{code}"
    )

    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(stamped, encoding="utf-8")
    return target_file


# -----------------------------------------------------------------------------
# Compilation + Linking
# -----------------------------------------------------------------------------
def compile_gf(lang_code: str, strategy: str, *, regen_safe: bool = False) -> Tuple[subprocess.CompletedProcess, Path]:
    """
    Compiles a single language to a .gfo object file (Phase 1).
    Returns (proc, source_path).
    """
    gf_filename = get_gf_name(lang_code)
    source_path = ensure_source_exists(lang_code, strategy, regen_safe=regen_safe)

    # Use absolute path for -c to avoid cwd sensitivity; GF -path handles imports.
    cmd = [GF_BIN, "-batch", "-path", _gf_path_args(), "-c", str(source_path.resolve())]
    proc = _run(cmd, cwd=GF_DIR)

    if proc.returncode != 0:
        log_path = LOG_DIR / f"{gf_filename}.log"
        try:
            log_path.write_text((proc.stderr or "") + "\n" + (proc.stdout or ""), encoding="utf-8")
        except Exception:
            pass
        logger.error(f"   [STDERR {lang_code}] {(proc.stderr or '').strip()[-500:]}")
        logger.error(f"   [LOG] See {log_path}")

    return proc, source_path


def phase_1_verify(lang_code: str, strategy: str, *, regen_safe: bool = False) -> Tuple[str, bool, str, Optional[Path]]:
    """
    Phase 1: Verify compilation of individual languages.
    Returns: (lang_code, success, msg, source_path)
    """
    try:
        proc, src = compile_gf(lang_code, strategy, regen_safe=regen_safe)
    except Exception as e:
        return (lang_code, False, str(e), None)

    if proc.returncode == 0:
        return (lang_code, True, "OK", src)

    msg = (proc.stderr or "").strip() or (proc.stdout or "").strip() or f"Unknown Error (Exit Code {proc.returncode})"
    return (lang_code, False, msg, src)


@dataclass(frozen=True)
class LinkedLang:
    code: str
    strategy: str
    source_path: Path


def phase_2_link(valid_langs: List[LinkedLang]) -> None:
    """
    Phase 2: Link all valid languages into a single AbstractWiki.pgf binary.
    """
    start_time = time.time()
    logger.info("\n=== PHASE 2: LINKING PGF ===")

    if not valid_langs:
        logger.error("❌ No valid languages to link! Build aborted.")
        raise SystemExit(1)

    # Use explicit per-language paths to avoid ambiguity when duplicates exist.
    targets: List[str] = []
    for ll in valid_langs:
        rel = _relpath(GF_DIR, ll.source_path)
        targets.append(rel)

    cmd = [GF_BIN, "-make", "-path", _gf_path_args(), "-name", "AbstractWiki", "AbstractWiki.gf"] + targets

    logger.info(f"🔗 Linking {len(targets)} languages...")
    logger.info(f"   [CMD] {GF_BIN} -make -path <...> -name AbstractWiki AbstractWiki.gf ... ({len(targets)} files)")

    proc = _run(cmd, cwd=GF_DIR)
    duration = time.time() - start_time

    if proc.returncode == 0:
        logger.info(f"✅ BUILD SUCCESS: AbstractWiki.pgf created in {duration:.2f}s")
        pgf_path = GF_DIR / "AbstractWiki.pgf"
        if pgf_path.exists():
            size_mb = pgf_path.stat().st_size / (1024 * 1024)
            logger.info(f"   [ARTIFACT] {pgf_path} ({size_mb:.2f} MB)")
        else:
            logger.warning("⚠️ Build reported success but AbstractWiki.pgf not found.")
        return

    logger.error(f"❌ LINK FAILED in {duration:.2f}s")
    logger.error(f"   [STDERR]\n{(proc.stderr or '').strip()}")
    raise SystemExit(proc.returncode or 1)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Two-phase GF build orchestrator to produce AbstractWiki.pgf.")
    p.add_argument(
        "--strategy",
        choices=["AUTO", "HIGH_ROAD", "SAFE_MODE"],
        default="AUTO",
        help="AUTO uses everything_matrix.json verdicts. Otherwise force strategy for selected languages.",
    )
    p.add_argument("--langs", nargs="*", default=None, help="Language codes to build.")
    p.add_argument("--clean", action="store_true", help="Clean build artifacts before building.")
    p.add_argument("--verbose", action="store_true", help="Verbose logging.")
    p.add_argument("--max-workers", type=int, default=None, help="Thread pool size for compilation.")

    # Correctness controls
    p.add_argument("--no-preflight", action="store_true", help="Skip RGL pin/bridge preflight checks.")
    p.add_argument("--regen-safe", action="store_true", help="Regenerate SAFE_MODE grammars even if present.")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.clean:
        clean_artifacts()

    start_global = time.time()
    matrix = load_matrix()
    tasks: List[Tuple[str, str]] = []

    if args.strategy != "AUTO":
        langs = args.langs or ["en"]
        forced = args.strategy
        tasks = [(code, forced) for code in langs]
        logger.info(f"⚙️  Forced strategy: {forced} for {len(tasks)} language(s)")
    else:
        if matrix:
            langs_filter = set(args.langs) if args.langs else None
            languages = matrix.get("languages", {})
            if isinstance(languages, dict):
                for code, data in languages.items():
                    if langs_filter is not None and code not in langs_filter:
                        continue
                    verdict = (data or {}).get("verdict", {}) if isinstance(data, dict) else {}
                    strategy = (verdict or {}).get("build_strategy", "SKIP") if isinstance(verdict, dict) else "SKIP"
                    if strategy in ("HIGH_ROAD", "SAFE_MODE"):
                        tasks.append((code, strategy))

        if not tasks:
            logger.info("⚠️  No tasks from matrix. Using bootstrap defaults.")
            tasks = [("en", "HIGH_ROAD")]

    # Preflight: fail fast on known-unfixable HIGH_ROAD problems (no side effects)
    if not args.no_preflight:
        _require_alignment(tasks)

    logger.info("=== PHASE 1: COMPILATION ===")
    logger.info(f"Targeting {len(tasks)} languages")
    logger.info(f"GF_BIN: {GF_BIN}")
    logger.info(f"GF_DIR: {_relpath(ROOT_DIR, GF_DIR)}")
    logger.info(f"SAFE_MODE_SRC: {_relpath(ROOT_DIR, SAFE_MODE_SRC)}")
    logger.info(f"Generated candidates: {', '.join(_relpath(ROOT_DIR, p) for p in _generated_src_candidates())}")

    valid: List[LinkedLang] = []
    phase1_start = time.time()

    max_workers = args.max_workers or min(32, max(1, (os.cpu_count() or 4)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(phase_1_verify, code, strat, regen_safe=args.regen_safe): (code, strat)
            for (code, strat) in tasks
        }

        for future in concurrent.futures.as_completed(futures):
            code, strategy = futures[future]
            try:
                lang, success, msg, src = future.result()
                if success and src is not None:
                    valid.append(LinkedLang(code=lang, strategy=strategy, source_path=src))
                    logger.info(f"  [OK] {lang} ({strategy})")
                else:
                    first = (msg.splitlines()[0] if msg else "Unknown error")[:140]
                    logger.info(f"  [FAIL] {lang} ({strategy}): {first}...")
            except Exception as e:
                logger.error(f"  [ERR] Exception for {code}: {e}")

    logger.info(f"Phase 1 complete in {time.time() - phase1_start:.2f}s")

    # Phase 2
    phase_2_link(valid)

    total_duration = time.time() - start_global
    logger.info("\n=== BUILD SUMMARY ===")
    logger.info(f"Total Duration: {total_duration:.2f}s")
    logger.info(f"Languages: {len(valid)}/{len(tasks)} compiled")

    if len(valid) == 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
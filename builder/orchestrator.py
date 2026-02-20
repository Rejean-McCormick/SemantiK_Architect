# builder/orchestrator.py
from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
RGL_SRC = ROOT_DIR / "gf-rgl" / "src"
RGL_API = RGL_SRC / "api"

# IMPORTANT: there are commonly *two* generated/src locations in this repo layout.
# We support both and choose per-language deterministically.
GENERATED_SRC_ROOT = ROOT_DIR / "generated" / "src"          # repo_root/generated/src
GENERATED_SRC_GF = GF_DIR / "generated" / "src"              # repo_root/gf/generated/src

# Default SAFE_MODE write location (overrideable)
# If set, it must be a directory (absolute or repo-relative).
_GENERATED_OVERRIDE = (os.getenv("ABSTRACTWIKI_GENERATED_SRC", "") or "").strip()
if _GENERATED_OVERRIDE:
    p = Path(_GENERATED_OVERRIDE)
    GENERATED_SRC_DEFAULT = (p if p.is_absolute() else (ROOT_DIR / p)).resolve()
else:
    # Prefer gf/generated/src if it exists (or can be created), otherwise repo_root/generated/src
    GENERATED_SRC_DEFAULT = GENERATED_SRC_GF if (GF_DIR.exists()) else GENERATED_SRC_ROOT

LOG_DIR = GF_DIR / "build_logs"

MATRIX_FILE = ROOT_DIR / "data" / "indices" / "everything_matrix.json"
ISO_MAP_FILE = ROOT_DIR / "data" / "config" / "iso_to_wiki.json"

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_SRC_ROOT.mkdir(parents=True, exist_ok=True)
GENERATED_SRC_GF.mkdir(parents=True, exist_ok=True)
GENERATED_SRC_DEFAULT.mkdir(parents=True, exist_ok=True)


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


# -----------------------------------------------------------------------------
# ISO Map
# -----------------------------------------------------------------------------
def load_iso_map() -> Dict[str, object]:
    """Loads the authoritative ISO -> GF Name mapping."""
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
    Output: 'WikiEng.gf' (wiki/RGL-style 3-letter code module)
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

    # Remove gfo from generated dirs (both locations)
    for gen_dir in (GENERATED_SRC_ROOT, GENERATED_SRC_GF, GENERATED_SRC_DEFAULT):
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
    Order matters: default first, then the other known locations.
    This is used for search and for -path ordering.
    """
    cands = [GENERATED_SRC_DEFAULT, GENERATED_SRC_GF, GENERATED_SRC_ROOT]
    # normalize + dedupe
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
      - generated/src dirs (both repo_root and gf/ variants)
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
# Source resolution (fixes duplicated locations deterministically)
# -----------------------------------------------------------------------------
def _locate_existing_source(gf_filename: str, *, strategy: str) -> Optional[Path]:
    """
    Return the exact file path that should be used for a given language + strategy.

    HIGH_ROAD: prefers gf/WikiX.gf
    SAFE_MODE: prefers generated dirs (default ordering)
    """
    if strategy == "HIGH_ROAD":
        p = GF_DIR / gf_filename
        if p.exists():
            return p

        # If someone accidentally generated into generated/src but expects HIGH_ROAD, be strict:
        # return None and let the caller fail loudly (so the layout mismatch gets fixed).
        return None

    # SAFE_MODE: search generated candidates
    for d in _generated_src_candidates():
        p = d / gf_filename
        if p.exists():
            return p
    return None


def ensure_source_exists(lang_code: str, strategy: str) -> Path:
    """
    Ensures the .gf source file exists before compilation.
    Returns the path that will be compiled.
    """
    gf_filename = get_gf_name(lang_code)

    # HIGH_ROAD: must exist in gf/
    if strategy == "HIGH_ROAD":
        p = GF_DIR / gf_filename
        if p.exists():
            return p
        raise FileNotFoundError(f"Missing HIGH_ROAD source: {p}")

    # SAFE_MODE: if exists anywhere in generated candidates, use it
    existing = _locate_existing_source(gf_filename, strategy="SAFE_MODE")
    if existing is not None:
        return existing

    # Else generate into default generated dir
    target_file = GENERATED_SRC_DEFAULT / gf_filename
    logger.info(f"🔨 Generating grammar for {lang_code} -> {target_file.name} (Factory @ {target_file.parent})...")

    if not generate_safe_mode_grammar:
        raise RuntimeError(f"Grammar Factory not imported. Cannot generate {lang_code}.")

    code = generate_safe_mode_grammar(lang_code)
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(code, encoding="utf-8")
    return target_file


# -----------------------------------------------------------------------------
# Compilation + Linking
# -----------------------------------------------------------------------------
def compile_gf(lang_code: str, strategy: str) -> Tuple[subprocess.CompletedProcess, Path]:
    """
    Compiles a single language to a .gfo object file (Phase 1).
    Returns (proc, source_path).
    """
    gf_filename = get_gf_name(lang_code)

    try:
        source_path = ensure_source_exists(lang_code, strategy)
    except Exception as e:
        # Create a fake proc-like object? Keep it simple: raise and let caller handle.
        raise e

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


def phase_1_verify(lang_code: str, strategy: str) -> Tuple[str, bool, str, Optional[Path]]:
    """
    Phase 1: Verify compilation of individual languages.
    Returns: (lang_code, success, msg, source_path)
    """
    try:
        proc, src = compile_gf(lang_code, strategy)
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
    # All args are relative-to-gf where possible (nicer logs), but absolute is fine too.
    targets: List[str] = []
    for ll in valid_langs:
        # If the source lives under gf/, pass a gf-relative path.
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
        langs = args.langs or ["eng"]
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
            tasks = [("eng", "HIGH_ROAD")]

    logger.info("=== PHASE 1: COMPILATION ===")
    logger.info(f"Targeting {len(tasks)} languages")
    logger.info(f"GF_BIN: {GF_BIN}")
    logger.info(f"GF_DIR: {_relpath(ROOT_DIR, GF_DIR)}")
    logger.info(f"Generated candidates: {', '.join(_relpath(ROOT_DIR, p) for p in _generated_src_candidates())}")

    valid: List[LinkedLang] = []
    phase1_start = time.time()

    max_workers = args.max_workers or min(32, max(1, (os.cpu_count() or 4)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(phase_1_verify, code, strat): (code, strat) for (code, strat) in tasks}

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
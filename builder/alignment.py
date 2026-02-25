# builder/alignment.py
from __future__ import annotations

"""
Alignment (GF/RGL) utilities.

Purpose
- Pin gf-rgl to a known-good commit (GF 3.12-compatible snapshot).
- Purge compiled artifacts (.gfo) that can cause version skew.
- Run Tier-1 bootstrap to generate bridge Syntax*.gf + app Wiki*.gf.

This module is intended to be invoked by:
- scripts/align_system.py (thin wrapper)
- manage.py align (recommended)
- CI preflight (optional)

Design goals
- Deterministic, idempotent, fail-fast
- No hidden "magic": default behavior is safe
- Minimal dependencies (stdlib only)
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger("alignment")


# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

DEFAULT_GF_RGL_COMMIT = "e0a2215"  # From ADR-001 (GF 3.12 stable snapshot)
DEFAULT_STATE_PATH = Path("data/indices/alignment_state.json")


@dataclass(frozen=True)
class AlignmentConfig:
    repo_root: Path
    gf_rgl_dir: Path
    gf_rgl_commit: str = DEFAULT_GF_RGL_COMMIT
    python_exe: str = sys.executable

    # Behavior flags
    dry_run: bool = False
    force: bool = False
    allow_dirty: bool = False

    # Scope controls
    langs: Optional[list[str]] = None  # ISO codes (as in everything_matrix)
    bootstrap_only: bool = False       # skip git pin + purge; just bootstrap
    purge_only: bool = False           # skip git pin + bootstrap; just purge

    # Output
    state_path: Path = DEFAULT_STATE_PATH


class AlignmentError(RuntimeError):
    pass


# -----------------------------------------------------------------------------
# Subprocess helpers
# -----------------------------------------------------------------------------

def _run(cmd: list[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    logger.debug("RUN: %s (cwd=%s)", " ".join(cmd), str(cwd) if cwd else None)
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except FileNotFoundError as e:
        raise AlignmentError(f"Command not found: {cmd[0]}") from e

    if check and proc.returncode != 0:
        raise AlignmentError(
            "Command failed:\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  cwd: {cwd}\n"
            f"  rc:  {proc.returncode}\n"
            f"  out: {proc.stdout.strip()}\n"
            f"  err: {proc.stderr.strip()}\n"
        )
    return proc


def _is_git_repo(path: Path) -> bool:
    return (path / ".git").exists() or (path / ".git").is_dir()


def _git(gf_rgl_dir: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return _run(["git", *args], cwd=gf_rgl_dir, check=check)


# -----------------------------------------------------------------------------
# Git pinning
# -----------------------------------------------------------------------------

def get_gf_rgl_head(gf_rgl_dir: Path) -> str:
    proc = _git(gf_rgl_dir, ["rev-parse", "HEAD"], check=True)
    return proc.stdout.strip()


def is_dirty(gf_rgl_dir: Path) -> bool:
    proc = _git(gf_rgl_dir, ["status", "--porcelain"], check=True)
    return bool(proc.stdout.strip())


def ensure_gf_rgl_commit(cfg: AlignmentConfig) -> None:
    if cfg.bootstrap_only or cfg.purge_only:
        return

    if not cfg.gf_rgl_dir.exists():
        raise AlignmentError(f"gf-rgl directory missing: {cfg.gf_rgl_dir}")

    if not _is_git_repo(cfg.gf_rgl_dir):
        raise AlignmentError(f"gf-rgl is not a git repo: {cfg.gf_rgl_dir}")

    if is_dirty(cfg.gf_rgl_dir) and not (cfg.allow_dirty or cfg.force):
        raise AlignmentError(
            "gf-rgl has uncommitted changes. Refusing to change commit.\n"
            "Use --allow-dirty to proceed without checkout, or --force to override."
        )

    head = get_gf_rgl_head(cfg.gf_rgl_dir)
    if head.startswith(cfg.gf_rgl_commit) or head == cfg.gf_rgl_commit:
        logger.info("gf-rgl already at commit %s (%s)", cfg.gf_rgl_commit, head[:12])
        return

    logger.info("Pinning gf-rgl to commit %s (was %s)", cfg.gf_rgl_commit, head[:12])
    if cfg.dry_run:
        return

    # Best-effort fetch (won't fail if offline); then checkout detached.
    _git(cfg.gf_rgl_dir, ["fetch", "--all", "--tags"], check=False)
    _git(cfg.gf_rgl_dir, ["checkout", "--detach", cfg.gf_rgl_commit], check=True)


# -----------------------------------------------------------------------------
# Purge artifacts
# -----------------------------------------------------------------------------

def purge_gfo(repo_root: Path, dry_run: bool = False) -> int:
    """
    Deletes all .gfo files under repo_root (including gf-rgl and generated dirs).
    This is intentionally broad: stale .gfo is a common source of mismatch errors.
    """
    count = 0
    for p in repo_root.rglob("*.gfo"):
        count += 1
        if dry_run:
            continue
        try:
            p.unlink()
        except FileNotFoundError:
            pass
        except Exception as e:
            raise AlignmentError(f"Failed to delete {p}: {e}") from e
    logger.info("Purged %d .gfo file(s)", count)
    return count


def purge_build_logs(repo_root: Path, dry_run: bool = False) -> int:
    """
    Optional: remove build logs to reduce confusion when iterating.
    Safe to ignore errors.
    """
    candidates = [
        repo_root / "gf" / "build_logs",
        repo_root / "gf" / "build-logs",
        repo_root / "build_logs",
        repo_root / "build-logs",
    ]
    removed = 0
    for d in candidates:
        if not d.exists() or not d.is_dir():
            continue
        for p in d.rglob("*.log"):
            removed += 1
            if dry_run:
                continue
            try:
                p.unlink()
            except Exception:
                pass
    if removed:
        logger.info("Purged %d build log(s)", removed)
    return removed


# -----------------------------------------------------------------------------
# Bootstrap Tier-1 bridges + app grammars
# -----------------------------------------------------------------------------

def run_bootstrap_tier1(cfg: AlignmentConfig) -> None:
    """
    Invokes tools/bootstrap_tier1.py to generate:
    - gf-rgl/src/<lang-folder>/Syntax<suffix>.gf (bridge instance)
    - gf/Wiki<iso>.gf app grammar for Tier-1
    """
    if cfg.purge_only:
        return

    tool = cfg.repo_root / "tools" / "bootstrap_tier1.py"
    if not tool.exists():
        raise AlignmentError(f"Missing bootstrap tool: {tool}")

    cmd = [cfg.python_exe, str(tool)]
    if cfg.dry_run:
        cmd.append("--dry-run")
    if cfg.force:
        cmd.append("--force")
    if cfg.langs:
        cmd.extend(["--langs", ",".join([l.strip().lower() for l in cfg.langs if l.strip()])])

    logger.info("Bootstrapping Tier-1 bridges/app grammars via %s", tool)
    if cfg.dry_run:
        _run(cmd, cwd=cfg.repo_root, check=False)
        return
    _run(cmd, cwd=cfg.repo_root, check=True)


# -----------------------------------------------------------------------------
# State (optional but useful for CI / debugging)
# -----------------------------------------------------------------------------

def write_state(cfg: AlignmentConfig, extra: Optional[dict] = None) -> None:
    if cfg.dry_run:
        return

    state = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "gf_rgl_commit": cfg.gf_rgl_commit,
        "gf_rgl_head": None,
        "langs": cfg.langs,
        "bootstrap_only": cfg.bootstrap_only,
        "purge_only": cfg.purge_only,
    }
    if cfg.gf_rgl_dir.exists() and _is_git_repo(cfg.gf_rgl_dir):
        try:
            state["gf_rgl_head"] = get_gf_rgl_head(cfg.gf_rgl_dir)
        except Exception:
            state["gf_rgl_head"] = None

    if extra:
        state.update(extra)

    out_path = cfg.repo_root / cfg.state_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    logger.info("Wrote alignment state: %s", out_path)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def align(cfg: AlignmentConfig) -> None:
    """
    One-shot alignment:
      1) pin gf-rgl commit
      2) purge .gfo
      3) run Tier-1 bootstrap
      4) write state
    """
    if not cfg.repo_root.exists():
        raise AlignmentError(f"repo_root does not exist: {cfg.repo_root}")

    logger.info("=== ALIGNMENT START ===")
    logger.info("repo_root=%s", cfg.repo_root)
    logger.info("gf_rgl_dir=%s", cfg.gf_rgl_dir)
    logger.info("commit=%s", cfg.gf_rgl_commit)
    logger.info("dry_run=%s force=%s allow_dirty=%s", cfg.dry_run, cfg.force, cfg.allow_dirty)
    if cfg.langs:
        logger.info("langs=%s", cfg.langs)

    ensure_gf_rgl_commit(cfg)
    purge_gfo(cfg.repo_root, dry_run=cfg.dry_run)
    purge_build_logs(cfg.repo_root, dry_run=cfg.dry_run)
    run_bootstrap_tier1(cfg)
    write_state(cfg)

    logger.info("=== ALIGNMENT DONE ===")


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Align gf-rgl + bootstrap Tier-1 bridge/app grammars.")
    p.add_argument("--repo-root", default=None, help="Repo root (default: inferred from this file).")
    p.add_argument("--gf-rgl-dir", default=None, help="Path to gf-rgl (default: <repo-root>/gf-rgl).")
    p.add_argument("--commit", default=DEFAULT_GF_RGL_COMMIT, help="gf-rgl commit to pin (default: e0a2215).")
    p.add_argument("--python", dest="python_exe", default=sys.executable, help="Python executable to run tools.")
    p.add_argument("--langs", default=None, help="Comma-separated ISO codes to bootstrap (optional).")

    p.add_argument("--dry-run", action="store_true", help="Print actions, do not modify files.")
    p.add_argument("--force", action="store_true", help="Overwrite bridge/app files; override dirty guard.")
    p.add_argument("--allow-dirty", action="store_true", help="Allow gf-rgl dirty state (no checkout).")

    p.add_argument("--bootstrap-only", action="store_true", help="Skip git pin + purge; only run bootstrap.")
    p.add_argument("--purge-only", action="store_true", help="Skip git pin + bootstrap; only purge .gfo.")
    p.add_argument("--verbose", action="store_true", help="Verbose logs.")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[1]
    gf_rgl_dir = Path(args.gf_rgl_dir).resolve() if args.gf_rgl_dir else (repo_root / "gf-rgl")

    langs = None
    if args.langs:
        langs = [x.strip().lower() for x in args.langs.split(",") if x.strip()]

    cfg = AlignmentConfig(
        repo_root=repo_root,
        gf_rgl_dir=gf_rgl_dir,
        gf_rgl_commit=args.commit,
        python_exe=args.python_exe,
        dry_run=bool(args.dry_run),
        force=bool(args.force),
        allow_dirty=bool(args.allow_dirty),
        langs=langs,
        bootstrap_only=bool(args.bootstrap_only),
        purge_only=bool(args.purge_only),
    )

    try:
        align(cfg)
        return 0
    except AlignmentError as e:
        logger.error(str(e))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
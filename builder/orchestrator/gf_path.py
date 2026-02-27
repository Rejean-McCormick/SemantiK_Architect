# builder/orchestrator/gf_path.py
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from . import config


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for s in items:
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def discover_rgl_lang_dirs() -> List[Path]:
    """
    GF does not recurse into directories in -path.
    Include all first-level dirs under gf-rgl/src that contain any .gf file somewhere inside.
    """
    rgl_src = config.RGL_SRC
    if not rgl_src.exists():
        return []

    def has_gf_files(d: Path) -> bool:
        try:
            for _ in d.rglob("*.gf"):
                return True
        except Exception:
            return False
        return False

    dirs: List[Path] = []
    for p in sorted(rgl_src.iterdir(), key=lambda x: x.name):
        if not p.is_dir():
            continue
        if p.name == "api":
            continue
        if has_gf_files(p):
            dirs.append(p)
    return dirs


def discover_contrib_dirs() -> List[Path]:
    """Find all language subdirectories inside gf/contrib/ (ADR 006)."""
    contrib = config.CONTRIB_DIR
    if not contrib.exists():
        return []
    return [p for p in contrib.iterdir() if p.is_dir()]


def generated_src_candidates() -> List[Path]:
    """
    Order matters for -path and file shadowing.
    Prefer canonical repo_root/generated/src over repo_root/gf/generated/src.
    SAFE_MODE is always first (isolated).
    """
    cands = [
        config.SAFE_MODE_SRC,
        config.GENERATED_SRC_DEFAULT,
        config.GENERATED_SRC_ROOT,
        config.GENERATED_SRC_GF,
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


def gf_path_args() -> str:
    """
    Construct GF -path value.

    CRITICAL: include:
      - gf-rgl/src + gf-rgl/src/api
      - all first-level language dirs under gf-rgl/src (Prelude/SyntaxXXX/etc)
      - gf/contrib/{lang}/ (ADR 006)
      - gf/ (local modules like SemantikArchitect.gf and Wiki*.gf)
      - generated/src dirs (SAFE_MODE + both legacy locations)
      - repo root (last resort)
    """
    rgl_lang_dirs = discover_rgl_lang_dirs()

    parts: List[str] = [
        str(config.RGL_SRC.resolve()) if config.RGL_SRC.exists() else str(config.RGL_SRC),
        str(config.RGL_API.resolve()) if config.RGL_API.exists() else str(config.RGL_API),
        *[str(d.resolve()) for d in rgl_lang_dirs if d.exists()],
        *[str(d.resolve()) for d in discover_contrib_dirs() if d.exists()],
        str(config.GF_DIR.resolve()) if config.GF_DIR.exists() else str(config.GF_DIR),
        *[str(d) for d in generated_src_candidates() if d.exists()],
        str(config.ROOT_DIR.resolve()),
    ]

    return os.pathsep.join(_dedupe_keep_order(parts))


__all__ = [
    "discover_rgl_lang_dirs",
    "discover_contrib_dirs",
    "generated_src_candidates",
    "gf_path_args",
]

# builder/orchestrator/git_utils.py
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


__all__ = [
    "git_head",
    "git_resolve_ref",
    "git_list_tags",
    "detect_gf_version",
    "choose_best_rgl_ref_from_tags",
    # Keep underscored helpers importable for internal callers/tests.
    "_run",
    "_git_head",
    "_git_resolve_ref",
    "_git_list_tags",
    "_detect_gf_version",
    "_choose_best_rgl_ref_from_tags",
]


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


def _git_head(repo_dir: Path) -> Optional[str]:
    """
    Return the full SHA of HEAD for repo_dir, or None if repo_dir isn't a git repo.
    Note: submodules often have .git as a file, not a directory.
    """
    if not (repo_dir / ".git").exists():
        return None
    proc = _run(["git", "rev-parse", "HEAD"], cwd=repo_dir, timeout=10)
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip() or None


def _git_resolve_ref(repo_dir: Path, ref: str) -> Optional[str]:
    """Resolve a tag/branch/commit-ish to a full commit SHA, or None if unavailable."""
    ref = (ref or "").strip()
    if not ref:
        return None
    if not (repo_dir / ".git").exists():
        return None
    proc = _run(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"], cwd=repo_dir, timeout=10)
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip() or None


def _git_list_tags(repo_dir: Path, limit: int = 30) -> List[str]:
    """List tags (sorted case-insensitively). If limit>0, return only the last `limit` tags."""
    if not (repo_dir / ".git").exists():
        return []
    proc = _run(["git", "tag", "--list"], cwd=repo_dir, timeout=15)
    if proc.returncode != 0:
        return []
    tags = [t.strip() for t in (proc.stdout or "").splitlines() if t.strip()]
    tags_sorted = sorted(tags, key=lambda s: s.lower())
    if limit > 0:
        return tags_sorted[-limit:]
    return tags_sorted


def _detect_gf_version(gf_bin: str, cwd: Path) -> Optional[Tuple[int, int, int]]:
    """Try to parse `gf --version` output as (major, minor, patch)."""
    try:
        proc = _run([gf_bin, "--version"], cwd=cwd, timeout=10)
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
    """Extract (major, minor) from tags like release-3.12, GF-3.10, etc."""
    m = re.search(r"(?i)(?:release|gf)[-_]?(\d+)\.(\d+)", tag or "")
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)))


def _choose_best_rgl_ref_from_tags(
    gf_ver: Optional[Tuple[int, int, int]],
    tags: List[str],
) -> Optional[str]:
    """
    Suggest a good RGL ref when no pin exists (non-enforcing):
      - Prefer exact match of installed GF (major, minor)
      - Else best <= installed
      - Else highest tag-version parseable
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

        # Exact match
        for (tv, t) in reversed(parsed):
            if tv == want:
                return t

        # Best <= installed
        leq = [t for (tv, t) in parsed if tv <= want]
        if leq:
            return leq[-1]

    # Fallback: highest parseable tag-version
    return parsed[-1][1]


# ---------------------------------------------------------------------
# Public API expected by builder/orchestrator/build.py (non-underscored)
# ---------------------------------------------------------------------


def git_head(repo_dir: Path) -> Optional[str]:
    return _git_head(repo_dir)


def git_resolve_ref(repo_dir: Path, ref: str) -> Optional[str]:
    return _git_resolve_ref(repo_dir, ref)


def git_list_tags(repo_dir: Path, limit: int = 30) -> List[str]:
    return _git_list_tags(repo_dir, limit=limit)


def detect_gf_version(gf_bin: str, cwd: Path) -> Optional[Tuple[int, int, int]]:
    return _detect_gf_version(gf_bin, cwd=cwd)


def choose_best_rgl_ref_from_tags(
    gf_ver: Optional[Tuple[int, int, int]],
    tags: List[str],
) -> Optional[str]:
    return _choose_best_rgl_ref_from_tags(gf_ver=gf_ver, tags=tags)
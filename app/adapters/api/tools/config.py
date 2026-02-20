from __future__ import annotations

import os
import re
import shlex
import sys
import datetime
from pathlib import Path
from typing import Sequence, Tuple

from fastapi import HTTPException

from app.shared.config import settings


PYTHON_EXE = sys.executable

REPO_ROOT = Path(settings.FILESYSTEM_REPO_PATH).resolve()
if not REPO_ROOT.exists():
    raise RuntimeError(f"FILESYSTEM_REPO_PATH does not exist: {REPO_ROOT}")

TOOL_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")

MAX_OUTPUT_CHARS = int(os.getenv("ARCHITECT_TOOLS_MAX_OUTPUT_CHARS", "200000"))
DEFAULT_TIMEOUT_SEC = int(os.getenv("ARCHITECT_TOOLS_DEFAULT_TIMEOUT_SEC", "600"))
AI_TOOLS_ENABLED = os.getenv("ARCHITECT_ENABLE_AI_TOOLS", "").strip().lower() in {"1", "true", "yes", "y"}


def iso_now() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def safe_join_cmd(parts: Sequence[str]) -> str:
    try:
        return shlex.join(list(parts))
    except Exception:
        return " ".join(shlex.quote(p) for p in parts)


def resolve_repo_path(rel_path: str) -> Path:
    p = (REPO_ROOT / rel_path).resolve()
    if p != REPO_ROOT and REPO_ROOT not in p.parents:
        raise HTTPException(status_code=400, detail="Invalid tool path (outside repo root).")
    return p


def ensure_exists(p: Path, rel_path: str) -> None:
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Tool target missing on disk: {rel_path}")


def truncate(text: str) -> Tuple[str, bool]:
    if text is None:
        return "", False
    if len(text) <= MAX_OUTPUT_CHARS:
        return text, False
    return text[:MAX_OUTPUT_CHARS] + "\n... [TRUNCATED]", True

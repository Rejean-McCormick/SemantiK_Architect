# \tools\language_health.py
"""
CLI entrypoint wrapper for language_health.

Why this file exists:
- The backend tool registry invokes:  python -u tools/language_health.py ...
- When executing a script by path, Python puts <repo>/tools on sys.path (not <repo>),
  so `import tools.language_health` will fail unless we add the repo root.
- The real implementation lives in the package: tools/language_health/
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Sequence


def _ensure_repo_root_on_syspath() -> Path:
    """
    Ensure <repo> (parent of tools/) is on sys.path so imports like
    `import tools.language_health` work when executing this file as a script.
    """
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    return repo_root


def main(argv: Optional[Sequence[str]] = None) -> int:
    _ensure_repo_root_on_syspath()

    # Canonical entrypoint is tools.language_health.main (package __init__.py).
    # That should delegate to tools.language_health.cli (thin orchestrator).
    from tools.language_health import main as pkg_main  # type: ignore

    return int(pkg_main(list(argv) if argv is not None else None))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
# tools/language_health/__init__.py
from __future__ import annotations

"""
tools.language_health

Package entrypoint for the hybrid language audit tool (compile + API runtime).

Design goals:
- Keep imports lightweight at package import time.
- Provide a stable `main()` entrypoint for CLI wrappers / scripts.
"""

from typing import Optional, Sequence

__version__ = "2.6"

__all__ = ["main", "__version__"]


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    CLI entrypoint.

    Kept as a thin wrapper so importing `tools.language_health` doesn't eagerly
    import heavier modules (requests, repo scans, etc.).
    """
    from .cli import main as _main  # local import to keep package import fast

    # cli.main expects Optional[List[str]]; allow any Sequence[str] here.
    return _main(list(argv) if argv is not None else None)
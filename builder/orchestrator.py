# builder/orchestrator.py
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Ensure repo root is on sys.path so this can be executed from different working dirs.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Re-export the programmatic API from the package implementation.
try:
    from builder.orchestrator.build import build_pgf  # noqa: F401
except Exception as e:  # pragma: no cover
    build_pgf = None  # type: ignore[assignment]
    _IMPORT_ERROR: Optional[BaseException] = e
else:
    _IMPORT_ERROR = None

__all__ = ["build_pgf", "main"]


def main() -> None:
    """
    Backwards-compatible CLI entrypoint.

    Preferred invocation after refactor:
        python -m builder.orchestrator [args...]
    """
    if _IMPORT_ERROR is not None:  # pragma: no cover
        raise RuntimeError(
            "Orchestrator package import failed. Ensure the refactor created:\n"
            "  builder/orchestrator/__init__.py\n"
            "  builder/orchestrator/__main__.py\n"
            "  builder/orchestrator/build.py\n"
            "  ...\n"
        ) from _IMPORT_ERROR

    # Delegate CLI parsing/execution to the package.
    from builder.orchestrator.__main__ import main as pkg_main

    pkg_main()


if __name__ == "__main__":
    main()
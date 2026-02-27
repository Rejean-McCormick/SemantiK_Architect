# builder/orchestrator/__main__.py
from __future__ import annotations

import argparse
import logging
import sys

from .build import build_pgf


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Two-phase GF build orchestrator to produce semantik_architect.pgf."
    )
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
    p.add_argument("--no-preflight", action="store_true", help="Skip RGL pin/bridge preflight checks.")
    p.add_argument(
        "--regen-safe",
        action="store_true",
        help="Regenerate SAFE_MODE grammars even if present.",
    )
    return p.parse_args()


def main() -> None:
    # CLI owns logging configuration; library modules should just use getLogger().
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
        force=True,
    )

    args = _parse_args()

    # build_pgf handles verbose logger-level adjustments internally.
    build_pgf(
        strategy=args.strategy,
        langs=args.langs,
        clean=args.clean,
        verbose=args.verbose,
        max_workers=args.max_workers,
        no_preflight=args.no_preflight,
        regen_safe=args.regen_safe,
    )


if __name__ == "__main__":
    main()
"""
builder.orchestrator package.

Public API surface:
  - build_pgf: programmatic entrypoint to produce AbstractWiki.pgf
"""

from .build import build_pgf

__all__ = ["build_pgf"]
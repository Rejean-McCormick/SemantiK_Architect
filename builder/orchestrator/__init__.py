"""
builder.orchestrator package.

Public API surface:
  - build_pgf: programmatic entrypoint to produce semantik_architect.pgf
"""

from .build import build_pgf

__all__ = ["build_pgf"]
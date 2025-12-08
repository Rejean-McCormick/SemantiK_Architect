# architect_http_api/gf/__init__.py
# =========================================================================
# GRAMMATICAL FRAMEWORK (GF) INTEGRATION PACKAGE
#
# This module exposes the runtime engine required to interact with the
# compiled PGF grammar. It serves as the single entry point for
# linearization and morphology tasks.
# =========================================================================

from .engine import GFEngine, GFEngineError
# Optionally expose language mapping tools if external modules need them
from .language_map import get_rgl_code, get_z_language

__all__ = [
    "GFEngine",
    "GFEngineError",
    "get_rgl_code",
    "get_z_language",
]
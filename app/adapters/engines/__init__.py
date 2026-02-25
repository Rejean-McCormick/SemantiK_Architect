# app/adapters/engines/__init__.py
"""
Grammar Engine Adapters.

This package contains the concrete implementations of the `IGrammarEngine` port.
It provides the mechanisms to transform abstract Semantic Frames into text using
different strategies:

1. GFGrammarEngine: The production-grade engine using the compiled PGF binary (High Fidelity).
2. PythonGrammarEngine: The fallback/prototyping engine using pure Python string manipulation (Low Fidelity).
"""

from .gf_wrapper import GFGrammarEngine
from .python_engine_wrapper import PythonGrammarEngine

__all__ = [
    "GFGrammarEngine",
    "PythonGrammarEngine",
]
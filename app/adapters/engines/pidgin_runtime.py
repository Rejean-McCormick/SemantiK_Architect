# app/adapters/engines/pidgin_runtime.py
from typing import Any, Dict

class PidginGrammarEngine:
    """
    A low-fidelity grammar engine used as a fallback.
    It simulates grammar operations using simple string manipulation
    instead of the full GF binary.
    """
    
    def __init__(self):
        pass

    def check_grammar(self, language_code: str) -> bool:
        """Always returns True in mock mode."""
        return True

    def generate(self, abstract_tree: str, language_code: str) -> str:
        """
        Mock generation: just returns the abstract tree prefixed.
        """
        return f"[Pidgin-{language_code}] {abstract_tree}"
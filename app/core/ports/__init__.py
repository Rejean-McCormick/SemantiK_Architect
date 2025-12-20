# app/core/ports/__init__.py
"""
Core Ports (Interfaces).

This package defines the abstract base classes (Protocols) that the
Infrastructure Adapters must implement. These interfaces allow the Core
Domain to interact with the outside world (Database, Redis, GF) without
knowing the implementation details.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

# --- existing imports if you have them separate ---
# from .grammar_engine import IGrammarEngine
# from .lexicon_repository import ILexiconRepository
# from .message_broker import IMessageBroker

class LanguageRepo(ABC):
    """
    The Port (Interface) for storing Language Grammars.
    Hexagonal Architecture: The Core defines this, the Adapter implements it.
    """
    
    @abstractmethod
    async def save_grammar(self, language_code: str, content: str) -> None:
        """Persist a grammar file."""
        pass

    @abstractmethod
    async def get_grammar(self, language_code: str) -> Optional[str]:
        """Retrieve a grammar file by language code."""
        pass

    @abstractmethod
    async def list_languages(self) -> List[str]:
        """List all available languages."""
        pass

class LLMPort(ABC):
    """
    The Port (Interface) for Large Language Models.
    Hexagonal Architecture: Core Use Cases rely on this to generate text.
    """
    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        """
        Send a prompt to the LLM and get the response text.
        """
        pass

# --- If you want to keep the old ones too, add them below or import them ---

# __all__ helps verify what is exported when doing `from app.core.ports import *`
__all__ = [
    "LanguageRepo",
    "LLMPort",
    # "IGrammarEngine",      <-- Add these back if you have the files
    # "ILexiconRepository",
    # "IMessageBroker",
]
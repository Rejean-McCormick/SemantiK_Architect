# app/core/ports/__init__.py
"""
Core Ports (Interfaces).

This package defines the abstract base classes (Protocols) that the
Infrastructure Adapters must implement. These interfaces allow the Core
Domain to interact with the outside world (Database, Redis, GF) without
knowing the implementation details.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Callable, Coroutine

# Import domain models for type hints
from app.core.domain.models import LexiconEntry, Frame, Sentence
from app.core.domain.events import SystemEvent

# =========================================================
# 1. PERSISTENCE PORTS (Databases & Files)
# =========================================================

class LanguageRepo(ABC):
    """
    Port for storing Language Grammars and Metadata (Zone A).
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
    async def list_languages(self) -> List[Any]:
        """
        List all available languages.
        Returns: List of Dicts/Objects (metadata).
        """
        pass

class LexiconRepo(ABC):
    """
    Port for accessing Vocabulary Data (Zone B).
    """
    @abstractmethod
    async def get_entry(self, iso_code: str, word: str) -> Optional[LexiconEntry]:
        """Retrieves a single lexicon entry by word/lemma."""
        pass

    @abstractmethod
    async def save_entry(self, iso_code: str, entry: LexiconEntry) -> None:
        """Saves or updates a lexicon entry."""
        pass

    @abstractmethod
    async def get_entries_by_concept(self, lang_code: str, qid: str) -> List[LexiconEntry]:
        """Finds all entries linked to a specific Wikidata QID."""
        pass

# =========================================================
# 2. GENERATION PORTS (Engines & AI)
# =========================================================

class IGrammarEngine(ABC):
    """
    Port for the Rule-Based Grammar Engine (GF or Python).
    """
    @abstractmethod
    async def generate(self, lang_code: str, frame: Frame) -> Sentence:
        """Converts a Semantic Frame into a Sentence."""
        pass

class LLMPort(ABC):
    """
    Port for Large Language Models (AI Services).
    """
    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        """Send a prompt to the LLM and get the response text."""
        pass

# =========================================================
# 3. INFRASTRUCTURE PORTS (Messaging)
# =========================================================

class IMessageBroker(ABC):
    """
    Port for the Event Bus (Redis/RabbitMQ).
    """
    @abstractmethod
    async def publish(self, event: SystemEvent) -> None:
        """Publishes a domain event."""
        pass

    @abstractmethod
    async def subscribe(self, event_type: str, handler: Callable[[SystemEvent], Coroutine[Any, Any, None]]) -> None:
        """Subscribes to a specific event type."""
        pass

# =========================================================
# EXPORTS
# =========================================================
__all__ = [
    "LanguageRepo",
    "LexiconRepo",
    "IGrammarEngine",
    "LLMPort",
    "IMessageBroker",
]
# app/core/ports/__init__.py
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Protocol, TYPE_CHECKING, runtime_checkable

if TYPE_CHECKING:
    from app.core.domain.events import SystemEvent
    from app.core.domain.models import Frame, Sentence


# Keep this module import-light.
# Do not import domain models or adapter code at runtime from here.
# This package should define ports only, so worker/API startup does not
# pull in app.core.domain.models during package initialization.

JSONMapping = Mapping[str, Any]
EventHandler = Callable[[Any], Awaitable[None]]


# ==============================================================================
# AI & GENERATION PORTS
# ==============================================================================

@runtime_checkable
class IGrammarEngine(Protocol):
    """
    Port for the abstract grammar engine (GF/PGF or compatible renderer).
    """

    grammar: Any  # Underlying engine/PGF object, if exposed by implementation.

    async def generate(
        self,
        lang_code: str,
        frame: "Frame | JSONMapping",
    ) -> "Sentence":
        """
        Generate a surface realization from a semantic frame.
        """
        ...

    async def get_supported_languages(self) -> list[str]:
        """
        Return supported ISO language codes.
        """
        ...

    async def reload(self) -> None:
        """
        Reload grammar assets from disk or backing storage.
        """
        ...

    async def health_check(self) -> bool:
        """
        Return True when the engine is operational.
        """
        ...


@runtime_checkable
class LLMPort(Protocol):
    """
    Port for text-generation backends.
    """

    def generate_text(self, prompt: str, **kwargs: Any) -> str:
        """
        Generate text for the given prompt.
        """
        ...


# ==============================================================================
# INFRASTRUCTURE PORTS
# ==============================================================================

@runtime_checkable
class IMessageBroker(Protocol):
    """
    Port for pub/sub messaging infrastructure.
    """

    async def publish(self, event: "SystemEvent | Any") -> None:
        """
        Publish an event to the broker.
        """
        ...

    async def subscribe(self, channel: str, handler: EventHandler) -> None:
        """
        Subscribe an async handler to a channel/topic.
        """
        ...

    async def connect(self) -> None:
        """
        Open broker connection(s).
        """
        ...

    async def disconnect(self) -> None:
        """
        Close broker connection(s).
        """
        ...

    async def health_check(self) -> bool:
        """
        Return True when the broker is reachable and healthy.
        """
        ...


@runtime_checkable
class TaskQueue(Protocol):
    """
    Port for async job queues such as Redis/ARQ.
    """

    async def connect(self) -> None:
        """
        Open queue connection(s).
        """
        ...

    async def disconnect(self) -> None:
        """
        Close queue connection(s).
        """
        ...

    async def enqueue(self, function_name: str, **kwargs: Any) -> str | None:
        """
        Enqueue a background job.

        Args:
            function_name: Worker function name to execute.
            **kwargs: Keyword arguments passed to the worker.

        Returns:
            The job ID if available, otherwise None.
        """
        ...


# ==============================================================================
# REPOSITORY PORTS
# ==============================================================================

@runtime_checkable
class LexiconRepo(Protocol):
    """
    Port for lexical knowledge storage.
    """

    async def get_entry(self, lang: str, key: str) -> dict[str, Any] | None:
        """
        Fetch a lexicon entry by language and key.
        """
        ...

    async def save_entry(self, lang: str, entry: JSONMapping) -> None:
        """
        Persist a lexicon entry.
        """
        ...

    async def health_check(self) -> bool:
        """
        Return True when the repository is reachable and healthy.
        """
        ...


@runtime_checkable
class LanguageRepo(Protocol):
    """
    Port for language metadata and grammar registry storage.
    """

    async def save_grammar(self, code: str, metadata_json: str) -> None:
        """
        Persist language/grammar metadata for a language code.
        """
        ...

    async def list_languages(self) -> list[dict[str, Any]]:
        """
        Return onboarded language records.
        """
        ...

    async def health_check(self) -> bool:
        """
        Return True when the repository is reachable and healthy.
        """
        ...


# ==============================================================================
# EXPORTS
# ==============================================================================

__all__ = [
    "EventHandler",
    "IGrammarEngine",
    "IMessageBroker",
    "LLMPort",
    "LanguageRepo",
    "LexiconRepo",
    "TaskQueue",
]
# app/core/ports/grammar_engine.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, TYPE_CHECKING, TypeAlias, runtime_checkable

if TYPE_CHECKING:
    from app.core.domain.models import Frame, Sentence
    from app.core.domain.planning.construction_plan import ConstructionPlan
else:
    # Keep this module runtime-light to avoid import cycles during startup.
    Frame = Any
    Sentence = Any
    ConstructionPlan = Any


FrameMapping: TypeAlias = Mapping[str, Any]
FrameInput: TypeAlias = Frame | FrameMapping


@runtime_checkable
class IGrammarEngine(Protocol):
    """
    Port for surface-realization backends.

    Preferred boundary:
        ConstructionPlan -> Sentence

    Temporary compatibility boundary:
        Frame | Mapping[str, Any] -> Sentence

    Guidance:
    - New orchestration should call `realize(construction_plan=...)`.
    - `generate(lang_code, frame)` is a migration shim for legacy callers.
    - If an implementation falls back to a compatibility path, that fallback
      should be explicit in the returned Sentence.debug_info.
    """

    async def realize(self, construction_plan: ConstructionPlan) -> Sentence:
        """
        Realize a planner-produced construction plan into surface text.

        Implementations should treat `construction_plan` as immutable input.

        Returns:
            A Sentence carrying surface text and structured debug metadata.

        Expected debug fields when available:
            - construction_id
            - renderer_backend / engine_backend
            - lang_code / resolved_language
            - fallback_used
            - backend_trace / ast / trace (backend-specific, optional)
        """
        ...

    async def generate(self, lang_code: str, frame: FrameInput) -> Sentence:
        """
        Legacy compatibility entrypoint.

        Implementations should prefer to normalize this into the planner-first
        path internally:

            frame -> planner/bridge -> ConstructionPlan -> realize()

        Args:
            lang_code:
                Normalized target language code.
            frame:
                Semantic Frame object or dict-like compatibility payload.

        Returns:
            A Sentence carrying surface text and structured debug metadata.

        Migration rule:
            New code should not use this as the primary runtime boundary.
            If direct frame generation or another fallback path is used, that
            fact should be machine-readable in `debug_info`.
        """
        ...

    def supports(self, construction_id: str, lang_code: str) -> bool:
        """
        Cheap capability probe for dispatch/orchestration.

        Returns:
            True if the backend can attempt realization for the given
            `(construction_id, lang_code)` pair, otherwise False.

        Notes:
            - Must be inexpensive.
            - Must not trigger full generation.
        """
        ...

    async def get_supported_languages(self) -> list[str]:
        """
        Return the language codes currently available to this backend.
        """
        ...

    async def reload(self) -> None:
        """
        Reload engine resources, for example after new grammar assets land.
        """
        ...

    async def health_check(self) -> bool:
        """
        Return True when the backend is responsive and usable.
        """
        ...


GrammarEnginePort = IGrammarEngine

__all__ = [
    "FrameMapping",
    "FrameInput",
    "IGrammarEngine",
    "GrammarEnginePort",
]
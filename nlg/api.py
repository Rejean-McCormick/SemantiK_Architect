# nlg/api.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from . import router
from .semantics import Frame, BioFrame, EventFrame


# ---------------------------------------------------------------------------
# Public data models
# ---------------------------------------------------------------------------


@dataclass
class GenerationOptions:
    """
    High-level generation controls.

    This is intentionally small and stable. Low-level knobs (morphology, etc.)
    should remain internal to engines / language profiles.
    """

    register: Optional[str] = None        # "neutral", "formal", "informal", etc.
    max_sentences: Optional[int] = None   # Upper bound on number of sentences
    discourse_mode: Optional[str] = None  # e.g. "intro", "summary"
    seed: Optional[int] = None            # Reserved for future stochastic behavior

    def to_engine_kwargs(self) -> Dict[str, Any]:
        """
        Convert to a dict suitable for passing into engines. Engines may ignore
        fields they do not understand.
        """
        data: Dict[str, Any] = {}
        if self.register is not None:
            data["register"] = self.register
        if self.max_sentences is not None:
            data["max_sentences"] = self.max_sentences
        if self.discourse_mode is not None:
            data["discourse_mode"] = self.discourse_mode
        if self.seed is not None:
            data["seed"] = self.seed
        return data


@dataclass
class GenerationResult:
    """
    Standardized output from the frontend API.
    """

    text: str
    sentences: List[str]
    lang: str
    frame: Frame
    debug_info: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Engine protocol (adapter boundary)
# ---------------------------------------------------------------------------


class Engine(Protocol):
    """
    Minimal protocol expected from family/language engines.

    You should implement this in your existing engines, either by:
      - Adding a `generate` method with this signature, or
      - Providing an adapter that wraps current engine APIs.

    The return value MUST be a dict with at least:
      - "text": str
      - optionally "sentences": list[str]
      - optionally "debug_info": dict
    """

    def generate(
        self,
        frame: Frame,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        ...


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class NLGSession:
    """
    Stateful session that caches engines and other resources.

    Use this in long-running services or batch jobs.
    """

    def __init__(self, *, preload_langs: Optional[List[str]] = None) -> None:
        self._engine_cache: Dict[str, Engine] = {}
        if preload_langs:
            for lang in preload_langs:
                self._get_engine(lang)

    # public API -------------------------------------------------------------

    def generate(
        self,
        lang: str,
        frame: Frame,
        *,
        options: Optional[GenerationOptions] = None,
        debug: bool = False,
    ) -> GenerationResult:
        """
        Main entry point: frame → text.
        """
        engine = self._get_engine(lang)
        engine_kwargs = options.to_engine_kwargs() if options else {}
        engine_kwargs["debug"] = debug

        raw = engine.generate(frame, **engine_kwargs)

        text = str(raw.get("text", ""))
        sentences = raw.get("sentences")

        if sentences is None:
            # Simple fallback: naive split on period. Engines are encouraged
            # to provide proper sentence segmentation.
            sentences = [s for s in text.split(".") if s.strip()]
            sentences = [s.strip() + "." for s in sentences] if text.strip() else []

        debug_info = raw.get("debug_info") if debug else None

        return GenerationResult(
            text=text,
            sentences=sentences,
            lang=lang,
            frame=frame,
            debug_info=debug_info,
        )

    # internal helpers -------------------------------------------------------

    def _get_engine(self, lang: str) -> Engine:
        """
        Retrieve or initialize the engine for a given language.

        This assumes that `router.get_engine(lang)` exists and returns an
        object implementing the `Engine` protocol above. If your router uses
        a different API, adapt this method accordingly.
        """
        if lang in self._engine_cache:
            return self._engine_cache[lang]

        engine = router.get_engine(lang)  # type: ignore[attr-defined]
        self._engine_cache[lang] = engine
        return engine


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

# Default process-global session for simple/stateless usage.
_default_session = NLGSession()


def generate(
    lang: str,
    frame: Frame,
    *,
    options: Optional[GenerationOptions] = None,
    debug: bool = False,
) -> GenerationResult:
    """
    Stateless convenience wrapper around `NLGSession.generate`.

    Suitable for scripts, tests, and simple integrations.
    """
    return _default_session.generate(
        lang=lang,
        frame=frame,
        options=options,
        debug=debug,
    )


def generate_bio(
    lang: str,
    bio: BioFrame,
    *,
    options: Optional[GenerationOptions] = None,
    debug: bool = False,
) -> GenerationResult:
    """
    Convenience wrapper for biography frames.
    """
    return generate(
        lang=lang,
        frame=bio,
        options=options,
        debug=debug,
    )


def generate_event(
    lang: str,
    event: EventFrame,
    *,
    options: Optional[GenerationOptions] = None,
    debug: bool = False,
) -> GenerationResult:
    """
    Convenience wrapper for event frames.
    """
    return generate(
        lang=lang,
        frame=event,
        options=options,
        debug=debug,
    )

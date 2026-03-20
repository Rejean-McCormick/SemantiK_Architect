# nlg/api.py

from __future__ import annotations

import asyncio
import inspect
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Sequence, cast

from app.core.domain.models import Frame as WireFrame
from app.core.domain.models import Sentence
from app.core.ports.grammar_engine import IGrammarEngine
from app.shared.container import container


# Optional semantic-frame types (kept for compatibility with older call sites).
try:
    from app.core.domain.semantics.types import BioFrame as BioFrame  # type: ignore
except Exception:  # pragma: no cover
    BioFrame = Any  # type: ignore[misc,assignment]

try:
    # Not all branches define EventFrame; keep it optional.
    from app.core.domain.semantics.types import EventFrame as EventFrame  # type: ignore
except Exception:  # pragma: no cover
    EventFrame = Any  # type: ignore[misc,assignment]


# Public "Frame" type for this module: the current engine contract uses WireFrame.
Frame = WireFrame


# ---------------------------------------------------------------------------
# Public data models
# ---------------------------------------------------------------------------


@dataclass
class GenerationOptions:
    """
    High-level generation controls.

    Note: current engine contract is intentionally small; options are carried
    forward for compatibility but may be ignored by the underlying engine.
    """

    register: Optional[str] = None
    max_sentences: Optional[int] = None
    discourse_mode: Optional[str] = None
    seed: Optional[int] = None

    def to_engine_kwargs(self) -> Dict[str, Any]:
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
    Frontend/client-facing convenience result.

    This is not the canonical public HTTP envelope. It is a consumer-friendly
    model that keeps the traditional `lang`, `sentences`, and `frame` fields,
    while optionally mirroring selected canonical generation fields so callers
    do not lose important runtime/public metadata.
    """

    text: str
    sentences: List[str]
    lang: str
    frame: Any  # accept WireFrame or semantic frames passed by callers
    debug_info: Optional[Dict[str, Any]] = None

    # Optional mirrors of canonical generation fields.
    construction_id: Optional[str] = None
    renderer_backend: Optional[str] = None
    fallback_used: bool = False
    tokens: List[str] = field(default_factory=list)
    generation_time_ms: float = 0.0


# ---------------------------------------------------------------------------
# Engine protocol (adapter boundary)
# ---------------------------------------------------------------------------


class Engine(Protocol):
    """
    Minimal protocol expected from engines/adapters.

    The return value SHOULD be a dict with at least:
      - "text": str

    It MAY also include:
      - "sentences": list[str]
      - "lang_code": str
      - "construction_id": str
      - "renderer_backend": str
      - "fallback_used": bool
      - "tokens": list[str]
      - "generation_time_ms": number
      - "debug_info": dict
    """

    def generate(self, frame: Any, **kwargs: Any) -> Dict[str, Any]:
        ...


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clean_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_lang(value: str) -> str:
    normalized = _clean_optional_str(value)
    if not normalized:
        raise ValueError("Language is required.")
    return normalized.lower()


def _normalize_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, Sequence):
        return []
    out: List[str] = []
    for item in value:
        text = _clean_optional_str(item)
        if text:
            out.append(text)
    return out


def _get_grammar_engine() -> IGrammarEngine:
    # DI container provides the configured grammar engine implementation.
    return cast(IGrammarEngine, container.grammar_engine())


def _run_async(coro: Any) -> Any:
    """
    Run an awaitable from sync code.

    If called while an event loop is already running, raise with guidance to
    use the async API.
    """
    if not inspect.isawaitable(coro):
        return coro

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    raise RuntimeError(
        "nlg.api.generate() was called from within a running event loop. "
        "Use NLGSession.generate_async(...) instead."
    )


def _coerce_to_wire_frame(frame: Any) -> WireFrame:
    """
    Accept several frame shapes and coerce into the WireFrame expected by IGrammarEngine.

    Supported inputs:
      - WireFrame (app.core.domain.models.Frame)
      - dict compatible with WireFrame
      - pydantic model with model_dump() producing WireFrame-compatible dict
      - legacy semantic BioFrame-like objects (best-effort)
    """
    if isinstance(frame, WireFrame):
        return frame

    if isinstance(frame, dict):
        return WireFrame.model_validate(frame)

    if hasattr(frame, "model_dump"):
        data = frame.model_dump()  # type: ignore[attr-defined]
        if isinstance(data, dict):
            return WireFrame.model_validate(data)

    # Best-effort adapter for legacy semantic BioFrame objects:
    # expects fields: main_entity.{name,gender}, primary_profession_lemmas, nationality_lemmas
    if hasattr(frame, "main_entity") and (
        hasattr(frame, "primary_profession_lemmas") or hasattr(frame, "nationality_lemmas")
    ):
        me = getattr(frame, "main_entity", None)
        name = getattr(me, "name", "") if me is not None else ""
        gender = getattr(me, "gender", "") if me is not None else ""

        profession = ""
        nationality = ""

        try:
            profs = getattr(frame, "primary_profession_lemmas", None) or []
            if profs:
                profession = str(profs[0] or "").strip()
        except Exception:
            profession = ""

        try:
            nats = getattr(frame, "nationality_lemmas", None) or []
            if nats:
                nationality = str(nats[0] or "").strip()
        except Exception:
            nationality = ""

        props: Dict[str, Any] = {}
        if profession:
            props["profession"] = profession
        if nationality:
            props["nationality"] = nationality

        return WireFrame(
            frame_type="bio",
            subject={"name": name, "gender": gender},
            properties=props,
        )

    raise TypeError(
        f"Unsupported frame type for generation: {type(frame).__name__}. "
        "Provide app.core.domain.models.Frame (WireFrame) or a compatible dict."
    )


def _split_sentences_fallback(text: str) -> List[str]:
    if not text.strip():
        return []
    chunks = re.split(r"([.!?])", text)
    sentences: List[str] = []
    buf = ""
    for piece in chunks:
        if not piece:
            continue
        buf += piece
        if piece in ".!?":
            sentence = buf.strip()
            if sentence:
                sentences.append(sentence)
            buf = ""
    leftover = buf.strip()
    if leftover:
        sentences.append(leftover)
    return sentences


def _normalize_debug_info(
    debug: bool,
    raw_debug_info: Any,
    options: Optional[GenerationOptions],
) -> Optional[Dict[str, Any]]:
    if not debug:
        return None

    debug_info = dict(raw_debug_info or {})
    if options is not None:
        debug_info.setdefault("options", options.to_engine_kwargs())
    return debug_info


def _build_generation_result(
    *,
    requested_lang: str,
    frame: Any,
    raw: Dict[str, Any],
    options: Optional[GenerationOptions],
    debug: bool,
) -> GenerationResult:
    text = str(raw.get("text", "") or "")
    lang = _normalize_lang(str(raw.get("lang_code") or requested_lang))
    tokens = _normalize_string_list(raw.get("tokens"))
    if not tokens and text:
        tokens = text.split()

    raw_sentences = raw.get("sentences")
    if raw_sentences is None:
        sentences = _split_sentences_fallback(text)
    else:
        sentences = [str(s) for s in cast(Sequence[Any], raw_sentences)]

    debug_info = _normalize_debug_info(
        debug=debug,
        raw_debug_info=raw.get("debug_info"),
        options=options,
    )

    construction_id = _clean_optional_str(raw.get("construction_id"))
    renderer_backend = _clean_optional_str(raw.get("renderer_backend"))
    fallback_used = bool(raw.get("fallback_used", False))

    generation_time_ms_raw = raw.get("generation_time_ms", 0.0)
    try:
        generation_time_ms = max(0.0, float(generation_time_ms_raw))
    except (TypeError, ValueError):
        generation_time_ms = 0.0

    return GenerationResult(
        text=text,
        sentences=sentences,
        lang=lang,
        frame=frame,
        debug_info=debug_info,
        construction_id=construction_id,
        renderer_backend=renderer_backend,
        fallback_used=fallback_used,
        tokens=tokens,
        generation_time_ms=generation_time_ms,
    )


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------


class _AppEngineAdapter:
    """
    Adapter around the app's configured IGrammarEngine (container-backed).
    """

    def __init__(self, lang: str) -> None:
        self.lang = _normalize_lang(lang)
        self._engine = _get_grammar_engine()

    async def generate_async(self, frame: Any, **kwargs: Any) -> Dict[str, Any]:
        debug = bool(kwargs.get("debug", False))
        wire_frame = _coerce_to_wire_frame(frame)
        sentence: Sentence = await self._engine.generate(lang_code=self.lang, frame=wire_frame)

        text = sentence.text
        tokens = list(sentence.tokens) if sentence.tokens else text.split()

        out: Dict[str, Any] = {
            "text": text,
            "sentences": _split_sentences_fallback(text) or [text],
            "lang_code": sentence.lang_code,
            "construction_id": sentence.construction_id,
            "renderer_backend": sentence.renderer_backend,
            "fallback_used": sentence.fallback_used,
            "tokens": tokens,
            "generation_time_ms": sentence.generation_time_ms,
        }

        if debug:
            out["debug_info"] = sentence.debug_info

        return out

    def generate(self, frame: Any, **kwargs: Any) -> Dict[str, Any]:
        return _run_async(self.generate_async(frame, **kwargs))


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

    def generate(
        self,
        lang: str,
        frame: Any,
        *,
        options: Optional[GenerationOptions] = None,
        debug: bool = False,
    ) -> GenerationResult:
        normalized_lang = _normalize_lang(lang)
        engine = self._get_engine(normalized_lang)

        engine_kwargs = options.to_engine_kwargs() if options else {}
        engine_kwargs["debug"] = debug

        raw = engine.generate(frame, **engine_kwargs)

        return _build_generation_result(
            requested_lang=normalized_lang,
            frame=frame,
            raw=raw,
            options=options,
            debug=debug,
        )

    async def generate_async(
        self,
        lang: str,
        frame: Any,
        *,
        options: Optional[GenerationOptions] = None,
        debug: bool = False,
    ) -> GenerationResult:
        """
        Async variant for callers already running an event loop.
        """
        normalized_lang = _normalize_lang(lang)
        engine = self._get_engine(normalized_lang)
        if not isinstance(engine, _AppEngineAdapter):
            # Fallback: run sync engine in thread-compatible way is out of scope here.
            # Keep behavior explicit.
            return self.generate(
                lang=normalized_lang,
                frame=frame,
                options=options,
                debug=debug,
            )

        engine_kwargs = options.to_engine_kwargs() if options else {}
        engine_kwargs["debug"] = debug

        raw = await engine.generate_async(frame, **engine_kwargs)

        return _build_generation_result(
            requested_lang=normalized_lang,
            frame=frame,
            raw=raw,
            options=options,
            debug=debug,
        )

    def _get_engine(self, lang: str) -> Engine:
        normalized_lang = _normalize_lang(lang)
        if normalized_lang in self._engine_cache:
            return self._engine_cache[normalized_lang]

        engine: Engine = _AppEngineAdapter(normalized_lang)
        self._engine_cache[normalized_lang] = engine
        return engine


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

_default_session = NLGSession()


def generate(
    lang: str,
    frame: Any,
    *,
    options: Optional[GenerationOptions] = None,
    debug: bool = False,
) -> GenerationResult:
    return _default_session.generate(lang=lang, frame=frame, options=options, debug=debug)


def generate_bio(
    lang: str,
    bio: Any,
    *,
    options: Optional[GenerationOptions] = None,
    debug: bool = False,
) -> GenerationResult:
    return generate(lang=lang, frame=bio, options=options, debug=debug)


def generate_event(
    lang: str,
    event: Any,
    *,
    options: Optional[GenerationOptions] = None,
    debug: bool = False,
) -> GenerationResult:
    return generate(lang=lang, frame=event, options=options, debug=debug)


__all__ = [
    "GenerationOptions",
    "GenerationResult",
    "Engine",
    "NLGSession",
    "generate",
    "generate_bio",
    "generate_event",
]
```
```python
# nlg/api.py

from __future__ import annotations

import asyncio
import inspect
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Sequence, cast

from app.core.domain.models import Frame as WireFrame
from app.core.domain.models import Sentence
from app.core.ports.grammar_engine import IGrammarEngine
from app.shared.container import container


# Optional semantic-frame types (kept for compatibility with older call sites).
try:
    from app.core.domain.semantics.types import BioFrame as BioFrame  # type: ignore
except Exception:  # pragma: no cover
    BioFrame = Any  # type: ignore[misc,assignment]

try:
    # Not all branches define EventFrame; keep it optional.
    from app.core.domain.semantics.types import EventFrame as EventFrame  # type: ignore
except Exception:  # pragma: no cover
    EventFrame = Any  # type: ignore[misc,assignment]


# Public "Frame" type for this module: the current engine contract uses WireFrame.
Frame = WireFrame


# ---------------------------------------------------------------------------
# Public data models
# ---------------------------------------------------------------------------


@dataclass
class GenerationOptions:
    """
    High-level generation controls.

    Note: current engine contract is intentionally small; options are carried
    forward for compatibility but may be ignored by the underlying engine.
    """

    register: Optional[str] = None
    max_sentences: Optional[int] = None
    discourse_mode: Optional[str] = None
    seed: Optional[int] = None

    def to_engine_kwargs(self) -> Dict[str, Any]:
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
    Frontend/client-facing convenience result.

    This is not the canonical public HTTP envelope. It is a consumer-friendly
    model that keeps the traditional `lang`, `sentences`, and `frame` fields,
    while optionally mirroring selected canonical generation fields so callers
    do not lose important runtime/public metadata.
    """

    text: str
    sentences: List[str]
    lang: str
    frame: Any  # accept WireFrame or semantic frames passed by callers
    debug_info: Optional[Dict[str, Any]] = None

    # Optional mirrors of canonical generation fields.
    construction_id: Optional[str] = None
    renderer_backend: Optional[str] = None
    fallback_used: bool = False
    tokens: List[str] = field(default_factory=list)
    generation_time_ms: float = 0.0


# ---------------------------------------------------------------------------
# Engine protocol (adapter boundary)
# ---------------------------------------------------------------------------


class Engine(Protocol):
    """
    Minimal protocol expected from engines/adapters.

    The return value SHOULD be a dict with at least:
      - "text": str

    It MAY also include:
      - "sentences": list[str]
      - "lang_code": str
      - "construction_id": str
      - "renderer_backend": str
      - "fallback_used": bool
      - "tokens": list[str]
      - "generation_time_ms": number
      - "debug_info": dict
    """

    def generate(self, frame: Any, **kwargs: Any) -> Dict[str, Any]:
        ...


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clean_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_lang(value: str) -> str:
    normalized = _clean_optional_str(value)
    if not normalized:
        raise ValueError("Language is required.")
    return normalized.lower()


def _normalize_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, Sequence):
        return []
    out: List[str] = []
    for item in value:
        text = _clean_optional_str(item)
        if text:
            out.append(text)
    return out


def _get_grammar_engine() -> IGrammarEngine:
    # DI container provides the configured grammar engine implementation.
    return cast(IGrammarEngine, container.grammar_engine())


def _run_async(coro: Any) -> Any:
    """
    Run an awaitable from sync code.

    If called while an event loop is already running, raise with guidance to
    use the async API.
    """
    if not inspect.isawaitable(coro):
        return coro

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    raise RuntimeError(
        "nlg.api.generate() was called from within a running event loop. "
        "Use NLGSession.generate_async(...) instead."
    )


def _coerce_to_wire_frame(frame: Any) -> WireFrame:
    """
    Accept several frame shapes and coerce into the WireFrame expected by IGrammarEngine.

    Supported inputs:
      - WireFrame (app.core.domain.models.Frame)
      - dict compatible with WireFrame
      - pydantic model with model_dump() producing WireFrame-compatible dict
      - legacy semantic BioFrame-like objects (best-effort)
    """
    if isinstance(frame, WireFrame):
        return frame

    if isinstance(frame, dict):
        return WireFrame.model_validate(frame)

    if hasattr(frame, "model_dump"):
        data = frame.model_dump()  # type: ignore[attr-defined]
        if isinstance(data, dict):
            return WireFrame.model_validate(data)

    # Best-effort adapter for legacy semantic BioFrame objects:
    # expects fields: main_entity.{name,gender}, primary_profession_lemmas, nationality_lemmas
    if hasattr(frame, "main_entity") and (
        hasattr(frame, "primary_profession_lemmas") or hasattr(frame, "nationality_lemmas")
    ):
        me = getattr(frame, "main_entity", None)
        name = getattr(me, "name", "") if me is not None else ""
        gender = getattr(me, "gender", "") if me is not None else ""

        profession = ""
        nationality = ""

        try:
            profs = getattr(frame, "primary_profession_lemmas", None) or []
            if profs:
                profession = str(profs[0] or "").strip()
        except Exception:
            profession = ""

        try:
            nats = getattr(frame, "nationality_lemmas", None) or []
            if nats:
                nationality = str(nats[0] or "").strip()
        except Exception:
            nationality = ""

        props: Dict[str, Any] = {}
        if profession:
            props["profession"] = profession
        if nationality:
            props["nationality"] = nationality

        return WireFrame(
            frame_type="bio",
            subject={"name": name, "gender": gender},
            properties=props,
        )

    raise TypeError(
        f"Unsupported frame type for generation: {type(frame).__name__}. "
        "Provide app.core.domain.models.Frame (WireFrame) or a compatible dict."
    )


def _split_sentences_fallback(text: str) -> List[str]:
    if not text.strip():
        return []
    chunks = re.split(r"([.!?])", text)
    sentences: List[str] = []
    buf = ""
    for piece in chunks:
        if not piece:
            continue
        buf += piece
        if piece in ".!?":
            sentence = buf.strip()
            if sentence:
                sentences.append(sentence)
            buf = ""
    leftover = buf.strip()
    if leftover:
        sentences.append(leftover)
    return sentences


def _normalize_debug_info(
    debug: bool,
    raw_debug_info: Any,
    options: Optional[GenerationOptions],
) -> Optional[Dict[str, Any]]:
    if not debug:
        return None

    debug_info = dict(raw_debug_info or {})
    if options is not None:
        debug_info.setdefault("options", options.to_engine_kwargs())
    return debug_info


def _build_generation_result(
    *,
    requested_lang: str,
    frame: Any,
    raw: Dict[str, Any],
    options: Optional[GenerationOptions],
    debug: bool,
) -> GenerationResult:
    text = str(raw.get("text", "") or "")
    lang = _normalize_lang(str(raw.get("lang_code") or requested_lang))
    tokens = _normalize_string_list(raw.get("tokens"))
    if not tokens and text:
        tokens = text.split()

    raw_sentences = raw.get("sentences")
    if raw_sentences is None:
        sentences = _split_sentences_fallback(text)
    else:
        sentences = [str(s) for s in cast(Sequence[Any], raw_sentences)]

    debug_info = _normalize_debug_info(
        debug=debug,
        raw_debug_info=raw.get("debug_info"),
        options=options,
    )

    construction_id = _clean_optional_str(raw.get("construction_id"))
    renderer_backend = _clean_optional_str(raw.get("renderer_backend"))
    fallback_used = bool(raw.get("fallback_used", False))

    generation_time_ms_raw = raw.get("generation_time_ms", 0.0)
    try:
        generation_time_ms = max(0.0, float(generation_time_ms_raw))
    except (TypeError, ValueError):
        generation_time_ms = 0.0

    return GenerationResult(
        text=text,
        sentences=sentences,
        lang=lang,
        frame=frame,
        debug_info=debug_info,
        construction_id=construction_id,
        renderer_backend=renderer_backend,
        fallback_used=fallback_used,
        tokens=tokens,
        generation_time_ms=generation_time_ms,
    )


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------


class _AppEngineAdapter:
    """
    Adapter around the app's configured IGrammarEngine (container-backed).
    """

    def __init__(self, lang: str) -> None:
        self.lang = _normalize_lang(lang)
        self._engine = _get_grammar_engine()

    async def generate_async(self, frame: Any, **kwargs: Any) -> Dict[str, Any]:
        debug = bool(kwargs.get("debug", False))
        wire_frame = _coerce_to_wire_frame(frame)
        sentence: Sentence = await self._engine.generate(lang_code=self.lang, frame=wire_frame)

        text = sentence.text
        tokens = list(sentence.tokens) if sentence.tokens else text.split()

        out: Dict[str, Any] = {
            "text": text,
            "sentences": _split_sentences_fallback(text) or [text],
            "lang_code": sentence.lang_code,
            "construction_id": sentence.construction_id,
            "renderer_backend": sentence.renderer_backend,
            "fallback_used": sentence.fallback_used,
            "tokens": tokens,
            "generation_time_ms": sentence.generation_time_ms,
        }

        if debug:
            out["debug_info"] = sentence.debug_info

        return out

    def generate(self, frame: Any, **kwargs: Any) -> Dict[str, Any]:
        return _run_async(self.generate_async(frame, **kwargs))


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

    def generate(
        self,
        lang: str,
        frame: Any,
        *,
        options: Optional[GenerationOptions] = None,
        debug: bool = False,
    ) -> GenerationResult:
        normalized_lang = _normalize_lang(lang)
        engine = self._get_engine(normalized_lang)

        engine_kwargs = options.to_engine_kwargs() if options else {}
        engine_kwargs["debug"] = debug

        raw = engine.generate(frame, **engine_kwargs)

        return _build_generation_result(
            requested_lang=normalized_lang,
            frame=frame,
            raw=raw,
            options=options,
            debug=debug,
        )

    async def generate_async(
        self,
        lang: str,
        frame: Any,
        *,
        options: Optional[GenerationOptions] = None,
        debug: bool = False,
    ) -> GenerationResult:
        """
        Async variant for callers already running an event loop.
        """
        normalized_lang = _normalize_lang(lang)
        engine = self._get_engine(normalized_lang)
        if not isinstance(engine, _AppEngineAdapter):
            # Fallback: run sync engine in thread-compatible way is out of scope here.
            # Keep behavior explicit.
            return self.generate(
                lang=normalized_lang,
                frame=frame,
                options=options,
                debug=debug,
            )

        engine_kwargs = options.to_engine_kwargs() if options else {}
        engine_kwargs["debug"] = debug

        raw = await engine.generate_async(frame, **engine_kwargs)

        return _build_generation_result(
            requested_lang=normalized_lang,
            frame=frame,
            raw=raw,
            options=options,
            debug=debug,
        )

    def _get_engine(self, lang: str) -> Engine:
        normalized_lang = _normalize_lang(lang)
        if normalized_lang in self._engine_cache:
            return self._engine_cache[normalized_lang]

        engine: Engine = _AppEngineAdapter(normalized_lang)
        self._engine_cache[normalized_lang] = engine
        return engine


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

_default_session = NLGSession()


def generate(
    lang: str,
    frame: Any,
    *,
    options: Optional[GenerationOptions] = None,
    debug: bool = False,
) -> GenerationResult:
    return _default_session.generate(lang=lang, frame=frame, options=options, debug=debug)


def generate_bio(
    lang: str,
    bio: Any,
    *,
    options: Optional[GenerationOptions] = None,
    debug: bool = False,
) -> GenerationResult:
    return generate(lang=lang, frame=bio, options=options, debug=debug)


def generate_event(
    lang: str,
    event: Any,
    *,
    options: Optional[GenerationOptions] = None,
    debug: bool = False,
) -> GenerationResult:
    return generate(lang=lang, frame=event, options=options, debug=debug)


__all__ = [
    "GenerationOptions",
    "GenerationResult",
    "Engine",
    "NLGSession",
    "generate",
    "generate_bio",
    "generate_event",
]


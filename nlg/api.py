# nlg/api.py

from __future__ import annotations

import asyncio
import inspect
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable

from app.core.domain.models import Frame as WireFrame

if TYPE_CHECKING:
    from app.core.domain.models import Sentence
    from app.core.ports.grammar_engine import IGrammarEngine


# Public frame type for this module.
Frame = WireFrame


# ---------------------------------------------------------------------------
# Public data models
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class GenerationOptions:
    """
    High-level generation controls.

    The current engine contract is intentionally small. These options are kept
    for compatibility and may be ignored by the underlying engine.
    """

    register: str | None = None
    max_sentences: int | None = None
    discourse_mode: str | None = None
    seed: int | None = None

    def to_engine_kwargs(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.register is not None:
            data["register"] = self.register
        if self.max_sentences is not None:
            data["max_sentences"] = self.max_sentences
        if self.discourse_mode is not None:
            data["discourse_mode"] = self.discourse_mode
        if self.seed is not None:
            data["seed"] = self.seed
        return data


@dataclass(slots=True)
class GenerationResult:
    """
    Consumer-facing convenience result.

    This is not the canonical public HTTP envelope. It preserves the traditional
    `lang`, `sentences`, and `frame` fields while mirroring selected runtime
    metadata from the canonical Sentence model.
    """

    text: str
    sentences: list[str]
    lang: str
    frame: Any
    debug_info: dict[str, Any] | None = None

    construction_id: str | None = None
    renderer_backend: str | None = None
    fallback_used: bool = False
    tokens: list[str] = field(default_factory=list)
    generation_time_ms: float = 0.0


# ---------------------------------------------------------------------------
# Engine protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class Engine(Protocol):
    """
    Minimal sync adapter protocol used by this module.
    """

    def generate(self, frame: Any, **kwargs: Any) -> dict[str, Any]:
        """
        Generate a payload containing at least:
            - text: str

        It may also include:
            - sentences: list[str]
            - lang_code: str
            - construction_id: str
            - renderer_backend: str
            - fallback_used: bool
            - tokens: list[str]
            - generation_time_ms: number
            - debug_info: dict
        """
        ...


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clean_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_lang(value: Any) -> str:
    normalized = _clean_optional_str(value)
    if not normalized:
        raise ValueError("Language is required.")
    return normalized.lower()


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, Sequence):
        return []
    out: list[str] = []
    for item in value:
        text = _clean_optional_str(item)
        if text:
            out.append(text)
    return out


def _get_grammar_engine() -> "IGrammarEngine":
    """
    Resolve the configured grammar engine lazily.

    This avoids importing the DI container at module import time, which reduces
    startup coupling and helps prevent circular-import regressions.
    """
    from app.core.ports.grammar_engine import IGrammarEngine
    from app.shared.container import container

    return cast(IGrammarEngine, container.grammar_engine())


def _run_async(coro_or_value: Any) -> Any:
    """
    Run an awaitable from sync code.

    If called while an event loop is already running, raise with guidance to use
    the async API instead.
    """
    if not inspect.isawaitable(coro_or_value):
        return coro_or_value

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro_or_value)

    raise RuntimeError(
        "nlg.api.generate() was called from within a running event loop. "
        "Use NLGSession.generate_async(...) instead."
    )


async def _await_if_needed(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _coerce_to_wire_frame(frame: Any) -> WireFrame:
    """
    Accept several frame shapes and coerce them into the WireFrame expected by
    the grammar engine.

    Supported inputs:
      - WireFrame
      - dict / Mapping compatible with WireFrame
      - pydantic model with model_dump()
      - legacy object with dict()
      - legacy bio-like object with main_entity / lemma lists
    """
    if isinstance(frame, WireFrame):
        return frame

    if isinstance(frame, Mapping):
        return WireFrame.model_validate(dict(frame))

    if hasattr(frame, "model_dump"):
        data = frame.model_dump()  # type: ignore[attr-defined]
        if isinstance(data, Mapping):
            return WireFrame.model_validate(dict(data))

    if hasattr(frame, "dict"):
        data = frame.dict()  # type: ignore[attr-defined]
        if isinstance(data, Mapping):
            return WireFrame.model_validate(dict(data))

    if hasattr(frame, "main_entity") and (
        hasattr(frame, "primary_profession_lemmas") or hasattr(frame, "nationality_lemmas")
    ):
        main_entity = getattr(frame, "main_entity", None)
        name = _clean_optional_str(getattr(main_entity, "name", None)) or ""
        gender = _clean_optional_str(getattr(main_entity, "gender", None)) or ""
        qid = _clean_optional_str(getattr(main_entity, "qid", None))

        profession = ""
        nationality = ""

        try:
            professions = getattr(frame, "primary_profession_lemmas", None) or []
            if professions:
                profession = _clean_optional_str(professions[0]) or ""
        except Exception:
            profession = ""

        try:
            nationalities = getattr(frame, "nationality_lemmas", None) or []
            if nationalities:
                nationality = _clean_optional_str(nationalities[0]) or ""
        except Exception:
            nationality = ""

        subject: dict[str, Any] = {"name": name, "gender": gender}
        if qid:
            subject["qid"] = qid

        properties: dict[str, Any] = {}
        if profession:
            properties["profession"] = profession
            properties["primary_profession_lemmas"] = [profession]
        if nationality:
            properties["nationality"] = nationality
            properties["nationality_lemmas"] = [nationality]

        return WireFrame(
            frame_type="bio",
            subject=subject,
            main_entity=subject,
            properties=properties,
            primary_profession_lemmas=properties.get("primary_profession_lemmas", []),
            nationality_lemmas=properties.get("nationality_lemmas", []),
        )

    raise TypeError(
        f"Unsupported frame type for generation: {type(frame).__name__}. "
        "Provide app.core.domain.models.Frame or a compatible mapping/model."
    )


def _split_sentences_fallback(text: str) -> list[str]:
    if not text.strip():
        return []
    parts = re.split(r"([.!?])", text)
    sentences: list[str] = []
    buf = ""
    for part in parts:
        if not part:
            continue
        buf += part
        if part in ".!?":
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
    options: GenerationOptions | None,
) -> dict[str, Any] | None:
    if not debug:
        return None

    debug_info = dict(raw_debug_info or {})
    if options is not None:
        debug_info.setdefault("options", options.to_engine_kwargs())
    return debug_info


def _coerce_engine_output(
    result: Any,
    *,
    requested_lang: str,
    debug: bool,
) -> dict[str, Any]:
    """
    Normalize either a canonical Sentence-like object or a dict-like adapter
    payload into a single dict representation.
    """
    if isinstance(result, Mapping):
        payload = dict(result)
    elif hasattr(result, "model_dump"):
        dumped = result.model_dump()  # type: ignore[attr-defined]
        payload = dict(dumped) if isinstance(dumped, Mapping) else {}
    else:
        text = str(getattr(result, "text", "") or "")
        tokens = getattr(result, "tokens", None)
        payload = {
            "text": text,
            "lang_code": getattr(result, "lang_code", requested_lang),
            "construction_id": getattr(result, "construction_id", None),
            "renderer_backend": getattr(result, "renderer_backend", None),
            "fallback_used": bool(getattr(result, "fallback_used", False)),
            "tokens": list(tokens) if tokens else text.split(),
            "generation_time_ms": getattr(result, "generation_time_ms", 0.0),
        }
        if debug:
            payload["debug_info"] = getattr(result, "debug_info", None)

    payload.setdefault("text", "")
    payload.setdefault("lang_code", requested_lang)
    payload.setdefault("fallback_used", False)
    payload.setdefault("generation_time_ms", 0.0)

    if "tokens" not in payload or payload["tokens"] is None:
        payload["tokens"] = str(payload["text"] or "").split()

    if "sentences" not in payload or payload["sentences"] is None:
        text = str(payload["text"] or "")
        payload["sentences"] = _split_sentences_fallback(text) or ([text] if text else [])

    if debug and "debug_info" not in payload:
        payload["debug_info"] = {}

    return payload


def _build_generation_result(
    *,
    requested_lang: str,
    frame: Any,
    raw: dict[str, Any],
    options: GenerationOptions | None,
    debug: bool,
) -> GenerationResult:
    text = str(raw.get("text", "") or "")
    lang = _normalize_lang(raw.get("lang_code") or requested_lang)

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
# Adapter
# ---------------------------------------------------------------------------


class _AppEngineAdapter:
    """
    Adapter around the app's configured grammar engine.
    """

    def __init__(self, lang: str) -> None:
        self.lang = _normalize_lang(lang)
        self._engine = _get_grammar_engine()

    async def generate_async(self, frame: Any, **kwargs: Any) -> dict[str, Any]:
        debug = bool(kwargs.get("debug", False))
        wire_frame = _coerce_to_wire_frame(frame)

        result = await _await_if_needed(
            self._engine.generate(lang_code=self.lang, frame=wire_frame)
        )

        return _coerce_engine_output(
            result,
            requested_lang=self.lang,
            debug=debug,
        )

    def generate(self, frame: Any, **kwargs: Any) -> dict[str, Any]:
        return _run_async(self.generate_async(frame, **kwargs))


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class NLGSession:
    """
    Stateful session that caches per-language adapters.

    Useful for long-running services and batch jobs.
    """

    def __init__(self, *, preload_langs: list[str] | None = None) -> None:
        self._engine_cache: dict[str, Engine] = {}
        if preload_langs:
            for lang in preload_langs:
                self._get_engine(lang)

    def generate(
        self,
        lang: str,
        frame: Any,
        *,
        options: GenerationOptions | None = None,
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
        options: GenerationOptions | None = None,
        debug: bool = False,
    ) -> GenerationResult:
        normalized_lang = _normalize_lang(lang)
        engine = self._get_engine(normalized_lang)

        if isinstance(engine, _AppEngineAdapter):
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

        return self.generate(
            lang=normalized_lang,
            frame=frame,
            options=options,
            debug=debug,
        )

    def _get_engine(self, lang: str) -> Engine:
        normalized_lang = _normalize_lang(lang)
        cached = self._engine_cache.get(normalized_lang)
        if cached is not None:
            return cached

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
    options: GenerationOptions | None = None,
    debug: bool = False,
) -> GenerationResult:
    return _default_session.generate(
        lang=lang,
        frame=frame,
        options=options,
        debug=debug,
    )


def generate_bio(
    lang: str,
    bio: Any,
    *,
    options: GenerationOptions | None = None,
    debug: bool = False,
) -> GenerationResult:
    return generate(
        lang=lang,
        frame=bio,
        options=options,
        debug=debug,
    )


def generate_event(
    lang: str,
    event: Any,
    *,
    options: GenerationOptions | None = None,
    debug: bool = False,
) -> GenerationResult:
    return generate(
        lang=lang,
        frame=event,
        options=options,
        debug=debug,
    )


__all__ = [
    "Frame",
    "GenerationOptions",
    "GenerationResult",
    "Engine",
    "NLGSession",
    "generate",
    "generate_bio",
    "generate_event",
]

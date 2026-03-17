from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _get_value(source: Any, key: str, default: Any = None) -> Any:
    """
    Read a field from either a dict-like object or an attribute-bearing object.
    """
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def _normalize_lang_code(value: Any) -> str:
    return str(value or "").strip().lower()


def _coerce_debug_info(value: Any) -> dict[str, Any]:
    """
    Normalize debug_info into a plain JSON-friendly dict.
    """
    if value is None:
        return {}

    if isinstance(value, Mapping):
        return dict(value)

    if hasattr(value, "model_dump"):
        try:
            dumped = value.model_dump()
            if isinstance(dumped, Mapping):
                return dict(dumped)
        except Exception:
            pass

    if hasattr(value, "__dict__"):
        try:
            raw = vars(value)
            if isinstance(raw, Mapping):
                return dict(raw)
        except Exception:
            pass

    return {"raw_debug_info": str(value)}


def _coerce_tokens(value: Any, *, fallback_text: str) -> list[str]:
    if isinstance(value, list) and all(isinstance(tok, str) for tok in value):
        return value
    return [part for part in str(fallback_text or "").split() if part]


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    return bool(value)


def _coerce_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def map_generation_response(
    result: Any,
    *,
    requested_lang_code: str | None = None,
) -> dict[str, Any]:
    """
    Map a domain/use-case generation result into the public API response shape.

    Canonical public contract:
        {
            "text": "...",
            "lang_code": "en",
            "construction_id": "copula_equative_classification" | null,
            "renderer_backend": "gf" | "family" | "safe_mode" | null,
            "fallback_used": false,
            "tokens": ["..."],
            "debug_info": {...},
            "generation_time_ms": 12.5
        }

    Accepts:
    - Sentence-like objects exposing attributes such as `.text`, `.lang_code`,
      `.debug_info`, `.generation_time_ms`
    - dict-like results with equivalent keys
    - raw string results (best-effort compatibility)

    Raises:
        ValueError: when required response fields cannot be derived.
    """
    if result is None:
        raise ValueError("Generation result cannot be None.")

    text = _get_value(result, "text")
    legacy_surface_key_used = False

    if text is None and isinstance(result, str):
        text = result
    elif text is None:
        legacy_surface_text = _get_value(result, "surface_text")
        if legacy_surface_text is not None:
            text = legacy_surface_text
            legacy_surface_key_used = True

    text = "" if text is None else str(text).strip()
    if not text:
        raise ValueError("Generation result is missing required field 'text'.")

    lang_code = _get_value(result, "lang_code", requested_lang_code)
    if not lang_code:
        lang_code = _get_value(result, "language", requested_lang_code)

    lang_code = _normalize_lang_code(lang_code)
    if not lang_code:
        raise ValueError("Generation result is missing required field 'lang_code'.")

    debug_info = _coerce_debug_info(_get_value(result, "debug_info"))

    if legacy_surface_key_used:
        debug_info.setdefault("legacy_result_key", "surface_text")

    # Top-level promoted fields are authoritative in the public envelope.
    # When missing on the result object, fall back to debug_info if available.
    construction_id = _get_value(result, "construction_id", None)
    if construction_id is None:
        construction_id = debug_info.get("construction_id")

    renderer_backend = _get_value(result, "renderer_backend", None)
    if renderer_backend is None:
        renderer_backend = debug_info.get("renderer_backend")

    fallback_used = _get_value(result, "fallback_used", None)
    if fallback_used is None:
        fallback_used = debug_info.get("fallback_used", False)
    fallback_used = _coerce_bool(fallback_used, default=False)

    tokens = _get_value(result, "tokens", None)
    if tokens is None:
        tokens = debug_info.get("tokens")
    tokens = _coerce_tokens(tokens, fallback_text=text)

    generation_time_ms = _get_value(result, "generation_time_ms", None)
    if generation_time_ms is None:
        generation_time_ms = debug_info.get("generation_time_ms", 0.0)
    generation_time_ms = _coerce_float(generation_time_ms, default=0.0)

    # Preserve useful runtime metadata when it exists outside debug_info.
    promoted_keys = (
        "construction_id",
        "renderer_backend",
        "fallback_used",
        "selected_backend",
        "attempted_backends",
        "tokens",
        "warnings",
        "confidence",
        "slot_keys",
    )
    for key in promoted_keys:
        value = _get_value(result, key, None)
        if value is not None and key not in debug_info:
            debug_info[key] = value

    # Mirror the canonical public fields back into debug_info so observability
    # stays aligned with the top-level response.
    debug_info["lang_code"] = lang_code
    debug_info["fallback_used"] = fallback_used
    debug_info["tokens"] = tokens
    debug_info["generation_time_ms"] = generation_time_ms

    if construction_id is not None:
        debug_info["construction_id"] = construction_id
    if renderer_backend is not None:
        debug_info["renderer_backend"] = renderer_backend

    resolved_language = _get_value(result, "language", None)
    if resolved_language and "resolved_language" not in debug_info:
        debug_info["resolved_language"] = str(resolved_language)

    return {
        "text": text,
        "lang_code": lang_code,
        "construction_id": construction_id,
        "renderer_backend": renderer_backend,
        "fallback_used": fallback_used,
        "tokens": tokens,
        "debug_info": debug_info,
        "generation_time_ms": generation_time_ms,
    }


# Small aliases so router code can read naturally during refactors.
to_generation_response = map_generation_response
generation_response_to_dict = map_generation_response


__all__ = [
    "map_generation_response",
    "to_generation_response",
    "generation_response_to_dict",
]


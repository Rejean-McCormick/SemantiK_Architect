from __future__ import annotations

from collections.abc import Mapping
from typing import Any


CANONICAL_RUNTIME_PATH = "planner_first"
COMPATIBILITY_RUNTIME_PATH = "compatibility_unknown"


def _get_value(source: Any, key: str, default: Any = None) -> Any:
    """
    Read a field from either a dict-like object or an attribute-bearing object.
    """
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def _normalize_lang_code(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalize_nonempty_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


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


def _coerce_tokens(value: Any) -> list[str] | None:
    if isinstance(value, list) and all(isinstance(tok, str) for tok in value):
        return value
    return None


def _tokenize_fallback_text(text: str) -> list[str]:
    return [part for part in str(text or "").split() if part]


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


def _has_compatibility_markers(debug_info: Mapping[str, Any]) -> bool:
    return any(
        key in debug_info
        for key in (
            "compatibility_mode",
            "compatibility_shim",
            "legacy_result_key",
            "fallback_reason",
        )
    )


def _is_nominal_runtime_path(runtime_path: str) -> bool:
    return runtime_path == CANONICAL_RUNTIME_PATH


def map_generation_response(
    result: Any,
    *,
    requested_lang_code: str | None = None,
) -> dict[str, Any]:
    """
    Map a domain/use-case generation result into the canonical public API response.

    Canonical public contract:
        {
            "text": "...",
            "lang_code": "en",
            "construction_id": "copula_equative_classification",
            "renderer_backend": "gf" | "family" | "safe_mode",
            "fallback_used": false,
            "tokens": ["..."],
            "debug_info": {...},
            "generation_time_ms": 12.5
        }

    Accepts:
    - SurfaceResult-like objects exposing canonical attributes
    - dict-like results with equivalent keys
    - compatibility shapes during the migration tail
    - raw string results only as best-effort compatibility input

    Raises:
        ValueError: when required public fields cannot be derived or when a
        nominal planner-first result is missing required canonical top-level
        fields before mapping.
    """
    if result is None:
        raise ValueError("Generation result cannot be None.")

    text = _get_value(result, "text")
    legacy_surface_key_used = False

    if text is None and isinstance(result, str):
        text = result
        legacy_surface_key_used = True
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

    explicit_runtime_path = _normalize_nonempty_string(_get_value(result, "runtime_path"))
    debug_runtime_path = _normalize_nonempty_string(debug_info.get("runtime_path"))
    runtime_path = explicit_runtime_path or debug_runtime_path

    if runtime_path is None:
        compatibility_signals = legacy_surface_key_used or _has_compatibility_markers(debug_info)
        if compatibility_signals:
            runtime_path = COMPATIBILITY_RUNTIME_PATH
        else:
            raise ValueError(
                "Generation result is missing required debug field 'runtime_path'."
            )

    nominal_path = _is_nominal_runtime_path(runtime_path)

    construction_id = _normalize_nonempty_string(_get_value(result, "construction_id"))
    if construction_id is None and not nominal_path:
        construction_id = _normalize_nonempty_string(debug_info.get("construction_id"))
    if construction_id is None:
        raise ValueError(
            "Generation result is missing required field 'construction_id'."
        )

    renderer_backend = _normalize_nonempty_string(_get_value(result, "renderer_backend"))
    if renderer_backend is None and not nominal_path:
        renderer_backend = _normalize_nonempty_string(debug_info.get("renderer_backend"))
    if renderer_backend is None:
        raise ValueError(
            "Generation result is missing required field 'renderer_backend'."
        )

    fallback_used_raw = _get_value(result, "fallback_used", None)
    if fallback_used_raw is None and not nominal_path:
        fallback_used_raw = debug_info.get("fallback_used", True)
    if fallback_used_raw is None and nominal_path:
        raise ValueError(
            "Generation result is missing required field 'fallback_used'."
        )
    fallback_used = _coerce_bool(
        fallback_used_raw,
        default=not nominal_path,
    )

    tokens = _coerce_tokens(_get_value(result, "tokens", None))
    if tokens is None and not nominal_path:
        tokens = _coerce_tokens(debug_info.get("tokens"))

    if tokens is None:
        if nominal_path:
            raise ValueError(
                "Generation result is missing required field 'tokens' on the nominal "
                "planner-first path."
            )
        tokens = _tokenize_fallback_text(text)

    generation_time_raw = _get_value(result, "generation_time_ms", None)
    if generation_time_raw is None and not nominal_path:
        generation_time_raw = debug_info.get("generation_time_ms", 0.0)
    if generation_time_raw is None and nominal_path:
        raise ValueError(
            "Generation result is missing required field 'generation_time_ms'."
        )
    generation_time_ms = _coerce_float(generation_time_raw, default=0.0)

    # Preserve useful runtime metadata when it exists outside debug_info.
    promoted_keys = (
        "selected_backend",
        "attempted_backends",
        "warnings",
        "confidence",
        "slot_keys",
        "backend_trace",
        "resolved_language",
        "fallback_reason",
        "compatibility_mode",
        "compatibility_shim",
        "legacy_result_key",
    )
    for key in promoted_keys:
        value = _get_value(result, key, None)
        if value is not None and key not in debug_info:
            debug_info[key] = value

    resolved_language = _get_value(result, "language", None)
    if resolved_language and "resolved_language" not in debug_info:
        debug_info["resolved_language"] = str(resolved_language)

    # Mirror the canonical public fields back into debug_info so observability
    # stays aligned with the top-level response.
    debug_info["runtime_path"] = runtime_path
    debug_info["lang_code"] = lang_code
    debug_info["construction_id"] = construction_id
    debug_info["renderer_backend"] = renderer_backend
    debug_info["fallback_used"] = fallback_used
    debug_info.setdefault("slot_keys", [])

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


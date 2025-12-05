"""
semantics/aw_bridge.py

Bridge between Wikifunctions-style Z-Objects and the local NLG router.

Goal
----
In Wikifunctions, implementations may receive inputs wrapped in Z-Objects
(e.g. Z6 for strings) instead of plain Python primitives. This module:

1. Safely unwraps Z-Objects into native Python types (recursively).
2. Normalizes a generic "render this construction" request.
3. Calls the local `router.render(...)`.
4. Wraps the final surface string back into a Z6 object (if desired).

Typical Wikifunctions usage
---------------------------

Implementation pseudo-code for a generic "render clause" function:

    from semantics.aw_bridge import render_from_z_call

    def impl(z_args):
        # `z_args` is a dict containing construction id, language, slots, etc.
        # Wikifunctions will pass Z-Objects here; locally you can call this
        # function directly with plain Python values or Z-wrapped ones.
        return render_from_z_call(z_args)

Expected input shape
--------------------

`render_from_z_call` expects a single argument: a dict (possibly Z-wrapped)
with at least:

    {
        "construction_id": "copula_equative_simple",  # or Z6(...)
        "lang_code": "fr",                            # or "language"/"lang"
        "slots": {
            # arbitrary construction-specific slots
            "SUBJ": {"surface": "Marie Curie"},
            "PRED_NP": {
                "lemma": "physicist",
                "pos": "NOUN",
                "features": {"gender": "f", "number": "sg"},
            },
        },
    }

Key aliases supported:

    - construction_id: "construction_id" | "construction" | "template"
    - lang_code:       "lang_code" | "language" | "lang"
    - slots:           "slots" | "arguments" | "args"

All values can be plain Python objects or Z-Objects; everything is
recursively unwrapped before calling the router.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

try:
    # Preferred: use the local mock that understands Z6/Z9
    from utils.wikifunctions_api_mock import unwrap as wf_unwrap, Z6
except Exception:  # pragma: no cover - extremely defensive
    # Fallbacks so this module still works outside this repository
    def wf_unwrap(obj: Any) -> Any:
        return obj

    def Z6(text: str) -> Dict[str, Any]:
        return {"Z1K1": "Z6", "Z6K1": text}


# The router is the main entry point into the NLG system.
import router


# ---------------------------------------------------------------------------
# Z-object helpers
# ---------------------------------------------------------------------------


def unwrap_recursive(obj: Any) -> Any:
    """
    Recursively unwrap Wikifunctions Z-Objects into plain Python types.

    Rules:
        - First, pass the object through `wf_unwrap` (handles Z6/Z9, etc.).
        - If the result is a dict, unwrap its values recursively.
        - If the result is a list/tuple, unwrap each element.
        - Otherwise, return the value as-is.

    This lets callers pass a deeply nested structure containing Z-Objects
    anywhere and receive a plain Python structure back.
    """
    base = wf_unwrap(obj)

    if isinstance(base, dict):
        return {k: unwrap_recursive(v) for k, v in base.items()}

    if isinstance(base, (list, tuple)):
        return [unwrap_recursive(v) for v in base]

    return base


# ---------------------------------------------------------------------------
# Normalization of a generic NLG call
# ---------------------------------------------------------------------------


def _pick_first(d: Dict[str, Any], *keys: str) -> Any:
    """
    Return the first non-missing key from `d` among `keys`.

    Example:
        lang = _pick_first(data, "lang_code", "language", "lang")
    """
    for key in keys:
        if key in d:
            return d[key]
    return None


def normalize_nlg_call(z_call: Dict[str, Any]) -> Tuple[str, Dict[str, Any], str]:
    """
    Normalize a Wikifunctions-style call into:

        (construction_id, slots_dict, lang_code)

    Steps:
        1. Recursively unwrap all Z-Objects in `z_call`.
        2. Resolve aliases for construction id, language code, and slots.
        3. Validate types and return normalized values.

    Raises:
        ValueError / TypeError if required fields are missing or malformed.
    """
    if not isinstance(z_call, dict):
        raise TypeError(f"Expected top-level dict for z_call, got {type(z_call)}")

    plain: Dict[str, Any] = unwrap_recursive(z_call)

    construction_id = _pick_first(plain, "construction_id", "construction", "template")
    lang_code = _pick_first(plain, "lang_code", "language", "lang")
    slots = _pick_first(plain, "slots", "arguments", "args")

    if construction_id is None:
        raise ValueError(
            "Missing 'construction_id' (or alias 'construction' / 'template') "
            "in NLG call."
        )

    if lang_code is None:
        raise ValueError(
            "Missing 'lang_code' (or alias 'language' / 'lang') in NLG call."
        )

    if slots is None:
        slots = {}

    if not isinstance(slots, dict):
        raise TypeError(f"'slots' must be a dict after unwrapping, got {type(slots)}")

    return str(construction_id), slots, str(lang_code)


# ---------------------------------------------------------------------------
# Public bridge API
# ---------------------------------------------------------------------------


def render_from_z_call(z_call: Dict[str, Any], wrap_result: bool = True) -> Any:
    """
    Main bridge function: take a Wikifunctions-style payload, return surface text.

    Args:
        z_call:
            Dict that may contain Wikifunctions Z-Objects anywhere. Must specify:
                - construction_id / construction / template
                - lang_code / language / lang
                - slots / arguments / args (optional, defaults to {})
        wrap_result:
            If True (default), wrap the resulting string in a Z6 object.
            If False, return the raw Python string.

    Returns:
        Either:
            - A Z6-wrapped string (default), e.g. {"Z1K1": "Z6", "Z6K1": "..."}
            - A plain Python string, if wrap_result=False.

    Raises:
        ValueError / TypeError if the input is missing required fields or
        has the wrong top-level type.
    """
    construction_id, slots, lang_code = normalize_nlg_call(z_call)

    # Delegate to the central router; it decides which engine/constructions
    # to use based on `lang_code` and `construction_id`.
    surface_text: str = router.render(
        construction_id=construction_id,
        slots=slots,
        lang_code=lang_code,
    )

    if wrap_result:
        return Z6(surface_text)

    return surface_text


__all__ = [
    "unwrap_recursive",
    "normalize_nlg_call",
    "render_from_z_call",
]

"""
semantics/normalization.py
==========================

Light-weight helpers to turn “messy” abstract inputs into a clean,
predictable shape before they hit the engines / constructions.

This module focuses on three things:

1. Unwrapping Wikifunctions Z-objects (Z6, Z9) into native Python types.
2. Normalizing core biography semantics:
   - name
   - gender
   - profession / nationality lemmas
   - target language code
3. Normalizing simple information-structure features:
   - topic / focus / background role labels

The goal is *not* to prescribe a single global semantic model, but to give
you a stable, minimal contract so that:

- router.render_biography(...) can accept a variety of inputs
- future construction-based renderers can rely on uniform fields
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union

try:
    # Preferred: use the project’s Wikifunctions mock if available
    from utils.wikifunctions_api_mock import unwrap as _unwrap_zobject
except ImportError:  # pragma: no cover - defensive fallback for isolated use

    def _unwrap_zobject(obj: Any) -> Any:
        """
        Minimal fallback: return plain strings as-is, unwrap naive Z6/Z9 dicts,
        otherwise return the object unchanged.
        """
        if isinstance(obj, str):
            return obj
        if isinstance(obj, dict):
            t = obj.get("Z1K1")
            if t == "Z6":
                return obj.get("Z6K1", "")
            if t == "Z9":
                return obj.get("Z9K1", "")
        return obj


# ---------------------------------------------------------------------------
# Dataclasses used by callers
# ---------------------------------------------------------------------------


@dataclass
class BioSemantics:
    """
    Canonical semantic input for a simple encyclopedic biography sentence,
    e.g. "Marie Curie was a Polish physicist."

    Fields:

    - name: surface name (already in target script / orthography)
    - gender: normalized gender label
        "male" | "female" | "nonbinary" | "unknown" | "other"
    - profession_lemma: lemma key used by engines / lexicons
    - nationality_lemma: lemma key used by engines / lexicons
    - language: BCP-47 / ISO 639-1 language code (e.g. "en", "fr", "ja")
    - extra: free bag of additional semantic / discourse info
    """

    name: str
    gender: str
    profession_lemma: str
    nationality_lemma: str
    language: str
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InfoStructure:
    """
    Information-structure annotations for a single clause.

    - topic:   list of role labels that function as TOPIC (e.g. ["SUBJ"])
    - focus:   list of role labels in FOCUS (e.g. ["PRED_NP"])
    - background: list of role labels that are de-emphasized / given
    """

    topic: List[str] = field(default_factory=list)
    focus: List[str] = field(default_factory=list)
    background: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Primitive normalizers
# ---------------------------------------------------------------------------


def _normalize_string(value: Any) -> str:
    """
    Turn arbitrary input (incl. Z-objects) into a clean Python string.

    - Unwraps Z6/Z9 via _unwrap_zobject
    - Converts non-strings via str(...)
    - Strips leading/trailing whitespace
    """
    value = _unwrap_zobject(value)
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return value.strip()


def _lower_ascii(value: Any) -> str:
    """
    Lowercase helper for ASCII-ish tokens (gender codes, language codes).
    """
    s = _normalize_string(value)
    return s.lower()


# ---------------------------------------------------------------------------
# Gender normalization
# ---------------------------------------------------------------------------


# Known Wikidata gender QIDs for convenience (not exhaustive, but useful).
_WD_MALE = {"Q6581097"}
_WD_FEMALE = {"Q6581072"}
_WD_NONBINARY = {"Q48270", "Q1097630"}


def normalize_gender(raw: Any) -> str:
    """
    Normalize a gender value to one of:

        "male" | "female" | "nonbinary" | "unknown" | "other"

    Accepts:

    - Plain strings: "M", "male", "Female", "f", etc.
    - Wikidata QIDs: "Q6581097" (male), "Q6581072" (female), etc.
    - Z-objects or arbitrary types (converted to string as a last resort).
    """
    if raw is None:
        return "unknown"

    unwrapped = _unwrap_zobject(raw)

    # If we got a mapping that looks like a Wikidata entity, try to use its id.
    if isinstance(unwrapped, Mapping):
        # Example shapes:
        #   {"id": "Q6581097", ...}
        #   {"wikidata_qid": "Q6581097", ...}
        qid = unwrapped.get("id") or unwrapped.get("wikidata_qid")
        if isinstance(qid, str):
            return normalize_gender(qid)

    token = _lower_ascii(unwrapped)

    if not token:
        return "unknown"

    # QID handling
    if token in _WD_MALE:
        return "male"
    if token in _WD_FEMALE:
        return "female"
    if token in _WD_NONBINARY:
        return "nonbinary"

    # Common textual variants
    if token in {"m", "male", "man", "masculine"}:
        return "male"
    if token in {"f", "female", "woman", "feminine"}:
        return "female"
    if token in {"nonbinary", "non-binary", "nb", "enby"}:
        return "nonbinary"
    if token in {"unknown", "unspecified", "na", "n/a", "none"}:
        return "unknown"

    # Anything else is marked as "other" so downstream logic can branch if needed.
    return "other"


# ---------------------------------------------------------------------------
# Information-structure normalization
# ---------------------------------------------------------------------------


def _ensure_role_list(value: Any) -> List[str]:
    """
    Normalize value to a list of role labels (strings).

    Accepts:
    - None        → []
    - "SUBJ"      → ["SUBJ"]
    - ["SUBJ"]    → ["SUBJ"]
    - {"role": "SUBJ"} → ["SUBJ"]
    - arbitrary sequences → list of stringified elements
    """
    if value is None:
        return []

    value = _unwrap_zobject(value)

    # Single string
    if isinstance(value, str):
        v = value.strip()
        return [v] if v else []

    # Mapping with a 'role' field
    if isinstance(value, Mapping) and "role" in value:
        r = _normalize_string(value["role"])
        return [r] if r else []

    # Sequence of things
    if isinstance(value, Sequence):
        out: List[str] = []
        for elem in value:
            s = _normalize_string(elem)
            if s:
                out.append(s)
        return out

    # Fallback: single value coerced to string
    s = _normalize_string(value)
    return [s] if s else []


def normalize_info_structure(raw: Optional[Mapping[str, Any]]) -> InfoStructure:
    """
    Normalize a loosely structured information-structure spec into InfoStructure.

    Accepted shapes (examples):

        raw = {
            "topic": "SUBJ",
            "focus": ["PRED_NP"],
        }

        raw = {
            "topic_role": "SUBJ",
            "focus_roles": ["PRED_NP", "OBL_TIME"],
            "background": "LOCATION"
        }

    Returns:
        InfoStructure(topic=[...], focus=[...], background=[...])
    """
    if not raw:
        return InfoStructure()

    # Accept both long and short key names
    topic_val = (
        raw.get("topic")
        or raw.get("topic_role")
        or raw.get("topics")
        or raw.get("topic_roles")
    )
    focus_val = (
        raw.get("focus")
        or raw.get("focus_role")
        or raw.get("foci")
        or raw.get("focus_roles")
    )
    background_val = (
        raw.get("background")
        or raw.get("background_roles")
        or raw.get("given")
        or raw.get("given_roles")
    )

    return InfoStructure(
        topic=_ensure_role_list(topic_val),
        focus=_ensure_role_list(focus_val),
        background=_ensure_role_list(background_val),
    )


# ---------------------------------------------------------------------------
# Biography input normalization
# ---------------------------------------------------------------------------


def normalize_bio_semantics(
    raw: Union[Mapping[str, Any], Sequence[Any]],
    *,
    default_lang: str = "en",
) -> BioSemantics:
    """
    Normalize a variety of biography input shapes into a BioSemantics object.

    Supported patterns:

    1) Dict-style (recommended):

        raw = {
            "name": "Marie Curie",
            "gender": "female",
            "profession": "physicist",
            "nationality": "polish",
            "language": "fr",
            # Optional extras:
            "birth_year": 1867,
            "death_year": 1934,
            "info_structure": {...},  # will be kept in .extra
        }

    2) Positional list/tuple (legacy):

        raw = ["Marie Curie", "female", "physicist", "polish", "fr"]

    3) Wikifunctions call pattern with Z-object wrappers:

        raw = {
            "Z1K1": "Z7",
            "K1": { "Z1K1": "Z6", "Z6K1": "Marie Curie" },      # name
            "K2": { "Z1K1": "Z6", "Z6K1": "female" },           # gender
            "K3": { "Z1K1": "Z6", "Z6K1": "physicist" },        # profession
            "K4": { "Z1K1": "Z6", "Z6K1": "polish" },           # nationality
            "K5": { "Z1K1": "Z6", "Z6K1": "fr" },               # language
        }

    Any unknown keys are preserved in `extra`.
    """
    # Case 1: mapping / dict
    if isinstance(raw, Mapping):
        # Try the obvious keys first
        name = _normalize_string(
            raw.get("name")
            or raw.get("label")
            or raw.get("K1")  # Wikifunctions positional convention
        )

        gender_raw = raw.get("gender") or raw.get("sex") or raw.get("K2")
        gender = normalize_gender(gender_raw)

        prof_lemma = _normalize_string(
            raw.get("profession")
            or raw.get("occupation")
            or raw.get("prof_lemma")
            or raw.get("K3")
        )

        nat_lemma = _normalize_string(
            raw.get("nationality")
            or raw.get("citizenship")
            or raw.get("nat_lemma")
            or raw.get("K4")
        )

        lang_code = _lower_ascii(raw.get("language") or raw.get("lang") or raw.get("K5"))
        if not lang_code:
            lang_code = _lower_ascii(default_lang)

        # Collect extras (everything that is not one of the canonical fields)
        extra: Dict[str, Any] = {}
        for k, v in raw.items():
            if k in {
                "name",
                "label",
                "gender",
                "sex",
                "profession",
                "occupation",
                "prof_lemma",
                "nationality",
                "citizenship",
                "nat_lemma",
                "language",
                "lang",
                "K1",
                "K2",
                "K3",
                "K4",
                "K5",
            }:
                continue
            extra[k] = v

        return BioSemantics(
            name=name,
            gender=gender,
            profession_lemma=prof_lemma,
            nationality_lemma=nat_lemma,
            language=lang_code,
            extra=extra,
        )

    # Case 2: positional sequence
    if isinstance(raw, Sequence):
        # We are liberal in what we accept; missing fields become empty/unknown.
        seq = list(raw)

        def _idx(i: int, default: Any = "") -> Any:
            return seq[i] if i < len(seq) else default

        name = _normalize_string(_idx(0, ""))
        gender = normalize_gender(_idx(1, None))
        prof_lemma = _normalize_string(_idx(2, ""))
        nat_lemma = _normalize_string(_idx(3, ""))
        lang_code = _lower_ascii(_idx(4, default_lang))

        return BioSemantics(
            name=name,
            gender=gender,
            profession_lemma=prof_lemma,
            nationality_lemma=nat_lemma,
            language=lang_code,
            extra={},  # no place for extras in positional form
        )

    # Fallback: treat any other type as a “name-only” input; everything else unknown.
    name = _normalize_string(raw)
    return BioSemantics(
        name=name,
        gender="unknown",
        profession_lemma="",
        nationality_lemma="",
        language=_lower_ascii(default_lang),
        extra={"raw": raw},
    )


# ---------------------------------------------------------------------------
# Convenience composite helper
# ---------------------------------------------------------------------------


def normalize_bio_with_info(
    raw_bio: Union[Mapping[str, Any], Sequence[Any]],
    raw_info_structure: Optional[Mapping[str, Any]] = None,
    *,
    default_lang: str = "en",
) -> Dict[str, Any]:
    """
    Convenience wrapper that returns a plain dict combining:

        - normalized biography semantics
        - normalized information structure

    Result schema:

        {
            "bio": BioSemantics(...),
            "info_structure": InfoStructure(...)
        }

    This is intentionally a plain dict so that it can be JSON-ified or
    passed directly into engines / constructions without requiring callers
    to import the dataclasses.
    """
    bio = normalize_bio_semantics(raw_bio, default_lang=default_lang)
    info = normalize_info_structure(raw_info_structure or {})

    return {
        "bio": bio,
        "info_structure": info,
    }


__all__ = [
    "BioSemantics",
    "InfoStructure",
    "normalize_gender",
    "normalize_info_structure",
    "normalize_bio_semantics",
    "normalize_bio_with_info",
]

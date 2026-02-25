# discourse\referring_expression.py
"""
discourse/referring_expression.py
=================================

Referring expression selection: decide *how* to refer to an entity in
context (full name, short name, pronoun, generic description, etc.),
without doing any language-specific morphology.

This module sits between:

- semantics (which defines what an `entity` is), and
- morphology (which knows how to realize names / pronouns as strings).

It returns a small, language-agnostic *NP specification* that the
morphology layer can realize into a surface noun phrase.

----------------------------------------------------------------------
Expected inputs
----------------------------------------------------------------------

`entity`: a semantic entity object, typically a dict with fields like:

    {
        "id": "Q123",
        "name": "Marie Curie",
        "short_name": "Curie",          # optional
        "gender": "female",             # "female" | "male" | "other" | ...
        "number": "sg",                 # "sg" | "pl"
        "human": True,
        "person": 3,
        "type": "person",               # optional
    }

This module does not enforce a strict schema; it uses these keys if present
and falls back to reasonable defaults otherwise.

`discourse_info`: a small dict describing the entity's status in discourse:

    {
        "is_first_mention": bool,
        "is_topic": bool,
        "is_focus": bool,
        "force_pronoun": bool,          # optional override
    }

`lang_profile`: language profile (router-level configuration) may include
a section:

    "referring_expression": {
        "allow_pronouns": true,
        "use_pronoun_for_topic_after_first_mention": true,
        "use_short_name_after_first_mention": true
    }

All keys are optional; sensible defaults are used when missing.

----------------------------------------------------------------------
Output: NP specification
----------------------------------------------------------------------

The main function `select_np_spec(...)` returns a dict like:

    {
        "realization_type": "pronoun" | "name" | "short_name" | "description",
        "lemma": "Marie Curie",                 # or None for pronouns
        "features": {
            "definiteness": "def",
            "person": 3,
            "number": "sg",
            "gender": "fem",
            "human": True,
            "pronoun_type": "personal"         # for pronouns
        }
    }

The morphology layer is responsible for converting this spec into
language-specific strings (articles, pronoun forms, agreement, etc.).
"""

from __future__ import annotations

from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _get_ref_cfg(lang_profile: Dict[str, Any]) -> Dict[str, Any]:
    return lang_profile.get("referring_expression", {}) or {}


def _flag(cfg: Dict[str, Any], key: str, default: bool) -> bool:
    value = cfg.get(key)
    if value is None:
        return default
    return bool(value)


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------


def _entity_gender(entity: Dict[str, Any]) -> Optional[str]:
    """
    Map entity.gender to a canonical value if present.

    Returns:
        "fem" | "masc" | "other" | None
    """
    g_raw = entity.get("gender")
    if not g_raw:
        return None

    g = str(g_raw).lower()
    if g.startswith("f"):
        return "fem"
    if g.startswith("m"):
        return "masc"
    return "other"


def _entity_number(entity: Dict[str, Any]) -> str:
    n_raw = entity.get("number", "sg")
    n = str(n_raw).lower()
    if n in ("pl", "plural"):
        return "pl"
    return "sg"


def _entity_person(entity: Dict[str, Any]) -> int:
    p_raw = entity.get("person", 3)
    try:
        return int(p_raw)
    except Exception:
        return 3


def _entity_is_human(entity: Dict[str, Any]) -> bool:
    if "human" in entity:
        return bool(entity["human"])
    t = str(entity.get("type", "")).lower()
    return t in ("person", "human", "person_entity")


def _build_base_features(entity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Base morphological features for any NP referring to this entity.
    """
    feats: Dict[str, Any] = {
        "person": _entity_person(entity),
        "number": _entity_number(entity),
        "gender": _entity_gender(entity),
        "human": _entity_is_human(entity),
        "definiteness": "def",  # references in discourse are typically definite
    }
    return feats


# ---------------------------------------------------------------------------
# Core decision logic
# ---------------------------------------------------------------------------


def should_use_pronoun(
    entity: Dict[str, Any],
    discourse_info: Dict[str, Any],
    lang_profile: Dict[str, Any],
) -> bool:
    """
    Decide whether to use a pronoun to refer to this entity in this context.

    Heuristics:
    - Never use pronouns on the first mention.
    - Only use pronouns if:
        - `allow_pronouns` (profile) is True, AND
        - entity is human OR profile opts into pronouns for non-human, AND
        - the entity is not the only mention in the discourse (to avoid
          ambiguous pronouns in one-sentence outputs).
    - Prefer pronouns when:
        - `is_topic` is True or `force_pronoun` is True, and
        - not first mention.
    """
    cfg = _get_ref_cfg(lang_profile)

    if discourse_info.get("force_pronoun"):
        # Caller explicitly asked for a pronoun (e.g. in constructions).
        return True

    if discourse_info.get("is_first_mention", False):
        return False

    allow_pronouns = _flag(cfg, "allow_pronouns", True)
    if not allow_pronouns:
        return False

    human_only_pronouns = _flag(cfg, "pronouns_for_humans_only", True)
    if human_only_pronouns and not _entity_is_human(entity):
        return False

    use_pronoun_for_topic = _flag(
        cfg,
        "use_pronoun_for_topic_after_first_mention",
        True,
    )
    if use_pronoun_for_topic and discourse_info.get("is_topic", False):
        return True

    # Generic heuristic: if not first mention and not special, we *may*
    # still prefer pronouns for humans.
    if _entity_is_human(entity):
        return True

    return False


def should_use_short_name(
    entity: Dict[str, Any],
    discourse_info: Dict[str, Any],
    lang_profile: Dict[str, Any],
) -> bool:
    """
    Decide whether to use a short name (family name, last name, etc.)
    for this entity, instead of full name.

    Heuristics:
    - Only after first mention.
    - Only if a short_name is available.
    """
    cfg = _get_ref_cfg(lang_profile)

    if discourse_info.get("is_first_mention", False):
        return False

    if not entity.get("short_name"):
        return False

    return _flag(cfg, "use_short_name_after_first_mention", True)


# ---------------------------------------------------------------------------
# NP spec builders
# ---------------------------------------------------------------------------


def _build_pronoun_spec(entity: Dict[str, Any]) -> Dict[str, Any]:
    feats = _build_base_features(entity)
    feats["pronoun_type"] = "personal"
    # Pronoun lemma is language-dependent; morphology will decide.
    return {
        "realization_type": "pronoun",
        "lemma": None,
        "features": feats,
    }


def _build_full_name_spec(entity: Dict[str, Any]) -> Dict[str, Any]:
    name = entity.get("name")
    if not name:
        # Fallback: if no explicit name, treat as generic description with head lemma.
        head = entity.get("head_lemma") or entity.get("label") or "entity"
        feats = _build_base_features(entity)
        feats["definiteness"] = "def"
        return {
            "realization_type": "description",
            "lemma": head,
            "features": feats,
        }

    feats = _build_base_features(entity)
    feats["named_entity"] = True
    return {
        "realization_type": "name",
        "lemma": str(name),
        "features": feats,
    }


def _build_short_name_spec(entity: Dict[str, Any]) -> Dict[str, Any]:
    short = entity.get("short_name") or entity.get("name")
    feats = _build_base_features(entity)
    feats["named_entity"] = True
    feats["short_form"] = True
    return {
        "realization_type": "short_name",
        "lemma": str(short),
        "features": feats,
    }


def _build_description_spec(entity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Basic descriptive NP: usually a head lemma like 'physicist',
    with features indicating human, gender, number, etc.

    This is useful for non-named referents or when the construction
    wants to use NP as predicate (copular sentences).
    """
    head = entity.get("head_lemma") or entity.get("label") or "entity"
    feats = _build_base_features(entity)
    feats["definiteness"] = "def"
    return {
        "realization_type": "description",
        "lemma": str(head),
        "features": feats,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def select_np_spec(
    entity: Dict[str, Any],
    discourse_info: Optional[Dict[str, Any]],
    lang_profile: Dict[str, Any],
    *,
    allow_description_fallback: bool = True,
) -> Dict[str, Any]:
    """
    Main entrypoint: decide how to refer to `entity` in this context.

    Args:
        entity:
            Semantic entity dict (see module docstring).
        discourse_info:
            Dict with:
                - is_first_mention: bool
                - is_topic: bool
                - is_focus: bool
                - force_pronoun: bool (optional)
            May be None, in which case we treat it as "first mention, not topic".
        lang_profile:
            Language profile dict (from router).
        allow_description_fallback:
            If True, and the entity has neither a name nor a short_name, we
            fall back to a descriptive NP spec.

    Returns:
        An NP specification dict with keys:
            - realization_type: "pronoun" | "name" | "short_name" | "description"
            - lemma: str or None
            - features: dict
    """
    if discourse_info is None:
        discourse_info = {
            "is_first_mention": True,
            "is_topic": False,
            "is_focus": False,
        }

    # 1. Pronoun?
    if should_use_pronoun(entity, discourse_info, lang_profile):
        return _build_pronoun_spec(entity)

    # 2. Short name?
    if should_use_short_name(entity, discourse_info, lang_profile):
        return _build_short_name_spec(entity)

    # 3. Full name (default for first mention and named entities)
    if entity.get("name"):
        return _build_full_name_spec(entity)

    # 4. Description fallback
    if allow_description_fallback:
        return _build_description_spec(entity)

    # 5. Absolute last resort: opaque "entity"
    return {
        "realization_type": "description",
        "lemma": "entity",
        "features": _build_base_features(entity),
    }


__all__ = [
    "select_np_spec",
    "should_use_pronoun",
    "should_use_short_name",
]

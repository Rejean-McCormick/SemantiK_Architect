"""
discourse/info_structure.py
===========================

Heuristics for assigning *information-structure* labels (topic, focus,
background) to simple clauses, especially biographical first sentences.

This module is deliberately lightweight:

- It does NOT try to model full discourse or all languages.
- It provides a small set of helpers that constructions can consult to
  decide whether to generate a topic-comment pattern, use a pronoun, etc.

It builds on the `InfoStructure` and `BioSemantics` types defined in
`semantics.normalization`.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from semantics.normalization import (
    BioSemantics,
    InfoStructure,
    normalize_info_structure,
)


# ---------------------------------------------------------------------------
# Basic defaults for biography-like sentences
# ---------------------------------------------------------------------------


def default_bio_first_sentence_info(
    main_predicate_role: str = "PRED_NP",
) -> InfoStructure:
    """
    Default information-structure for *first* biographical sentence:

        [TOPIC]   SUBJ (the person)
        [FOCUS]   main predicate NP (profession/nationality)
        [BACKGROUND] empty

    Role labels are intentionally abstract:
    - "SUBJ"       → subject entity (the biography's main person)
    - "PRED_NP"    → the main predicate NP (profession, role, etc.)

    Downstream constructions can interpret these labels in their own way.
    """
    return InfoStructure(
        topic=["SUBJ"],
        focus=[main_predicate_role],
        background=[],
    )


def default_bio_followup_sentence_info(
    main_predicate_role: str = "PRED_NP",
) -> InfoStructure:
    """
    Default information-structure for *subsequent* biographical sentences
    about the same person:

        [TOPIC]   SUBJ (still the person)
        [FOCUS]   main predicate NP (new fact)
        [BACKGROUND] empty (or optionally filled by caller)

    This is almost the same as the first-sentence default, but keeping
    them separate makes it clearer for callers and future extensions
    (e.g., marking SUBJ as given/background in some languages).
    """
    return InfoStructure(
        topic=["SUBJ"],
        focus=[main_predicate_role],
        background=[],
    )


# ---------------------------------------------------------------------------
# Combining defaults with user / upstream hints
# ---------------------------------------------------------------------------


def apply_override(
    base: InfoStructure,
    override_raw: Optional[Mapping[str, Any]],
) -> InfoStructure:
    """
    Apply a *loose* override on top of a base InfoStructure.

    The override is first normalized with `semantics.normalize_info_structure`,
    so it can use a variety of shapes:

        override_raw = {
            "topic": "SUBJ",
            "focus": ["PRED_NP"],
            "background": "LOCATION"
        }

    Rules:
    - If override.topic is non-empty, it replaces base.topic.
    - If override.focus is non-empty, it replaces base.focus.
    - If override.background is non-empty, it replaces base.background.
    - Otherwise, base values are kept.

    This allows callers (or test cases) to specify only the parts they
    care about, without having to restate everything.
    """
    if not override_raw:
        return base

    override_norm = normalize_info_structure(override_raw)

    topic = override_norm.topic or base.topic
    focus = override_norm.focus or base.focus
    background = override_norm.background or base.background

    return InfoStructure(topic=topic, focus=focus, background=background)


# ---------------------------------------------------------------------------
# High-level helper for biography frames
# ---------------------------------------------------------------------------


def infer_bio_info_structure(
    bio: BioSemantics,
    *,
    is_first_sentence: bool = True,
    main_predicate_role: str = "PRED_NP",
    user_override: Optional[Mapping[str, Any]] = None,
) -> InfoStructure:
    """
    Infer an InfoStructure object for a biography sentence.

    Parameters
    ----------
    bio:
        The normalized BioSemantics object (currently not deeply inspected;
        present for future extensions where different biographies might
        trigger different patterns).
    is_first_sentence:
        If True, use the “first sentence” defaults (definitional statement).
        If False, use the “follow-up sentence” defaults.
    main_predicate_role:
        Role label for the main predicate NP in the construction.
        By convention we use "PRED_NP" for copular equatives / attributes.
    user_override:
        Optional loose dict to override topic/focus/background.
        Passed through `apply_override`.

    Returns
    -------
    InfoStructure
        A normalized InfoStructure instance with topic/focus/background lists.
    """
    del bio  # currently unused; kept for future richer heuristics

    if is_first_sentence:
        base = default_bio_first_sentence_info(main_predicate_role=main_predicate_role)
    else:
        base = default_bio_followup_sentence_info(
            main_predicate_role=main_predicate_role
        )

    return apply_override(base, user_override)


__all__ = [
    "default_bio_first_sentence_info",
    "default_bio_followup_sentence_info",
    "apply_override",
    "infer_bio_info_structure",
]

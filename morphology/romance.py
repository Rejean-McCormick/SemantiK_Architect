"""
ROMANCE MORPHOLOGY LAYER
------------------------

Shared morphology helpers for Romance languages (it, es, fr, pt, ro, ca, …).

This module is intentionally “data-driven”:

* All language-specific behaviour comes from a JSON config (per language).
* The code below only knows how to:
  - Inflect gendered lemmas using suffix rules + irregular maps.
  - Select indefinite articles based on phonetic triggers.

Typical config shape (per language):

{
  "articles": {
    "m": {
      "default": "un",
      "vowel": "un",
      "s_impure": "uno",
      "stressed_a": "un"
    },
    "f": {
      "default": "una",
      "vowel": "un'"
    }
  },
  "morphology": {
    "suffixes": [
      { "ends_with": "tore", "replace_with": "trice" },
      { "ends_with": "o",    "replace_with": "a" }
    ],
    "irregulars": {
      "attore": "attrice"
    }
  },
  "phonetics": {
    "impure_triggers": ["s_consonant", "z", "gn"],
    "stressed_a_words": ["águila", "agua"]
  }
}

Nothing in this file is Wikifunctions-specific; it’s plain Python.
"""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional, Tuple

Gender = Literal["male", "female"]

_ROMANCE_VOWELS = "aeiouàèìòùáéíóúâêîôûAEIOUÀÈÌÒÙÁÉÍÓÚÂÊÎÔÛ"


def _normalize_gender(gender: str) -> Gender:
    """
    Normalize a free-form gender string into 'male' or 'female'.

    Anything that is not clearly 'female' is treated as 'male', because
    Romance profession lemmas are conventionally stored in masculine form.
    """
    g = (gender or "").strip().lower()
    if g in {"f", "female", "fem", "woman", "w"}:
        return "female"
    return "male"


def _preserve_capitalisation(original: str, inflected: str) -> str:
    """
    Preserve leading capitalisation from the original lemma.

    Example:
        original='Italiano', inflected='italiana' -> 'Italiana'
    """
    if not original:
        return inflected
    if original[0].isupper() and inflected:
        return inflected[0].upper() + inflected[1:]
    return inflected


def inflect_gendered_lemma(
    lemma: str,
    gender: str,
    morphology_cfg: Dict[str, Any],
) -> str:
    """
    Inflect a profession/nationality lemma for grammatical gender.

    Args:
        lemma: Base lemma (usually masculine singular), e.g. 'attore', 'italiano'.
        gender: Target gender ('Male'/'Female'/variants).
        morphology_cfg:
            The 'morphology' section for this language, typically:

            {
              "suffixes": [
                { "ends_with": "tore", "replace_with": "trice" },
                { "ends_with": "o",    "replace_with": "a" }
              ],
              "irregulars": {
                "attore": "attrice"
              }
            }

    Returns:
        The inflected surface form (string).
    """
    norm_gender = _normalize_gender(gender)
    base = (lemma or "").strip()
    if not base:
        return base

    # If we are asked for masculine, we generally return the lemma as is.
    if norm_gender == "male":
        return base

    # Work in lowercase for rule matching.
    lower = base.lower()
    irregulars: Dict[str, str] = morphology_cfg.get("irregulars", {}) or {}

    # 1. Irregular dictionary lookup
    if lower in irregulars:
        candidate = irregulars[lower]
        return _preserve_capitalisation(base, candidate)

    # 2. Suffix rules (ordered, longest first for safety)
    suffixes = morphology_cfg.get("suffixes", []) or []
    # Be defensive: ignore malformed entries.
    valid_suffixes = [
        r for r in suffixes
        if isinstance(r, dict)
        and "ends_with" in r
        and "replace_with" in r
        and isinstance(r["ends_with"], str)
        and isinstance(r["replace_with"], str)
    ]
    # More specific endings should be tried first.
    valid_suffixes.sort(key=lambda r: len(r["ends_with"]), reverse=True)

    for rule in valid_suffixes:
        ending = rule["ends_with"]
        replacement = rule["replace_with"]

        if ending and lower.endswith(ending):
            stem = lower[: -len(ending)]
            candidate = stem + replacement
            return _preserve_capitalisation(base, candidate)

    # 3. Generic Romance fallback: -o → -a
    if lower.endswith("o"):
        candidate = lower[:-1] + "a"
        return _preserve_capitalisation(base, candidate)

    # 4. No applicable rule: return lemma unchanged
    return base


def select_indefinite_article(
    next_word: str,
    gender: str,
    articles_cfg: Dict[str, Any],
    phonetics_cfg: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Pick the correct indefinite article before `next_word`.

    This is where we handle:
      * Vowel-initial words (elision)
      * Italian "s-impure" / complex onset clusters
      * Spanish 'stressed-a' nouns (águila, agua, etc.)

    Args:
        next_word: The word that follows the article (already inflected).
        gender: Target gender ('Male'/'Female'/variants).
        articles_cfg:
            The 'articles' section for this language, e.g.:

            {
              "m": { "default": "un", "s_impure": "uno", "vowel": "un" },
              "f": { "default": "una", "vowel": "un'", "stressed_a": "un" }
            }

        phonetics_cfg:
            Optional 'phonetics' section, e.g.:

            {
              "impure_triggers": ["s_consonant", "z", "gn"],
              "stressed_a_words": ["águila", "agua"]
            }

    Returns:
        The indefinite article string (may be empty if not configured).
    """
    phonetics_cfg = phonetics_cfg or {}
    norm_gender = _normalize_gender(gender)

    word = (next_word or "").strip()
    if not word:
        # No following word; fall back to a bare default if possible.
        bucket = "m" if norm_gender == "male" else "f"
        rules = articles_cfg.get(bucket, {})
        return rules.get("default", "")

    gender_key = "m" if norm_gender == "male" else "f"
    rules: Dict[str, Any] = articles_cfg.get(gender_key, {}) or {}
    default_article: str = rules.get("default", "")

    if not rules:
        return ""

    # 1. Vowel-initial words (elision, l'/un', etc.)
    if word[0] in _ROMANCE_VOWELS:
        vowel_form = rules.get("vowel")
        if vowel_form:
            return vowel_form

    # 2. Impure / complex onsets (Italian specific)
    # Config example:
    # "impure_triggers": ["s_consonant", "z", "gn", "ps"]
    impure_triggers = phonetics_cfg.get("impure_triggers", []) or []
    if impure_triggers:
        is_s_consonant = (
            word.startswith("s")
            and len(word) > 1
            and word[1] not in _ROMANCE_VOWELS
        )

        # any other clusters like z-, gn-, ps-, etc.
        other_match = any(
            t != "s_consonant" and word.startswith(t)
            for t in impure_triggers
        )

        if (is_s_consonant and "s_consonant" in impure_triggers) or other_match:
            s_impure_form = rules.get("s_impure")
            if s_impure_form:
                return s_impure_form

    # 3. Spanish-style stressed-A nouns (águila, agua…)
    stressed_a_words = phonetics_cfg.get("stressed_a_words", []) or []
    # We compare in lowercase for robustness.
    if word.lower() in {w.lower() for w in stressed_a_words}:
        stressed_form = rules.get("stressed_a")
        if stressed_form:
            return stressed_form

    # 4. Default article
    return default_article


def apply_romance_morphology(
    prof_lemma: str,
    nat_lemma: str,
    gender: str,
    full_config: Dict[str, Any],
) -> Tuple[str, str, str, str]:
    """
    Convenience helper used by higher-level engines.

    Given a full Romance language config (data/romance/xx.json), inflect
    profession + nationality and select the correct indefinite article.

    Args:
        prof_lemma: Profession lemma (usually masculine sg).
        nat_lemma: Nationality lemma (usually masculine sg).
        gender: Target gender.
        full_config:
            The complete per-language config dictionary. At minimum it should
            define:

            {
              "articles": { ... },
              "morphology": { ... },
              "phonetics": { ... }   # optional
            }

    Returns:
        (article, profession_form, nationality_form, sep)

        * article: the indefinite article (may be '').
        * profession_form: inflected profession.
        * nationality_form: inflected nationality.
        * sep: either "" or " ", describing how article and profession
               should be concatenated (handles elision like "un'" vs "una ").
    """
    morph_cfg = full_config.get("morphology", {}) or {}
    articles_cfg = full_config.get("articles", {}) or {}
    phonetics_cfg = full_config.get("phonetics", {}) or {}

    # Normalise lemmas for rule lookup, but keep original for case recovery.
    prof_inflected = inflect_gendered_lemma(prof_lemma, gender, morph_cfg)
    nat_inflected = inflect_gendered_lemma(nat_lemma, gender, morph_cfg)

    article = select_indefinite_article(
        prof_inflected,
        gender,
        articles_cfg,
        phonetics_cfg=phonetics_cfg,
    )

    # If article ends with an apostrophe, we do not want a space afterwards.
    if article and article.endswith("'"):
        sep = ""
    else:
        # Default: single space between article and profession.
        sep = " "

    return article, prof_inflected, nat_inflected, sep

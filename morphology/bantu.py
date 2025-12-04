"""
BANTU MORPHOLOGY MODULE
-----------------------
Noun-class based morphology utilities for Bantu languages (e.g. Swahili).

This module is responsible ONLY for:
- Choosing the right noun/adjective prefixes for a given noun class.
- Applying simple vowel-harmony adjustments to those prefixes.
- Selecting a class-specific copula (if defined).

Sentence-level assembly (word order, punctuation, etc.) is handled elsewhere
by construction modules. This file is purely about *forms*, not full sentences.

It expects a JSON configuration shaped like data/bantu/sw.json in this repo. :contentReference[oaicite:0]{index=0}
"""

from typing import Dict


def get_default_human_class(config: Dict) -> str:
    """
    Return the default noun class to use for human singular subjects.

    Many Bantu languages use:
    - Class 1 for human singular (e.g. m- / mu-)
    - Class 2 for human plural (e.g. wa-)

    The config is expected to provide:
        config["syntax"]["default_human_class"]

    If missing, falls back to "1".
    """
    return (
        config.get("syntax", {}).get("default_human_class", "1")
    )


def _get_prefix_maps(morph_rules: Dict):
    """
    Internal helper to fetch noun and adjective prefix maps
    from the morphology section of the config.
    """
    prefixes = morph_rules.get("prefixes", {})
    adjective_prefixes = morph_rules.get("adjective_prefixes", prefixes)
    return prefixes, adjective_prefixes


def apply_class_prefix(
    word: str,
    target_class: str,
    config: Dict,
    word_type: str = "noun",
) -> str:
    """
    Attach the appropriate class prefix to a noun or adjective.

    Args:
        word:      Lemma or stem for the lexical item (e.g. 'walimu', 'zuri').
        target_class: Noun class identifier as a string (e.g. "1", "2", "9").
        config:    Language card dict (e.g. data/bantu/sw.json). :contentReference[oaicite:1]{index=1}
        word_type: Either 'noun' or 'adjective'. Adjectives can use a separate
                   concord prefix map if provided.

    Returns:
        The inflected form with the appropriate class prefix, e.g.:
            'alimu' + class-1 → 'mwalimu'
            'zuri'  + class-1 adjective → 'mzuri'
    """
    if not word:
        return word

    morph_rules = config.get("morphology", {})
    prefixes, adjective_prefixes = _get_prefix_maps(morph_rules)

    # 1. Class-specific base prefix
    target_prefix = prefixes.get(target_class, "")

    # 2. Whole-word irregular overrides
    irregulars = morph_rules.get("irregulars", {})
    if word in irregulars:
        return irregulars[word]

    # 3. Use adjective concord if requested
    if word_type == "adjective":
        target_prefix = adjective_prefixes.get(target_class, target_prefix)

    # NOTE ON STEMMING:
    # In a full system you would strip any existing dictionary prefix to get
    # the true stem (e.g. 'mwalimu' → 'alimu'). For this prototype we assume
    # that:
    # - Inputs are either stems or
    # - The irregular map handles common dictionary forms.
    # We therefore do *not* strip prefixes automatically.

    # 4. Vowel-based allomorphy for prefixes (simple harmony)
    #    e.g. Swahili: m- → mw- before vowel; wa- → w- before vowel.
    vowel_rules = morph_rules.get("vowel_harmony", {})
    if word and word[0].lower() in "aeiou" and target_prefix in vowel_rules:
        target_prefix = vowel_rules[target_prefix]

    return f"{target_prefix}{word}"


def inflect_noun_for_class(
    lemma: str,
    noun_class: str,
    config: Dict,
) -> str:
    """
    Convenience wrapper: inflect a noun lemma for a given noun class.

    Typically used for professions or other head nouns in bios.
    """
    lemma = lemma.strip()
    if not lemma:
        return lemma
    return apply_class_prefix(lemma, noun_class, config, word_type="noun")


def inflect_adjective_for_class(
    lemma: str,
    noun_class: str,
    config: Dict,
) -> str:
    """
    Convenience wrapper: inflect an adjective lemma for a given noun class.

    Typically used for nationalities or descriptive adjectives that must
    agree with a class-1 human subject, etc.
    """
    lemma = lemma.strip()
    if not lemma:
        return lemma
    return apply_class_prefix(lemma, noun_class, config, word_type="adjective")


def get_copula_for_class(
    noun_class: str,
    config: Dict,
) -> str:
    """
    Return a copular form agreeing with the given noun class, if available.

    The config is expected to define something like:

        "verbs": {
          "copula": {
            "default": "ni",
            "1": "yu",
            "2": "wa"
          }
        }

    For Swahili, for example, 'ni' is often invariant, but other Bantu
    languages may have class-specific copulas. :contentReference[oaicite:2]{index=2}
    """
    verbs = config.get("verbs", {})
    copula_map = verbs.get("copula", {})

    # Class-specific copula (if provided)
    if noun_class in copula_map:
        return copula_map[noun_class]

    # Invariant fallback
    return copula_map.get("default", "")


def get_human_singular_bundle(
    prof_lemma: str,
    nat_lemma: str,
    config: Dict,
) -> Dict[str, str]:
    """
    High-level helper: given profession & nationality lemmas,
    return their class-1 (human singular) forms plus the matching copula.

    This is a convenience for construction modules that want to say
    things like:
        {NAME} {COPULA} {PROF} {NAT}

    Returns a dict with keys:
        - 'class': noun class used (string, e.g. "1")
        - 'profession': inflected profession
        - 'nationality': inflected nationality
        - 'copula': class-agreeing copula (or default/invariant)
    """
    human_class = get_default_human_class(config)

    inflected_prof = inflect_noun_for_class(prof_lemma, human_class, config)
    inflected_nat = inflect_adjective_for_class(nat_lemma, human_class, config)
    copula = get_copula_for_class(human_class, config)

    return {
        "class": human_class,
        "profession": inflected_prof,
        "nationality": inflected_nat,
        "copula": copula,
    }

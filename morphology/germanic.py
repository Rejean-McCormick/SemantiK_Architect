"""
morphology/germanic.py

Morphology helpers for Germanic languages (DE, EN, NL, SV, DA, NO).

This module is intentionally **stateless**: all language-specific behavior
comes from the JSON configuration cards (e.g. data/germanic/de.json,
data/germanic/en.json).

It is responsible for:

- Profession gender inflection (masc → fem)
- Grammatical gender inference from word shape
- Adjective (nationality) agreement with noun gender
- Indefinite article selection (including English a/an)
- Optional noun capitalization (e.g. German)

Typical usage from a higher-level engine:

    from morphology import germanic as gmorph

    parts = gmorph.realize_predicate(
        prof_lemma="Lehrer",
        nat_lemma="deutsch",
        gender="female",
        config=de_config,
    )

    # parts == {
    #   "profession": "Lehrerin",
    #   "nationality": "deutsche",
    #   "article": "eine",
    #   "word_gender": "f"
    # }

The sentence assembler is *not* defined here; it belongs to a syntax/engine
module which decides on word order, copula, punctuation, etc.
"""

from typing import Any, Dict


def _get_lang_code(config: Dict[str, Any]) -> str:
    """
    Get a stable language code for conditional logic.

    Priority:
    1. config["code"] (if a router injected it)
    2. config["meta"]["language"] from the JSON card
    """
    code = config.get("code")
    if code:
        return str(code).lower()

    meta = config.get("meta", {})
    return str(meta.get("language", "")).lower()


def normalize_gender(gender: str) -> str:
    """
    Normalize a variety of gender labels into 'male' / 'female' / raw.
    """
    if not gender:
        return ""

    g = gender.strip().lower()
    if g in {"f", "female", "woman", "w"}:
        return "female"
    if g in {"m", "male", "man"}:
        return "male"
    return g


# ---------------------------------------------------------------------------
# 1. Profession Morphology (gender inflection)
# ---------------------------------------------------------------------------


def inflect_profession(prof_lemma: str, gender: str, config: Dict[str, Any]) -> str:
    """
    Inflect a profession lemma for natural gender (typically masc → fem).

    - Uses:
      - config["morphology"]["irregulars"]
      - config["morphology"]["gender_suffixes"]
      - config["morphology"]["generic_feminine_suffix"]

    The function does **not** handle capitalization; call `apply_noun_casing`
    afterwards if your language requires capitalized nouns (e.g. German).
    """
    gender = normalize_gender(gender)
    word = prof_lemma.strip()

    # Masculine: assume input lemma is already the correct form.
    if gender == "male":
        return word

    morph_rules = config.get("morphology", {})

    # 1) Irregulars (dictionary lookup, case-insensitive)
    irregulars = morph_rules.get("irregulars", {}) or {}
    lowered = word.lower()
    for base, fem in irregulars.items():
        if base.lower() == lowered:
            return fem

    # 2) Suffix rules (e.g. DE: Lehrer → Lehrerin)
    suffixes = morph_rules.get("gender_suffixes", []) or []
    # Apply longer endings first (e.g. "-erin" before "-in")
    suffixes_sorted = sorted(
        suffixes, key=lambda r: len(str(r.get("ends_with", ""))), reverse=True
    )

    for rule in suffixes_sorted:
        ending = str(rule.get("ends_with", ""))
        replacement = str(rule.get("replace_with", ""))

        if ending and word.endswith(ending):
            stem = word[: -len(ending)]
            return stem + replacement

    # 3) Generic feminine suffix (e.g. DE: Lehrer → Lehrerin)
    generic_suffix = morph_rules.get("generic_feminine_suffix", "")
    if generic_suffix:
        return word + str(generic_suffix)

    # 4) Fallback: return lemma unchanged
    return word


# ---------------------------------------------------------------------------
# 2. Grammatical gender inference
# ---------------------------------------------------------------------------


def infer_grammatical_gender(
    noun_form: str, natural_gender: str, config: Dict[str, Any]
) -> str:
    """
    Infer the grammatical gender (m/f/n/pl) of a noun form.

    Uses:

    - config["morphology"]["grammatical_gender_map"], mapping suffix → "m"/"f"/"n"/"pl"
    - Falls back to natural_gender:
        "male"   → "m"
        "female" → "f"
        other    → "n"
    """
    morph_rules = config.get("morphology", {}) or {}
    gram_map = morph_rules.get("grammatical_gender_map", {}) or {}

    word = noun_form.strip()

    # Check suffix-based map, longest suffix first for safety
    suffixes_sorted = sorted(
        gram_map.items(), key=lambda kv: len(str(kv[0])), reverse=True
    )
    for suffix, gram_gender in suffixes_sorted:
        suffix = str(suffix)
        if suffix and word.endswith(suffix):
            return str(gram_gender)

    # Fallback: approximate from natural gender
    nat = normalize_gender(natural_gender)
    if nat == "male":
        return "m"
    if nat == "female":
        return "f"
    return "n"


# ---------------------------------------------------------------------------
# 3. Adjective (nationality) inflection
# ---------------------------------------------------------------------------


def inflect_nationality(
    nat_lemma: str, noun_gender: str, config: Dict[str, Any]
) -> str:
    """
    Inflect a nationality adjective to agree with the noun's grammatical gender.

    Uses:

    - config["adjectives"]["inflects"] (bool)
    - config["adjectives"]["indefinite_endings"][gender]

    For languages without adjective inflection (e.g. English),
    this returns the lemma unchanged.
    """
    adj = nat_lemma.strip()
    adj_rules = config.get("adjectives", {}) or {}

    if not adj_rules.get("inflects", False):
        return adj

    endings = adj_rules.get("indefinite_endings", {}) or {}
    suffix = endings.get(noun_gender, "")
    return adj + str(suffix)


# ---------------------------------------------------------------------------
# 4. Article selection (indefinite)
# ---------------------------------------------------------------------------


def choose_indefinite_article(
    next_word: str, noun_gender: str, config: Dict[str, Any]
) -> str:
    """
    Choose an indefinite article for Germanic languages.

    - English: handles **a/an** using phonetic heuristics and the JSON card:
        - articles.indefinite.default
        - articles.indefinite.vowel_trigger
        - phonetics.vowels
    - Other Germanic languages (DE, NL, SV, DA, NO):
        - articles.indefinite is expected to be a dict keyed by
          grammatical gender ("m", "f", "n", "pl").

    Parameters
    ----------
    next_word:
        The word immediately following the article (usually the nationality
        adjective; if absent, use the noun itself).
    noun_gender:
        Grammatical gender code ("m", "f", "n", "pl").
    config:
        Language configuration card.
    """
    articles = config.get("articles", {}) or {}
    lang = _get_lang_code(config)
    word = next_word.strip()

    # English: a/an logic
    if lang == "en":
        ind = articles.get("indefinite", {}) or {}
        phon = config.get("phonetics", {}) or {}

        default = ind.get("default", "a")
        vowel_form = ind.get("vowel_trigger", "an")
        vowels = phon.get("vowels", "aeiouAEIOU")

        if not word:
            return default

        first_char = word[0]
        if first_char in vowels:
            return vowel_form
        return default

    # Generic Germanic: lookup by grammatical gender
    ind_map = articles.get("indefinite", {}) or {}
    if isinstance(ind_map, str):
        # Some JSONs may store a single string as "indefinite"
        return ind_map

    return ind_map.get(noun_gender, ind_map.get("default", ""))


# ---------------------------------------------------------------------------
# 5. Casing helpers
# ---------------------------------------------------------------------------


def apply_noun_casing(noun: str, config: Dict[str, Any]) -> str:
    """
    Apply language-specific casing to nouns.

    - For German, config["casing"]["capitalize_nouns"] is typically True.
    - For English and others, this is usually False and we return the noun
      unchanged (assuming the caller provided the desired casing).
    """
    casing = config.get("casing", {}) or {}
    if casing.get("capitalize_nouns", False) and noun:
        return noun[0].upper() + noun[1:]
    return noun


# ---------------------------------------------------------------------------
# 6. High-level convenience: realize full predicate
# ---------------------------------------------------------------------------


def realize_predicate(
    prof_lemma: str, nat_lemma: str, gender: str, config: Dict[str, Any]
) -> Dict[str, str]:
    """
    Convenience function that computes all predicate-level morphology
    for the canonical Wikipedia bio pattern:

        NAME  COPULA  ARTICLE  NATIONALITY  PROFESSION

    It returns a dict with:

        {
            "profession":  <inflected profession, with correct casing>,
            "nationality": <inflected nationality adjective>,
            "article":     <indefinite article string or "">,
            "word_gender": <grammatical gender of the profession word>
        }

    The caller (engine/syntax layer) is responsible for inserting these
    pieces into a sentence template and adding the copula, punctuation, etc.
    """
    gender_norm = normalize_gender(gender)

    # 1. Profession (lexeme) → gendered form
    prof_inflected = inflect_profession(prof_lemma, gender_norm, config)

    # 2. Grammatical gender of the profession word
    gram_gender = infer_grammatical_gender(prof_inflected, gender_norm, config)

    # 3. Nationality adjective agreement (if applicable)
    nat_inflected = inflect_nationality(nat_lemma, gram_gender, config)

    # 4. Article: normally looks at the word immediately after the article.
    # In patterns like "X is a [NATIONALITY] [PROFESSION]", the article precedes
    # the nationality, so we use nationality if present, else the profession.
    article_target = nat_inflected or prof_inflected
    article = choose_indefinite_article(article_target, gram_gender, config)

    # 5. Apply noun casing (e.g. German capitalization)
    prof_final = apply_noun_casing(prof_inflected, config)

    return {
        "profession": prof_final,
        "nationality": nat_inflected,
        "article": article,
        "word_gender": gram_gender,
    }

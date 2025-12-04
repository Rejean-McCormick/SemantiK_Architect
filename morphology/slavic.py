"""
Slavic morphology helpers.

This module provides data-driven utilities for Slavic languages (RU, PL, CS, UK, SR, HR, BG),
based on per-language JSON configuration files under data/slavic/*.json. :contentReference[oaicite:0]{index=0}

It does NOT decide sentence order or construction choice; it only:
- derives feminine forms from masculine lemmas (nouns/adjectives),
- declines words into grammatical cases (e.g. Instrumental),
- selects gendered past-tense copula forms.

The goal is to be reusable from any construction layer.
"""

from typing import Dict, Any


Config = Dict[str, Any]


# ---------------------------------------------------------------------------
# Gender derivation (feminization)
# ---------------------------------------------------------------------------

def _apply_suffix_rules(word: str, rules: Any) -> str:
    """
    Apply the first matching suffix replacement rule to `word`.

    Rules are expected to be a list of dicts:
    [{ "ends_with": "...", "replace_with": "..." }, ...]
    """
    if not isinstance(rules, list):
        return word

    # Match longer endings first to avoid "tel" vs "el" type conflicts
    sorted_rules = sorted(
        rules,
        key=lambda r: len(r.get("ends_with", "")),
        reverse=True,
    )

    for rule in sorted_rules:
        end = rule.get("ends_with", "")
        repl = rule.get("replace_with", "")
        if end and word.endswith(end):
            stem = word[:-len(end)]
            return stem + repl

    return word


def genderize_noun(lemma: str, gender: str, config: Config) -> str:
    """
    Return the nominative form of a profession/role noun for the given natural gender.

    - If gender is 'male', returns lemma unchanged.
    - If gender is 'female', first check irregulars, then apply gender_inflection.noun_suffixes.
    """
    lemma = (lemma or "").strip()
    gender = (gender or "").lower().strip()

    if gender != "female":
        return lemma

    morph = config.get("morphology", {})
    irregulars = morph.get("irregulars", {})

    if lemma in irregulars:
        return irregulars[lemma]

    noun_rules = morph.get("gender_inflection", {}).get("noun_suffixes", [])
    return _apply_suffix_rules(lemma, noun_rules)


def genderize_adjective(lemma: str, gender: str, config: Config) -> str:
    """
    Return the nominative form of a nationality adjective for the given natural gender.

    - If gender is 'male', returns lemma unchanged.
    - If gender is 'female', first check irregulars, then apply gender_inflection.adjective_suffixes.
    """
    lemma = (lemma or "").strip()
    gender = (gender or "").lower().strip()

    if gender != "female":
        return lemma

    morph = config.get("morphology", {})
    irregulars = morph.get("irregulars", {})

    if lemma in irregulars:
        return irregulars[lemma]

    adj_rules = morph.get("gender_inflection", {}).get("adjective_suffixes", [])
    return _apply_suffix_rules(lemma, adj_rules)


# ---------------------------------------------------------------------------
# Case declension
# ---------------------------------------------------------------------------

def decline_case(word: str, case: str, gender: str, config: Config) -> str:
    """
    Decline `word` into the requested case, using simple suffix replacement rules.

    - `case` is a string like 'nominative', 'instrumental', etc.
    - `gender` is reduced to 'm' or 'f' for rule lookup.

    If no rules are found, returns the word unchanged.
    """
    word = (word or "").strip()
    case = (case or "").lower().strip()
    if not word or not case:
        return word

    if case == "nominative":
        return word

    morph = config.get("morphology", {})
    cases = morph.get("cases", {})

    # Map natural gender -> simple grammatical key
    gram_gender = "f" if gender and gender.lower().startswith("f") else "m"
    rules = cases.get(case, {}).get(gram_gender, [])

    return _apply_suffix_rules(word, rules)


def decline_noun(word: str, case: str, gender: str, config: Config) -> str:
    """
    Convenience wrapper for declining a noun.

    Currently identical to decline_case, but separated for clarity / future extension.
    """
    return decline_case(word, case, gender, config)


def decline_adjective(word: str, case: str, gender: str, config: Config) -> str:
    """
    Convenience wrapper for declining an adjective.

    Some Slavic languages may use different rule sets for nouns vs adjectives;
    this function allows for that future specialization while currently delegating
    to decline_case.
    """
    return decline_case(word, case, gender, config)


# ---------------------------------------------------------------------------
# Copula (past tense) selection
# ---------------------------------------------------------------------------

def select_past_copula(gender: str, number: str, config: Config) -> str:
    """
    Select the correct past-tense copula ('was') form for the subject.

    Config is expected to have:
    config['verbs']['copula'] with keys like:
      - 'male', 'female', 'neuter', 'plural'
      - 'default'

    `gender` is natural gender ('male', 'female', 'other', etc.)
    `number` is 'sg' or 'pl'.

    Returns an empty string if the language prefers a zero copula.
    """
    verbs = config.get("verbs", {})
    copula_map = verbs.get("copula", {}) or {}

    gender = (gender or "").lower().strip()
    number = (number or "").lower().strip()

    if number.startswith("pl"):
        return copula_map.get("plural", copula_map.get("default", ""))

    if gender.startswith("f"):
        return copula_map.get("female", copula_map.get("default", ""))
    if gender.startswith("m"):
        return copula_map.get("male", copula_map.get("default", ""))

    # Fallback to a generic neuter/default
    return copula_map.get("neuter", copula_map.get("default", ""))


# ---------------------------------------------------------------------------
# High-level helper for a typical biographical predicate
# ---------------------------------------------------------------------------

def inflect_bio_predicate(
    prof_lemma: str,
    nat_lemma: str,
    gender: str,
    config: Config,
) -> Dict[str, str]:
    """
    Convenience function for biographical sentences:

    1. Derive gendered nominative forms for:
       - profession (noun)
       - nationality (usually adjective)
    2. Decline them into the language's configured predicative case
       (e.g., Instrumental in Russian).
    3. Select an appropriate past copula form.

    Returns:
        {
          "profession": <inflected_profession>,
          "nationality": <inflected_nationality>,
          "copula": <past_copula_or_empty>,
          "case": <case_used>
        }
    """
    gender_norm = (gender or "").lower().strip()
    syntax = config.get("syntax", {})
    pred_case = syntax.get("predicative_case", "nominative")

    # 1. Nominative forms by gender
    prof_nom = genderize_noun(prof_lemma, gender_norm, config)
    nat_nom = genderize_adjective(nat_lemma, gender_norm, config)

    # 2. Decline into target case
    prof_inf = decline_noun(prof_nom, pred_case, gender_norm, config)
    nat_inf = decline_adjective(nat_nom, pred_case, gender_norm, config)

    # 3. Copula (assume singular for simple bios)
    copula = select_past_copula(gender_norm, "sg", config)

    return {
        "profession": prof_inf,
        "nationality": nat_inf,
        "copula": copula,
        "case": pred_case,
    }

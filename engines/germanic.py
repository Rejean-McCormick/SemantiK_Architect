"""
GERMANIC LANGUAGE ENGINE
------------------------
A data-driven renderer for Germanic languages (EN, DE, NL, SV, DA, NO).

This module orchestrates the generation of sentences by:
1. Delegating morphology to `morphology.germanic.GermanicMorphology`.
2. Handling sentence structure and assembly.
"""

from morphology.germanic import GermanicMorphology


def render_bio(name, gender, prof_lemma, nat_lemma, config):
    """
    Main Entry Point for Germanic Biographies.

    Args:
        name (str): The subject's name.
        gender (str): 'Male' or 'Female'.
        prof_lemma (str): The profession (e.g., "Lehrer" / "Teacher").
        nat_lemma (str): The nationality adjective (e.g., "Deutsch" / "German").
        config (dict): The JSON configuration card.

    Returns:
        str: The fully inflected sentence.
    """
    # 1. Initialize Morphology Engine
    morph = GermanicMorphology(config)

    # 2. Get Predicate Components (Profession, Nationality, Article)
    # This handles gender inflection, adjective declension, and article selection
    # returning a dict: {"profession": ..., "nationality": ..., "article": ...}
    parts = morph.render_simple_bio_predicates(prof_lemma, nat_lemma, gender)

    # 3. Get Verb (Copula)
    # Default to past tense for bios ("was"), unless syntax config says otherwise.
    bio_tense = config.get("syntax", {}).get("bio_default_tense", "past")

    # We request the verb "be". The morphology engine handles mapping this
    # to the specific language's copula config (e.g. 'war', 'is', 'var').
    copula = morph.realize_verb("be", {"tense": bio_tense, "number": "sg", "person": "3"})

    # 4. Assembly
    structure = config.get(
        "structure",
        "{name} {copula} {article} {nationality} {profession}."
    )

    sentence = structure.replace("{name}", name)
    # Support both {copula} (standard) and {is_verb} (legacy config) placeholders
    sentence = sentence.replace("{copula}", copula)
    sentence = sentence.replace("{is_verb}", copula)

    sentence = sentence.replace("{article}", parts["article"])
    sentence = sentence.replace("{nationality}", parts["nationality"])
    sentence = sentence.replace("{profession}", parts["profession"])

    # Cleanup extra spaces (e.g. if article is empty)
    sentence = " ".join(sentence.split())

    return sentence
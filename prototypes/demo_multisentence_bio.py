"""
prototypes/demo_multisentence_bio.py

Small, self-contained demo script that shows how to build *multi-sentence*
biographies on top of the core `render_bio(...)` entrypoint.

It does NOT introduce new core logic; instead it:

- Uses `router.render_bio(...)` for the first, definitional sentence
  ("X is a Polish physicist.").
- Adds 1–2 FOLLOW-UP sentences per person using language-specific templates
  and simple pronoun selection.

This is meant as a human-readable demo you can run in a notebook or from
the CLI to show “multi-sentence output across languages”, not as a
production discourse module.

Usage (from project root):

    python prototypes/demo_multisentence_bio.py
    python prototypes/demo_multisentence_bio.py --langs fr,it
    python prototypes/demo_multisentence_bio.py --langs fr,it,es,en

You can extend:

- The `SAMPLE_BIOS` list with more people.
- The `FACT_TEMPLATES` and `PRONOUN_SUBJECT` dictionaries with more
  languages and content.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    # Main single-sentence entrypoint
    from router import render_bio  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - defensive
    render_bio = None


# ---------------------------------------------------------------------------
# Data model for this demo
# ---------------------------------------------------------------------------


@dataclass
class PersonBio:
    name: str
    gender: str  # "female" / "male"
    profession_lemma: str
    nationality_lemma: str
    fact_ids: List[str] = field(default_factory=list)


SAMPLE_BIOS: List[PersonBio] = [
    PersonBio(
        name="Marie Curie",
        gender="female",
        profession_lemma="physicist",
        nationality_lemma="polish",
        fact_ids=["curie_radioactivity", "curie_two_nobels"],
    ),
    PersonBio(
        name="Albert Einstein",
        gender="male",
        profession_lemma="physicist",
        nationality_lemma="german",
        fact_ids=["einstein_relativity"],
    ),
    PersonBio(
        name="Katherine Johnson",
        gender="female",
        profession_lemma="mathematician",
        nationality_lemma="american",
        fact_ids=["johnson_nasa"],
    ),
]

# ---------------------------------------------------------------------------
# Very small language-specific layer for follow-up sentences
# ---------------------------------------------------------------------------

# Subject pronouns (3rd person singular) by language and gender
PRONOUN_SUBJECT: Dict[str, Dict[str, str]] = {
    "en": {"female": "She", "male": "He"},
    "fr": {"female": "Elle", "male": "Il"},
    "it": {"female": "Lei", "male": "Lui"},
    "es": {"female": "Ella", "male": "Él"},
    # Fallback-friendly: if a lang is missing, we use the name instead
}

# Simple per-fact, per-language templates.
# All templates accept:
#   {pronoun} – already capitalized (e.g. "She", "Elle")
#   {name}    – full name (e.g. "Marie Curie")
FACT_TEMPLATES: Dict[str, Dict[str, str]] = {
    "curie_radioactivity": {
        "en": "{pronoun} pioneered research on radioactivity.",
        "fr": "{pronoun} a mené des recherches pionnières sur la radioactivité.",
        "it": "{pronoun} ha svolto ricerche pionieristiche sulla radioattività.",
        "es": "{pronoun} realizó investigaciones pioneras sobre la radiactividad.",
    },
    "curie_two_nobels": {
        "en": "{pronoun} received two Nobel Prizes.",
        "fr": "{pronoun} a reçu deux prix Nobel.",
        "it": "{pronoun} ha ricevuto due premi Nobel.",
        "es": "{pronoun} recibió dos premios Nobel.",
    },
    "einstein_relativity": {
        "en": "{pronoun} is best known for the theory of relativity.",
        "fr": "{pronoun} est surtout connu pour la théorie de la relativité.",
        "it": "{pronoun} è soprattutto conosciuto per la teoria della relatività.",
        "es": "{pronoun} es conocido sobre todo por la teoría de la relatividad.",
    },
    "johnson_nasa": {
        "en": "{pronoun} calculated critical flight trajectories for NASA.",
        "fr": "{pronoun} a calculé des trajectoires de vol cruciales pour la NASA.",
        "it": "{pronoun} ha calcolato traiettorie di volo cruciali per la NASA.",
        "es": "{pronoun} calculó trayectorias de vuelo cruciales para la NASA.",
    },
}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_followup_sentences(person: PersonBio, lang_code: str) -> List[str]:
    """
    Render 1–2 follow-up sentences for a person in a given language.

    If no templates or pronouns are available for that language, this falls
    back to empty list (only the first definitional sentence will be shown).
    """
    facts_for_lang = []
    pron_map = PRONOUN_SUBJECT.get(lang_code)

    if pron_map is None:
        # No pronoun mapping → stick to just the first sentence
        return facts_for_lang

    pronoun = pron_map.get(person.gender.lower())
    if not pronoun:
        # Again, better to omit than hallucinate
        return facts_for_lang

    for fact_id in person.fact_ids:
        templ_for_lang = FACT_TEMPLATES.get(fact_id, {}).get(lang_code)
        if templ_for_lang:
            facts_for_lang.append(
                templ_for_lang.format(pronoun=pronoun, name=person.name)
            )

    return facts_for_lang


def render_multisentence_bio(person: PersonBio, lang_code: str) -> List[str]:
    """
    Return a list of sentences (strings) for a given person and language.

    Sentence 1: uses the core router.render_bio(...) implementation.
    Sentence 2+: use lightweight templates with pronouns.
    """
    if render_bio is None:
        raise RuntimeError(
            "router.render_bio could not be imported. "
            "Make sure you're running from the project root and that "
            "`router.py` is available."
        )

    # First, the definitional sentence (goes through the full engine).
    first = render_bio(
        name=person.name,
        gender=person.gender,
        profession_lemma=person.profession_lemma,
        nationality_lemma=person.nationality_lemma,
        lang_code=lang_code,
    )

    # Then, follow-up sentences (simple language-specific templates).
    rest = render_followup_sentences(person, lang_code)

    # Filter out empties / None just in case
    sentences = [s for s in [first, *rest] if s]
    return sentences


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Demo: multi-sentence biographies across languages, "
            "using router.render_bio for the first sentence."
        )
    )
    parser.add_argument(
        "--langs",
        type=str,
        default="fr,it,es,en",
        help=("Comma-separated language codes to render. " "Default: fr,it,es,en"),
    )
    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    langs = [code.strip() for code in args.langs.split(",") if code.strip()]

    print("=== Multi-sentence biography demo ===\n")

    for person in SAMPLE_BIOS:
        print(f"Person: {person.name}  (gender={person.gender})")
        for lang in langs:
            try:
                sentences = render_multisentence_bio(person, lang)
            except Exception as e:
                print(f"  [{lang}] ERROR: {e}")
                continue

            if not sentences:
                print(f"  [{lang}] (no output)")
                continue

            print(f"  [{lang}]")
            for i, sent in enumerate(sentences, start=1):
                print(f"    {i:02d}. {sent}")
        print("")

    print("Done.")


if __name__ == "__main__":
    main()

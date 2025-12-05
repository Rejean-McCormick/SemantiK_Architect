"""
qa/test_lexicon_index.py

Basic unit tests for the lexicon.index module.

These tests intentionally construct tiny Lexicon instances in-memory,
without touching any JSON files. The goal is to verify that the index
layer:

- indexes professions and nationalities by both key and lemma
- is case-insensitive wrt lookup
- gracefully returns None for missing lemmas
"""

from __future__ import annotations

from lexicon.types import (
    Lexicon,
    LexiconMeta,
    ProfessionEntry,
    NationalityEntry,
    BaseLexicalEntry,
)
from lexicon.index import LexiconIndex


def make_minimal_lexicon_it() -> Lexicon:
    """
    Construct a tiny Italian lexicon for testing.
    """
    meta = LexiconMeta(language="it", family="romance", version="0.1.0")

    phys = ProfessionEntry(
        key="fisico",
        lemma="fisico",
        pos="NOUN",
        language="it",
        sense="profession",
        human=True,
        gender="m",
        default_number="sg",
        forms={"m.sg": "fisico", "f.sg": "fisica"},
    )

    writer = ProfessionEntry(
        key="scrittore",
        lemma="scrittore",
        pos="NOUN",
        language="it",
        sense="profession",
        human=True,
        gender="m",
        default_number="sg",
        forms={"m.sg": "scrittore", "f.sg": "scrittrice"},
    )

    italian = NationalityEntry(
        key="italiano",
        lemma="italiano",
        pos="ADJ",
        language="it",
        sense="nationality",
        human=None,
        gender="m",
        default_number="sg",
        forms={
            "m.sg": "italiano",
            "f.sg": "italiana",
            "m.pl": "italiani",
            "f.pl": "italiane",
        },
        adjective="italiano",
        demonym="italiano",
        country_name="Italia",
    )

    generic_noun = BaseLexicalEntry(
        key="scienziato",
        lemma="scienziato",
        pos="NOUN",
        language="it",
        sense="common_noun",
        human=True,
        gender="m",
        default_number="sg",
        forms={"sg": "scienziato", "pl": "scienziati"},
    )

    return Lexicon(
        meta=meta,
        professions={
            phys.key: phys,
            writer.key: writer,
        },
        nationalities={
            italian.key: italian,
        },
        titles={},
        honours={},
        general_entries={generic_noun.key: generic_noun},
        name_templates={},
    )


def test_profession_lookup_by_lemma_and_key() -> None:
    lex = make_minimal_lexicon_it()
    index = LexiconIndex(lex)

    # By lemma (exact)
    phys = index.lookup_profession("fisico")
    assert phys is not None
    assert phys.lemma == "fisico"
    assert phys.key == "fisico"

    # By lemma (case-insensitive)
    phys2 = index.lookup_profession("FISICO")
    assert phys2 is phys

    # By key (here same as lemma, but index should handle both)
    phys3 = index.lookup_profession("fisico")
    assert phys3 is phys

    # Another profession
    writer = index.lookup_profession("scrittore")
    assert writer is not None
    assert writer.key == "scrittore"
    assert writer.lemma == "scrittore"


def test_nationality_lookup() -> None:
    lex = make_minimal_lexicon_it()
    index = LexiconIndex(lex)

    nat = index.lookup_nationality("italiano")
    assert nat is not None
    assert nat.adjective == "italiano"
    assert nat.country_name == "Italia"

    # Case-insensitive
    nat2 = index.lookup_nationality("ITALIANO")
    assert nat2 is nat

    # Should also allow lookup by key or demonym if the index supports it
    nat3 = index.lookup_nationality("italiano")
    assert nat3 is nat


def test_lookup_any_falls_back_to_general_entries() -> None:
    lex = make_minimal_lexicon_it()
    index = LexiconIndex(lex)

    # Profession via lookup_any
    p = index.lookup_any("fisico")
    assert p is not None
    assert isinstance(p, BaseLexicalEntry)
    assert p.lemma == "fisico"

    # General entry via lookup_any
    g = index.lookup_any("scienziato")
    assert g is not None
    assert g.key == "scienziato"
    assert g.pos == "NOUN"


def test_missing_lemma_returns_none_instead_of_crashing() -> None:
    lex = make_minimal_lexicon_it()
    index = LexiconIndex(lex)

    assert index.lookup_profession("nonexistent") is None
    assert index.lookup_nationality("nonexistent") is None
    assert index.lookup_any("nonexistent") is None

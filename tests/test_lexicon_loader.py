# tests/test_lexicon_loader.py
"""
test/test_lexicon_loader.py
-------------------------

Basic smoke tests for the lexicon loader.

These tests assume that:

- Lexicon JSON files live under:  data/lexicon/
- Files follow the schema:

    {
      "_meta": { ... },
      "lemmas": {
        "lemma_string": { ... entry ... },
        ...
      }
    }

- `lexicon.loader.load_lexicon(lang)` returns a Lexicon object.

The tests are deliberately simple and do NOT depend on any particular
indexing implementation. They just verify that:

- Known languages ("fr", "pt", "ru") can be loaded.
- A few key lemmas exist and have expected POS / feature flags.
- An unknown language raises an appropriate error.
"""

from __future__ import annotations

import os

import pytest

# [FIX] Use full application paths for imports
from app.adapters.persistence.lexicon.config import LexiconConfig, set_config
from app.adapters.persistence.lexicon.loader import load_lexicon
from app.adapters.persistence.lexicon.types import Lexicon

# Project root: one level above tests/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEXICON_DIR = os.path.join(PROJECT_ROOT, "data", "lexicon")


@pytest.fixture(autouse=True)
def _configure_lexicon_dir() -> None:
    """
    Automatically point the lexicon subsystem at the real data/lexicon
    directory for all tests in this module.
    """
    cfg = LexiconConfig(lexicon_dir=LEXICON_DIR)
    set_config(cfg)


def test_load_lexicon_fr_basic() -> None:
    """French lexicon should load and contain key biography lemmas."""
    # Ensure dir exists before trying to load (avoids test failure on clean clone)
    if not os.path.exists(os.path.join(LEXICON_DIR, "fr")):
         pytest.skip("French lexicon data not present")

    lex = load_lexicon("fr")
    assert isinstance(lex, Lexicon)
    
    # Check professions map
    assert "physicienne" in lex.professions
    phys = lex.professions["physicienne"]
    assert phys.pos == "NOUN"
    assert phys.human is True
    assert phys.gender == "f"

    # Check nationalities map
    assert "polonais" in lex.nationalities
    pol = lex.nationalities["polonais"]
    assert pol.pos == "ADJ"
    # NationalityEntry usually implies nationality=True implicitly via class type


def test_load_lexicon_pt_basic() -> None:
    """Portuguese lexicon should load and contain professions and nationalities."""
    if not os.path.exists(os.path.join(LEXICON_DIR, "pt")):
         pytest.skip("Portuguese lexicon data not present")

    lex = load_lexicon("pt")
    assert isinstance(lex, Lexicon)

    assert "física" in lex.professions
    fis = lex.professions["física"]
    assert fis.pos == "NOUN"
    assert fis.human is True
    assert fis.gender == "f"

    assert "polonês" in lex.nationalities
    pol = lex.nationalities["polonês"]
    assert pol.pos == "ADJ"


def test_load_lexicon_ru_basic() -> None:
    """Russian lexicon should load and contain professions and nationality adjectives."""
    if not os.path.exists(os.path.join(LEXICON_DIR, "ru")):
         pytest.skip("Russian lexicon data not present")

    lex = load_lexicon("ru")
    assert isinstance(lex, Lexicon)

    assert "физик" in lex.professions
    fiz = lex.professions["физик"]
    assert fiz.pos == "NOUN"
    assert fiz.human is True

    assert "польский" in lex.nationalities
    pol = lex.nationalities["польский"]
    assert pol.pos == "ADJ"


def test_load_lexicon_unknown_language_raises() -> None:
    """
    Loading a lexicon for an unknown language should raise a FileNotFoundError
    (or a subclass). This shapes the expected API for callers.
    """
    with pytest.raises(FileNotFoundError):
        load_lexicon("xx")
"""
qa/test_lexicon_loader.py
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

- `lexicon.loader.load_lexicon(lang)` returns a mapping:
    lemma -> entry-dict

The tests are deliberately simple and do NOT depend on any particular
indexing or dataclass implementation. They just verify that:

- Known languages ("fr", "pt", "ru") can be loaded.
- A few key lemmas exist and have expected POS / feature flags.
- An unknown language raises an appropriate error.
"""

from __future__ import annotations

import os
import pytest

# Project root: one level above qa/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEXICON_DIR = os.path.join(PROJECT_ROOT, "data", "lexicon")


# Import config + loader from the lexicon package.
# These modules are expected to exist in the project.
from lexicon.config import LexiconConfig, set_config  # type: ignore[import-not-found]
from lexicon.loader import load_lexicon  # type: ignore[import-not-found]


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
    lemmas = load_lexicon("fr")
    assert isinstance(lemmas, dict)
    assert len(lemmas) > 0

    # Check a few key lemmas we defined in data/lexicon/fr_lexicon.json
    assert "physicienne" in lemmas
    assert "polonais" in lemmas

    phys = lemmas["physicienne"]
    assert phys.get("pos") == "NOUN"
    assert phys.get("human") is True
    assert phys.get("gender") == "f"

    pol = lemmas["polonais"]
    assert pol.get("pos") == "ADJ"
    assert pol.get("nationality") is True


def test_load_lexicon_pt_basic() -> None:
    """Portuguese lexicon should load and contain professions and nationalities."""
    lemmas = load_lexicon("pt")
    assert isinstance(lemmas, dict)
    assert len(lemmas) > 0

    assert "física" in lemmas
    assert "polonês" in lemmas

    fis = lemmas["física"]
    assert fis.get("pos") == "NOUN"
    assert fis.get("human") is True
    assert fis.get("gender") == "f"

    pol = lemmas["polonês"]
    assert pol.get("pos") == "ADJ"
    assert pol.get("nationality") is True


def test_load_lexicon_ru_basic() -> None:
    """Russian lexicon should load and contain professions and nationality adjectives."""
    lemmas = load_lexicon("ru")
    assert isinstance(lemmas, dict)
    assert len(lemmas) > 0

    assert "физик" in lemmas
    assert "польский" in lemmas

    fiz = lemmas["физик"]
    assert fiz.get("pos") == "NOUN"
    assert fiz.get("human") is True

    pol = lemmas["польский"]
    assert pol.get("pos") == "ADJ"
    assert pol.get("nationality") is True


def test_load_lexicon_unknown_language_raises() -> None:
    """
    Loading a lexicon for an unknown language should raise a FileNotFoundError
    (or a subclass). This shapes the expected API for callers.
    """
    with pytest.raises(FileNotFoundError):
        load_lexicon("xx")

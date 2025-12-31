# app/adapters/persistence/lexicon/normalization.py
# lexicon/normalization.py
"""
lexicon.normalization
=====================

Utility functions to normalize lemma strings and keys so that different
lexicon files (en/fr/sw/ja/…) can share a common lookup strategy.

Design goals
------------
- Tolerant of user input: capitalization, extra spaces, punctuation variants.
- Stable canonical form usable as a dictionary key.
- Unicode-safe and script-agnostic (Latin, Cyrillic, CJK, Arabic, …).
- Deterministic and testable normalization pipeline.
- Optional "aggressive" matching helpers for callers (explicit opt-in).
- Optional collision reporting for index-building.

Typical usage
-------------
>>> from lexicon.normalization import normalize_for_lookup
>>> normalize_for_lookup("  Nobel   Prize – in Physics ")
'nobel prize - in physics'
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

__all__ = [
    "normalize_whitespace",
    "standardize_punctuation",
    "strip_diacritics",
    "normalize_for_lookup",
    "build_normalized_index",
    "build_normalized_index_with_collisions",
    "NormalizationOptions",
]

# ---------------------------------------------------------------------------
# Core primitives
# ---------------------------------------------------------------------------

# Matches any run of Unicode whitespace characters.
_WHITESPACE_RE = re.compile(r"\s+")

# A small, conservative set of character replacements to reduce
# common Unicode punctuation variants to stable ASCII equivalents.
_CHAR_TRANSLATION_TABLE = str.maketrans(
    {
        # Apostrophes / quotes
        "’": "'",
        "‘": "'",
        "‛": "'",
        "‚": ",",
        "“": '"',
        "”": '"',
        "„": '"',
        "′": "'",
        "″": '"',
        # Dashes / hyphens
        "–": "-",
        "—": "-",
        "‒": "-",
        "‐": "-",
        "﹘": "-",
        "－": "-",
        # Full-width space and NBSP (often appear in copy/paste)
        "\u3000": " ",
        "\u00A0": " ",
    }
)

# Zero-width and copy/paste control characters that create invisible mismatches.
# We strip these deterministically.
_STRIP_CODEPOINTS = {
    "\u200B",  # ZERO WIDTH SPACE
    "\u200C",  # ZERO WIDTH NON-JOINER
    "\u200D",  # ZERO WIDTH JOINER
    "\u2060",  # WORD JOINER
    "\uFEFF",  # ZERO WIDTH NO-BREAK SPACE (BOM)
}


def _strip_invisible_controls(text: str) -> str:
    if not text:
        return text
    # Fast-path removals for common culprits
    for ch in _STRIP_CODEPOINTS:
        if ch in text:
            text = text.replace(ch, "")
    # Remove remaining Unicode "format" category characters (Cf).
    # Deterministic and generally safe for identifiers/labels.
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cf")


# ---------------------------------------------------------------------------
# Public primitives
# ---------------------------------------------------------------------------


def normalize_whitespace(text: str) -> str:
    """
    Collapse and trim whitespace in a Unicode-safe way.

    Steps:
      * Unicode NFKC normalization for consistency.
      * Collapse all whitespace runs to a single ASCII space.
      * Strip leading and trailing spaces.

    Args:
        text: Raw input string.

    Returns:
        A string with normalized spaces. Empty string for non-strings.
    """
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def standardize_punctuation(text: str) -> str:
    """
    Map common Unicode punctuation variants to simple ASCII forms.

    Also strips a small set of invisible control characters that can
    lead to hard-to-debug lookup misses.

    Args:
        text: Input string.

    Returns:
        String with punctuation standardized. Empty string for non-strings.
    """
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = _strip_invisible_controls(text)
    return text.translate(_CHAR_TRANSLATION_TABLE)


def strip_diacritics(text: str) -> str:
    """
    Strip combining diacritics while preserving base characters.

    Example:
        'éàï' -> 'eai'

    Not used by default in normalize_for_lookup() because diacritics can be
    semantically important. Callers must opt-in explicitly.

    Args:
        text: Input string.

    Returns:
        A string with combining marks removed. Empty string for non-strings.
    """
    if not isinstance(text, str):
        return ""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", stripped)


# ---------------------------------------------------------------------------
# Options and public high-level normalizer
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NormalizationOptions:
    """
    Options controlling normalization aggressiveness.

    Defaults preserve the historic behavior:
      - punctuation standardized
      - underscores treated as spaces
      - whitespace collapsed
      - casefold applied
      - invisibles stripped
      - diacritics NOT stripped (opt-in)
    """

    casefold: bool = True
    underscores_to_spaces: bool = True
    standardize_punct: bool = True
    normalize_ws: bool = True
    strip_invisibles: bool = True

    # Off by default: callers must opt-in explicitly.
    strip_marks: bool = False


def normalize_for_lookup(
    text: str,
    *,
    options: Optional[NormalizationOptions] = None,
) -> str:
    """
    Normalize a lemma / label string into a canonical lookup key.

    Intended for:
      * keys stored in lexicon JSON files
      * user/upstream input used to query those lexica

    Default pipeline (backward-compatible):
      1. Unicode NFKC normalization.
      2. Strip invisible control characters (copy/paste artifacts).
      3. Standardize punctuation (curly quotes, dashes, NBSP, …).
      4. Treat underscores as spaces.
      5. Normalize whitespace (collapse to single spaces, strip edges).
      6. Case-fold (robust lowercasing).

    Optional (opt-in):
      - strip diacritics/combining marks (options.strip_marks=True)

    Args:
        text: Raw lemma or label.
        options: Optional NormalizationOptions.

    Returns:
        Canonical lookup key. Empty string if input is not a string
        or reduces to nothing.
    """
    if not isinstance(text, str):
        return ""

    opts = options or NormalizationOptions()

    # 1. Unicode normalization base.
    norm = unicodedata.normalize("NFKC", text)

    # 2. Strip invisibles (independent switch).
    if opts.strip_invisibles:
        norm = _strip_invisible_controls(norm)

    # 3. Punctuation standardization.
    if opts.standardize_punct:
        norm = norm.translate(_CHAR_TRANSLATION_TABLE)

    # 4. Underscore harmonization.
    if opts.underscores_to_spaces:
        norm = norm.replace("_", " ")

    # 5. Whitespace normalization.
    if opts.normalize_ws:
        norm = _WHITESPACE_RE.sub(" ", norm).strip()
    else:
        norm = norm.strip()

    if not norm:
        return ""

    # 6. Optional diacritic stripping (aggressive).
    if opts.strip_marks:
        norm = strip_diacritics(norm)
        if opts.normalize_ws:
            norm = _WHITESPACE_RE.sub(" ", norm).strip()
        else:
            norm = norm.strip()
        if not norm:
            return ""

    # 7. Case folding.
    if opts.casefold:
        norm = norm.casefold()

    return norm


# ---------------------------------------------------------------------------
# Helpers for building indices
# ---------------------------------------------------------------------------


def build_normalized_index(
    keys: Iterable[str],
    *,
    options: Optional[NormalizationOptions] = None,
) -> Dict[str, str]:
    """
    Build an index from normalized keys to their original forms.

    Collision behavior:
        First-writer wins (deterministic). For collision details,
        use build_normalized_index_with_collisions().

    Args:
        keys: Iterable of raw key strings.
        options: Optional NormalizationOptions.

    Returns:
        dict {normalized_key -> original_key}
    """
    index: Dict[str, str] = {}
    opts = options or NormalizationOptions()

    for k in keys:
        if not isinstance(k, str):
            continue
        nk = normalize_for_lookup(k, options=opts)
        if not nk:
            continue
        index.setdefault(nk, k)

    return index


def build_normalized_index_with_collisions(
    keys: Iterable[str],
    *,
    options: Optional[NormalizationOptions] = None,
) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """
    Build an index and also report collisions.

    Collision behavior:
        The index keeps the first key (first-writer wins), and the
        collisions map records all raw keys that normalized to the same
        normalized key.

    Args:
        keys: Iterable of raw key strings.
        options: Optional NormalizationOptions.

    Returns:
        (index, collisions)
        - index: {normalized_key -> chosen_original_key}
        - collisions: {normalized_key -> [all_original_keys_in_order]}
    """
    index: Dict[str, str] = {}
    collisions_all: Dict[str, List[str]] = {}
    opts = options or NormalizationOptions()

    for k in keys:
        if not isinstance(k, str):
            continue
        nk = normalize_for_lookup(k, options=opts)
        if not nk:
            continue

        if nk not in index:
            index[nk] = k
            collisions_all[nk] = [k]
        else:
            collisions_all[nk].append(k)

    collisions = {nk: ks for nk, ks in collisions_all.items() if len(ks) > 1}
    return index, collisions

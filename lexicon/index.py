"""
lexicon/index.py

Unified access layer for per-language lexica stored in JSON under:

    data/lexicon/{lang_code}_lexicon.json

The goal of this module is NOT to prescribe a single universal schema
for all languages, but to provide a thin, stable API that:

- hides small schema differences between languages (en/fr/ja/sw, …),
- gives you a normalised `Lexeme` object,
- keeps the original raw JSON available when you need full details,
- offers convenience lookups by lemma or Wikidata QID.

Current supported shapes
------------------------

English (en_lexicon.json) :contentReference[oaicite:0]{index=0}

    {
      "meta": {...},
      "professions": {...},
      "nationalities": {...},
      "titles": {...},
      "honours": {...},
      "name_templates": {...}
    }

French (fr_lexicon.json) :contentReference[oaicite:1]{index=1}

    {
      "_meta": {...},
      "entries": { surface_string -> feature bundle }
    }

Japanese / Swahili (ja_lexicon.json, sw_lexicon.json) 

    {
      "_meta": {...},
      "lemmas": { lemma_key -> feature bundle }
    }

This module tries to normalise these into:

    Lexeme(
        language="fr",
        key="physicien",
        lemma="physicien",
        pos="NOUN",
        sense="profession" | None,
        data={...original entry...}
    )

The exact contents of `data` are deliberately left flexible: callers
can opt in to family- or language-specific details when needed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LexiconError(Exception):
    """Base exception for lexicon-related problems."""


class LexiconNotFound(LexiconError):
    """Raised when a {lang}_lexicon.json file cannot be located."""


class LexemeNotFound(LexiconError):
    """Raised when a specific lexeme key cannot be found in a lexicon."""


# ---------------------------------------------------------------------------
# Core data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Lexeme:
    """
    Normalised view of a lexicon entry.

    Attributes:
        language:
            BCP-47-ish language code (e.g. "en", "fr", "ja", "sw").

        key:
            Stable internal key for the entry, unique *within* a language.
            Examples:

                - "physicien"             (fr entries)
                - "mtu"                   (sw lemmas)
                - "professions:physicist" (en professions table)

        lemma:
            Canonical lemma or surface form for most uses. For some
            resources this is identical to `key`, but not always
            (e.g. multiword expressions or adjective vs country-name).

        pos:
            Coarse part-of-speech label where available, such as:
            "NOUN", "ADJ", "PROPN", "TITLE", "HONOUR".
            May be None if the source does not specify POS.

        sense:
            Very coarse sense label if available, such as:
            "profession", "country", "common_noun", etc.
            May be None.

        data:
            Original entry payload (after shallow copying) with any
            extra annotations (e.g. noun class, gender, wikidata_qid).
            Consumers that need language-specific detail should look here.
    """

    language: str
    key: str
    lemma: str
    pos: Optional[str] = None
    sense: Optional[str] = None
    data: Mapping[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Lexicon index
# ---------------------------------------------------------------------------


class LexiconIndex:
    """
    In-memory index for a single language's lexicon.

    Typically constructed via `load_lexicon(lang_code)`.

    Minimal usage:

        lex = load_lexicon("fr")
        phys = lex.get("physicien")
        print(phys.lemma, phys.pos)

    Convenience helpers:

        lex.find_by_lemma("Marie Curie")
        lex.find_by_qid("Q36")   # Poland (from en nationalities)
    """

    def __init__(
        self,
        lang_code: str,
        meta: Mapping[str, Any],
        entries: Mapping[str, Lexeme],
        raw: Mapping[str, Any],
    ) -> None:
        self.lang_code = lang_code
        self.meta: Dict[str, Any] = dict(meta)
        self._entries: Dict[str, Lexeme] = dict(entries)
        self._raw: Dict[str, Any] = dict(raw)

    # Basic introspection -------------------------------------------------

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._entries)

    def __iter__(self) -> Iterable[Lexeme]:  # pragma: no cover - trivial
        return iter(self._entries.values())

    @property
    def entries(self) -> Mapping[str, Lexeme]:
        """All lexemes keyed by `key`."""
        return self._entries

    @property
    def raw(self) -> Mapping[str, Any]:
        """
        Raw JSON payload for advanced use.

        This exposes language-specific structures such as:

            - English "name_templates"
            - Any future auxiliary tables

        The structure is intentionally *not* normalised.
        """
        return self._raw

    # Lookup helpers ------------------------------------------------------

    def get(self, key: str) -> Optional[Lexeme]:
        """
        Return the Lexeme with the given key, or None if missing.

        Keys are the internal stable identifiers such as "mtu" or
        "professions:physicist".
        """
        return self._entries.get(key)

    def get_or_raise(self, key: str) -> Lexeme:
        """
        Like `get`, but raises LexemeNotFound if the key is unknown.
        """
        if key not in self._entries:
            raise LexemeNotFound(
                f"Lexeme '{key}' not found in language '{self.lang_code}'."
            )
        return self._entries[key]

    def find_by_lemma(self, lemma: str, *, case_sensitive: bool = False) -> List[Lexeme]:
        """
        Return all lexemes whose `lemma` matches the given string.

        In many resources lemma == key, but we do not rely on it.
        By default the match is case-insensitive.
        """
        if not case_sensitive:
            target = lemma.lower()
            return [lx for lx in self._entries.values() if lx.lemma.lower() == target]
        return [lx for lx in self._entries.values() if lx.lemma == lemma]

    def find_by_qid(self, wikidata_qid: str) -> List[Lexeme]:
        """
        Return all lexemes that declare the given Wikidata QID.

        This looks for a `wikidata_qid` field inside `lexeme.data`.
        """
        results: List[Lexeme] = []
        for lex in self._entries.values():
            if str(lex.data.get("wikidata_qid")) == str(wikidata_qid):
                results.append(lex)
        return results

    def filter(self, predicate: Callable[[Lexeme], bool]) -> List[Lexeme]:
        """
        Generic filter helper.

        Example:

            # All human professions (where the entry has human=True)
            human_professions = lex.filter(
                lambda lx: lx.data.get("human") is True
            )
        """
        return [lx for lx in self._entries.values() if predicate(lx)]


# ---------------------------------------------------------------------------
# Loading and normalisation
# ---------------------------------------------------------------------------

# Simple in-process cache to avoid re-reading the same JSON files.
_CACHE: Dict[str, LexiconIndex] = {}


def _project_root() -> Path:
    """
    Infer the project root as the parent of this file's directory.

    This assumes the layout:

        abstract-wiki-architect/
            lexicon/
                index.py   <-- this file
            data/
                lexicon/
                    en_lexicon.json
                    ...
    """
    return Path(__file__).resolve().parent.parent


def _lexicon_dir(base_dir: Optional[Path] = None) -> Path:
    base = base_dir or _project_root()
    return base / "data" / "lexicon"


def available_languages(base_dir: Optional[Path] = None) -> List[str]:
    """
    Inspect data/lexicon/ and return a sorted list of language codes
    for which a *local* JSON lexicon exists.

        ["en", "fr", "ja", "sw", ...]
    """
    directory = _lexicon_dir(base_dir)
    if not directory.exists():
        return []

    langs: List[str] = []
    for path in directory.glob("*_lexicon.json"):
        name = path.name  # e.g. "en_lexicon.json"
        code = name.split("_", 1)[0]
        if code:
            langs.append(code)
    return sorted(sorted(set(langs)))


def load_lexicon(
    lang_code: str,
    base_dir: Optional[Path] = None,
    *,
    use_cache: bool = True,
) -> LexiconIndex:
    """
    Load and normalise the lexicon for a given language.

    Args:
        lang_code:
            Language code such as "en", "fr", "ja", "sw".

        base_dir:
            Optional explicit project root. Normally you can omit this
            and let the function infer the project root relative to this
            file location.

        use_cache:
            If True (default), keep a process-local cache per language.

    Raises:
        LexiconNotFound: if the JSON file does not exist.
    """
    cache_key = f"{lang_code}@{base_dir}" if base_dir is not None else lang_code
    if use_cache and cache_key in _CACHE:
        return _CACHE[cache_key]

    lex_dir = _lexicon_dir(base_dir)
    path = lex_dir / f"{lang_code}_lexicon.json"

    if not path.exists():
        raise LexiconNotFound(
            f"No lexicon file found for language '{lang_code}' "
            f"(expected at {path})."
        )

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    index = _build_index_from_raw(lang_code, raw)

    if use_cache:
        _CACHE[cache_key] = index
    return index


def _build_index_from_raw(lang_code: str, raw: Mapping[str, Any]) -> LexiconIndex:
    """
    Normalise a language-specific JSON payload into a LexiconIndex.

    This function knows about a few concrete schema variants but is
    intentionally conservative: if it encounters unknown keys, it
    leaves them in `LexiconIndex.raw` for higher-level code to use.

    The normalisation strategy is:

        - Prefer `_meta` over `meta` for metadata if present.
        - Collect:
            * `raw["lemmas"]` as generic lemma entries.
            * `raw["entries"]` as generic entry-surface mappings.
            * For English-style tables:
                - "professions"
                - "nationalities"
                - "titles"
                - "honours"
    """
    meta = raw.get("_meta") or raw.get("meta") or {}
    entries: Dict[str, Lexeme] = {}

    # 1. Languages with "lemmas": { id -> feature bundle }
    lemmas = raw.get("lemmas")
    if isinstance(lemmas, dict):
        for key, entry in lemmas.items():
            if not isinstance(entry, dict):
                continue
            lemma = str(entry.get("lemma") or key)
            pos = entry.get("pos")
            sense = entry.get("sense") or entry.get("gloss")
            data = dict(entry)
            data.setdefault("category", "lemma")
            entries[key] = Lexeme(
                language=lang_code,
                key=key,
                lemma=lemma,
                pos=pos,
                sense=sense,
                data=data,
            )

    # 2. Languages with "entries": { surface -> feature bundle }
    surface_entries = raw.get("entries")
    if isinstance(surface_entries, dict):
        for surface, entry in surface_entries.items():
            if not isinstance(entry, dict):
                continue
            lemma = str(entry.get("lemma") or surface)
            pos = entry.get("pos")
            sense = entry.get("sense") or entry.get("gloss")
            data = dict(entry)
            data.setdefault("surface", surface)
            data.setdefault("category", "entry")
            entries[surface] = Lexeme(
                language=lang_code,
                key=surface,
                lemma=lemma,
                pos=pos,
                sense=sense,
                data=data,
            )

    # 3. English-style multi-table schema (professions, nationalities, titles, honours)
    #    See data/lexicon/en_lexicon.json. :contentReference[oaicite:3]{index=3}
    multi_tables = {
        "professions": "NOUN",
        "nationalities": "ADJ",  # we treat the nationality adjective as the lemma
        "titles": "TITLE",
        "honours": "HONOUR",
    }

    for category, default_pos in multi_tables.items():
        table = raw.get(category)
        if not isinstance(table, dict):
            continue

        for local_key, entry in table.items():
            if not isinstance(entry, dict):
                continue

            # Heuristics for picking a suitable lemma:
            #   professions: lemma
            #   nationalities: adjective or demonym
            #   honours: label
            lemma = (
                entry.get("lemma")
                or entry.get("adjective")
                or entry.get("demonym")
                or entry.get("label")
                or local_key
            )
            lemma_str = str(lemma)

            # Some entries (especially honours / titles) may not have a POS; we
            # still attach a coarse label to help constructions choose words.
            pos = entry.get("pos") or default_pos

            # Sense is typically not specified for these; we leave as None.
            sense: Optional[str] = entry.get("sense")

            data = dict(entry)
            data.setdefault("category", category)
            data.setdefault("local_key", local_key)

            global_key = f"{category}:{local_key}"
            entries[global_key] = Lexeme(
                language=lang_code,
                key=global_key,
                lemma=lemma_str,
                pos=pos,
                sense=sense,
                data=data,
            )

    return LexiconIndex(lang_code=lang_code, meta=meta, entries=entries, raw=raw)


# ---------------------------------------------------------------------------
# CLI helper (optional)
# ---------------------------------------------------------------------------


def _main() -> None:  # pragma: no cover - tiny CLI helper
    """
    Minimal debugging CLI:

        python -m lexicon.index en
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m lexicon.index <lang_code>")
        print("Example: python -m lexicon.index en")
        sys.exit(1)

    lang = sys.argv[1]
    lex = load_lexicon(lang)

    print(f"Loaded lexicon for language '{lang}' with {len(lex)} entries.")
    print("Meta:", json.dumps(lex.meta, ensure_ascii=False, indent=2))

    # Print a few sample keys
    for i, lx in enumerate(lex):
        if i >= 10:
            break
        print(f"- {lx.key!r}: lemma={lx.lemma!r}, pos={lx.pos!r}, sense={lx.sense!r}")


if __name__ == "__main__":  # pragma: no cover
    _main()

"""
utils/build_lexicon_from_wikidata.py
====================================

Offline builder: turn a (filtered) Wikidata / Lexeme dump into a
language-specific lexicon JSON file under `data/lexicon/`.

This script is intentionally conservative and best-effort:

- It expects an input file that is either:
    * a standard Wikidata Lexeme dump (JSON), or
    * a line-delimited JSON file where each line is a Lexeme object.

- It extracts:
    * main lemma in the target language (`--lang`),
    * lexical category (mapped to a coarse POS),
    * optional QID links from senses / forms if present.

- It writes a JSON file that roughly matches the internal lexicon
  schema expected by `lexicon/loader.py` and `lexicon/schema.py`:

    {
        "meta": {
            "language": "it",
            "schema_version": 1,
            "source": "wikidata",
            "source_dump": "lexemes_dump.json.gz"
        },
        "lemmas": {
            "fisico": {
                "lemma": "fisico",
                "pos": "NOUN",
                "category": "lexeme",
                "human": false,
                "forms": {
                    "default": "fisico"
                },
                "features": {
                    "lexeme_id": "L12345"
                },
                "qid": null
            },
            ...
        }
    }

You will usually call this script on a *filtered* dump (for the
languages / domains you care about), not the full Wikidata dump.

Example
-------

    python utils/build_lexicon_from_wikidata.py \\
        --lang it \\
        --dump data/raw_wikidata/lexemes_dump.json.gz \\
        --out data/lexicon/it_lexicon.json

"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from typing import Any, Dict, Iterable, Iterator, Optional, Tuple

from utils.logging_setup import get_logger
from lexicon.schema import SCHEMA_VERSION

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lexeme parsing helpers (best-effort, Wikidata-ish)
# ---------------------------------------------------------------------------


def _open_maybe_gzip(path: str) -> Iterable[str]:
    """
    Open a file that may or may not be gzipped and yield lines.

    We keep this simple: check extension, fall back to plain open.
    """
    if path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                yield line
    else:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                yield line


def _is_dump_wrapper(obj: Any) -> bool:
    """
    Heuristic: return True if this looks like a standard Wikidata dump
    wrapper object (with a top-level 'entities' field).
    """
    return isinstance(obj, dict) and "entities" in obj and isinstance(
        obj["entities"], dict
    )


def _iter_lexemes_from_dump(path: str) -> Iterator[Dict[str, Any]]:
    """
    Yield Lexeme-like objects from a dump file.

    Supports:
        - Line-delimited JSON: each line is one Lexeme object.
        - Single massive JSON with {"entities": { "L1": {...}, ... }}.
    """
    log.info("Reading lexeme dump from %s", path)
    # Try to sniff whether it's a big JSON or line-delimited
    # by peeking at the first non-empty line.
    lines = list(_open_maybe_gzip(path))
    if not lines:
        log.warning("Dump file %s is empty.", path)
        return iter(())

    first_non_empty = next((ln for ln in lines if ln.strip()), None)
    if first_non_empty is None:
        log.warning("Dump file %s contains only whitespace.", path)
        return iter(())

    # Try to parse as a single JSON object
    try:
        obj = json.loads("".join(lines))
    except Exception:
        obj = None

    if _is_dump_wrapper(obj):
        # Standard Wikidata-style dump: { "entities": { "L1": {...}, ... } }
        entities = obj["entities"]
        for _, lexeme in entities.items():
            if isinstance(lexeme, dict):
                yield lexeme
        return

    # Otherwise, treat as line-delimited JSON
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            log.debug("Skipping non-JSON line in dump: %r", ln[:80])
            continue
        if isinstance(obj, dict):
            yield obj


# Mapping from Wikidata lexicalCategory QID → coarse POS.
# This is intentionally partial and safe; unknown QIDs fall back to "X".
LEXICAL_CATEGORY_POS_MAP: Dict[str, str] = {
    # Common Wikidata lexical categories:
    # Q24905 = noun, Q34698 = verb, Q34649 = adjective, Q1084 = adverb, etc.
    "Q24905": "NOUN",
    "Q34698": "VERB",
    "Q34649": "ADJ",
    "Q1084": "ADV",
}


def _extract_main_lemma(lexeme: Dict[str, Any], lang_code: str) -> Optional[str]:
    """
    Extract the main lemma in the target language from a Lexeme object.

    Wikidata Lexeme structure typically has:
        lexeme["lemmas"] = {
            "en": { "language": "en", "value": "physicist" },
            ...
        }
    """
    lemmas = lexeme.get("lemmas")
    if not isinstance(lemmas, dict):
        return None

    entry = lemmas.get(lang_code)
    if not isinstance(entry, dict):
        return None

    val = entry.get("value")
    return val if isinstance(val, str) else None


def _extract_pos(lexeme: Dict[str, Any]) -> str:
    """
    Extract coarse POS from a Lexeme object.

    Wikidata Lexeme has:
        lexeme["lexicalCategory"] = { "id": "Q24905", ... }

    We map it via LEXICAL_CATEGORY_POS_MAP, defaulting to "X".
    """
    cat = lexeme.get("lexicalCategory")
    if isinstance(cat, dict):
        qid = cat.get("id")
        if isinstance(qid, str):
            return LEXICAL_CATEGORY_POS_MAP.get(qid, "X")
    return "X"


def _extract_qid_from_senses(lexeme: Dict[str, Any]) -> Optional[str]:
    """
    Attempt to extract a representative QID from sense glosses / statements.

    This is intentionally very conservative; we simply look for:
        lexeme["senses"][0]["claim"] / {"wikidataItem": {"id": "Q..."}}
    or similar custom shapes in filtered dumps.

    If nothing recognizable is found, return None.
    """
    senses = lexeme.get("senses")
    if not isinstance(senses, list) or not senses:
        return None

    first = senses[0]
    if not isinstance(first, dict):
        return None

    # Extremely generic pattern: a sub-dict with an "id" starting with "Q"
    # (this is a heuristic for demonstration purposes only).
    for value in first.values():
        if isinstance(value, dict):
            qid = value.get("id")
            if isinstance(qid, str) and qid.startswith("Q"):
                return qid
    return None


def _build_lexeme_entry(
    lang_code: str,
    lexeme: Dict[str, Any],
) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Convert a single Wikidata Lexeme object into a (lemma, entry) pair
    for the internal lexicon format.

    Returns:
        (lemma, entry_dict) or None if the lexeme cannot be used
        (e.g. no lemma in target language).
    """
    lemma = _extract_main_lemma(lexeme, lang_code)
    if not lemma:
        return None

    pos = _extract_pos(lexeme)
    lexeme_id = lexeme.get("id")
    if not isinstance(lexeme_id, str):
        lexeme_id = None

    qid = _extract_qid_from_senses(lexeme)

    entry: Dict[str, Any] = {
        "lemma": lemma,
        "pos": pos,
        "category": "lexeme",
        "human": False,
        "gender": "none",
        "forms": {
            "default": lemma
        },
        "features": {},
        "qid": qid,
    }

    if lexeme_id:
        entry["features"]["lexeme_id"] = lexeme_id

    return lemma, entry


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------


def build_lexicon_from_dump(
    lang_code: str,
    dump_path: str,
    *,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build an in-memory lexicon dict for a given language from a dump file.

    Args:
        lang_code:
            Target language code (e.g. "en", "it", "tr").
        dump_path:
            Path to a lexeme dump (optionally gzipped).
        limit:
            Optional maximum number of lexemes to ingest (for testing).

    Returns:
        A dict of the form:

            {
                "meta": {...},
                "lemmas": {
                    "foo": {...},
                    "bar": {...},
                    ...
                }
            }

        ready to be JSON-serialized to `data/lexicon/<lang>_lexicon.json`.
    """
    lemmas: Dict[str, Dict[str, Any]] = {}
    count_total = 0
    count_used = 0

    for lexeme in _iter_lexemes_from_dump(dump_path):
        count_total += 1

        pair = _build_lexeme_entry(lang_code, lexeme)
        if pair is None:
            continue

        lemma, entry = pair
        if lemma in lemmas:
            # Keep first entry; skip duplicates
            continue

        lemmas[lemma] = entry
        count_used += 1

        if limit is not None and count_used >= limit:
            break

        if count_used and count_used % 10_000 == 0:
            log.info(
                "Built %d entries for %s (processed %d records)",
                count_used,
                lang_code,
                count_total,
            )

    log.info(
        "Finished building lexicon for %s: %d entries used (from %d records).",
        lang_code,
        count_used,
        count_total,
    )

    meta = {
        "language": lang_code,
        "schema_version": SCHEMA_VERSION,
        "source": "wikidata_lexeme_dump",
        "source_dump": os.path.basename(dump_path),
        "entries_total": count_total,
        "entries_used": count_used,
    }

    return {
        "meta": meta,
        "lemmas": lemmas,
    }


def save_lexicon(lexicon: Dict[str, Any], out_path: str) -> None:
    """
    Serialize a lexicon dict to JSON on disk.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(lexicon, f, ensure_ascii=False, indent=2)
    log.info("Wrote lexicon JSON to %s", out_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a language-specific lexicon JSON from a Wikidata Lexeme dump."
    )
    parser.add_argument(
        "--lang",
        required=True,
        help="Target language code (e.g. 'it', 'en', 'tr').",
    )
    parser.add_argument(
        "--dump",
        required=True,
        help="Path to a Wikidata Lexeme dump (JSON or JSON.gz).",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output path for the resulting lexicon JSON.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of lexemes to ingest (for testing).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    lang_code: str = args.lang
    dump_path: str = args.dump
    out_path: str = args.out
    limit: Optional[int] = args.limit

    if not os.path.isfile(dump_path):
        print(f"❌ Dump file not found: {dump_path}", file=sys.stderr)
        sys.exit(1)

    log.info(
        "Building lexicon for lang=%s from dump=%s (limit=%s)",
        lang_code,
        dump_path,
        limit,
    )

    lexicon = build_lexicon_from_dump(lang_code, dump_path, limit=limit)
    save_lexicon(lexicon, out_path)


if __name__ == "__main__":
    main()

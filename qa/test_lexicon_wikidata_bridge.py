"""
qa/test_lexicon_wikidata_bridge.py
==================================

Tests for the Wikidata → internal-lexicon bridge implemented in
`utils/build_lexicon_from_wikidata.py`.

These tests use tiny synthetic “lexeme” objects written to temporary
files (JSON lines and gzipped JSON) to verify that:

- Lemmas in the target language are extracted correctly.
- POS is mapped from `lexicalCategory` QIDs.
- A representative QID can be pulled from senses.
- The resulting structure matches the expected lexicon shape.
"""

from __future__ import annotations

import json
import gzip
from typing import Dict, Any

from utils.build_lexicon_from_wikidata import build_lexicon_from_dump


def _make_sample_lexeme(
    *,
    lexeme_id: str = "L1",
    lang: str = "it",
    lemma_value: str = "fisico",
    lexical_category_qid: str = "Q24905",  # noun
    sense_qid: str = "Q169470",
) -> Dict[str, Any]:
    """
    Build a small, Wikidata-like Lexeme object suitable for feeding
    into `build_lexicon_from_dump`.

    The structure is intentionally minimal and only exercises the
    parts used by the builder.
    """
    return {
        "id": lexeme_id,
        "lemmas": {
            lang: {
                "language": lang,
                "value": lemma_value,
            }
        },
        "lexicalCategory": {
            "id": lexical_category_qid,
        },
        "senses": [
            {
                # Any sub-dict with an "id" starting with "Q" is accepted
                # by _extract_qid_from_senses.
                "wikidataItem": {"id": sense_qid}
            }
        ],
    }


def test_build_lexicon_from_line_delimited_json(tmp_path) -> None:
    """
    Ensure that a simple line-delimited JSON dump with a single Lexeme
    yields a lexicon with the expected lemma, POS, QID, and meta.
    """
    dump_path = tmp_path / "lexemes_ldjson.json"

    lexeme = _make_sample_lexeme(
        lexeme_id="L1",
        lang="it",
        lemma_value="fisico",
        lexical_category_qid="Q24905",  # noun
        sense_qid="Q169470",
    )

    # Write one lexeme per line
    with dump_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(lexeme, ensure_ascii=False) + "\n")

    lexicon = build_lexicon_from_dump("it", str(dump_path))

    # Basic meta
    meta = lexicon.get("meta", {})
    assert meta.get("language") == "it"
    assert meta.get("source") == "wikidata_lexeme_dump"
    assert meta.get("entries_used") == 1

    # Lemma entries
    lemmas = lexicon.get("lemmas", {})
    assert "fisico" in lemmas
    entry = lemmas["fisico"]

    assert entry["lemma"] == "fisico"
    assert entry["pos"] == "NOUN"  # mapped from Q24905
    assert entry["qid"] == "Q169470"
    assert entry["forms"]["default"] == "fisico"
    assert entry["features"]["lexeme_id"] == "L1"


def test_build_lexicon_from_gzipped_dump(tmp_path) -> None:
    """
    Ensure that gzipped dumps are handled correctly and produce the
    same lexicon structure as plain JSON.
    """
    dump_path = tmp_path / "lexemes_dump.json.gz"

    lexeme = _make_sample_lexeme(
        lexeme_id="L2",
        lang="it",
        lemma_value="chimico",
        lexical_category_qid="Q24905",  # noun
        sense_qid="Q593644",
    )

    # Write gzipped line-delimited JSON
    with gzip.open(dump_path, "wt", encoding="utf-8") as f:
        f.write(json.dumps(lexeme, ensure_ascii=False) + "\n")

    lexicon = build_lexicon_from_dump("it", str(dump_path))

    meta = lexicon.get("meta", {})
    assert meta.get("language") == "it"
    assert meta.get("source_dump") == dump_path.name

    lemmas = lexicon.get("lemmas", {})
    assert "chimico" in lemmas
    entry = lemmas["chimico"]

    assert entry["lemma"] == "chimico"
    assert entry["pos"] == "NOUN"
    assert entry["qid"] == "Q593644"
    assert entry["forms"]["default"] == "chimico"
    assert entry["features"]["lexeme_id"] == "L2"


def test_duplicate_lemmas_keep_first(tmp_path) -> None:
    """
    If multiple Lexeme objects produce the same lemma in the target
    language, the builder should keep the first and ignore later ones.
    """
    dump_path = tmp_path / "lexemes_dups.json"

    lexeme1 = _make_sample_lexeme(
        lexeme_id="L10",
        lang="it",
        lemma_value="autore",
        lexical_category_qid="Q24905",
        sense_qid="Q1",
    )
    lexeme2 = _make_sample_lexeme(
        lexeme_id="L11",
        lang="it",
        lemma_value="autore",
        lexical_category_qid="Q24905",
        sense_qid="Q2",
    )

    with dump_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(lexeme1, ensure_ascii=False) + "\n")
        f.write(json.dumps(lexeme2, ensure_ascii=False) + "\n")

    lexicon = build_lexicon_from_dump("it", str(dump_path))

    lemmas = lexicon.get("lemmas", {})
    assert "autore" in lemmas
    entry = lemmas["autore"]

    # First lexeme should win
    assert entry["features"]["lexeme_id"] == "L10"
    assert entry["qid"] == "Q1"

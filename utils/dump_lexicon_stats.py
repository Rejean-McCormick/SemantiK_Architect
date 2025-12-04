"""
utils/dump_lexicon_stats.py
---------------------------

Quick statistics over the JSON lexicon files in data/lexicon/.

This is a lightweight, data-driven script: it reads the raw JSON files
directly, without requiring the full `lexicon` Python package to be
implemented. It assumes the files follow the schema used in this
project:

    {
      "_meta": { ... },
      "lemmas": {
        "lemma_string": {
          "pos": "NOUN" | "ADJ" | "VERB" | ...,
          "human": true/false (optional),
          "nationality": true/false (optional),
          ...
        },
        ...
      }
    }

By default it scans all *.json files under data/lexicon/, merges files
for the same language (e.g. en_lexicon.json + en_people.json), and
prints per-language stats.

Usage
=====

From project root:

    python utils/dump_lexicon_stats.py
    python utils/dump_lexicon_stats.py --langs en fr
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Tuple


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LEXICON_DIR = os.path.join(PROJECT_ROOT, "data", "lexicon")


# ---------------------------------------------------------------------------
# Helpers for finding / grouping lexicon files
# ---------------------------------------------------------------------------


def _infer_lang_from_filename(filename: str) -> str:
    """
    Infer a language code from a lexicon JSON filename.

    Heuristic:
        - Take the stem (filename without extension).
        - Use the part before the first underscore, if present.
          Example: "en_lexicon" → "en", "en_people" → "en"
        - Otherwise use the whole stem.
    """
    stem = os.path.splitext(os.path.basename(filename))[0]
    if "_" in stem:
        return stem.split("_", 1)[0]
    return stem


def find_lexicon_files(
    lexicon_dir: str, langs: Iterable[str] | None = None
) -> Dict[str, List[str]]:
    """
    Scan lexicon_dir for JSON lexicon files and group them by language code.

    Args:
        lexicon_dir:
            Directory containing *.json lexicon files.
        langs:
            Optional iterable of language codes to restrict to. If None,
            all languages are included.

    Returns:
        Mapping: lang_code → list of JSON file paths (absolute).
    """
    if langs is not None:
        target_langs = {s.strip() for s in langs if s.strip()}
    else:
        target_langs = None

    by_lang: Dict[str, List[str]] = defaultdict(list)

    if not os.path.isdir(lexicon_dir):
        raise FileNotFoundError(f"Lexicon directory not found: {lexicon_dir}")

    for entry in os.listdir(lexicon_dir):
        if not entry.endswith(".json"):
            continue
        path = os.path.join(lexicon_dir, entry)
        if not os.path.isfile(path):
            continue

        lang = _infer_lang_from_filename(entry)
        if target_langs is not None and lang not in target_langs:
            continue

        by_lang[lang].append(path)

    return by_lang


# ---------------------------------------------------------------------------
# Stats computation
# ---------------------------------------------------------------------------


def load_lemmas_from_files(files: Iterable[str]) -> Dict[str, dict]:
    """
    Load and merge lemma dictionaries from a list of JSON files.

    For identical lemma keys across files for the same language,
    later files override earlier ones.
    """
    merged: Dict[str, dict] = {}
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        lemmas = data.get("lemmas", {})
        if not isinstance(lemmas, dict):
            continue
        merged.update(lemmas)
    return merged


def compute_stats_for_lang(
    lang: str, lemmas: Dict[str, dict]
) -> Tuple[Counter, int, int, int]:
    """
    Compute basic statistics for a single language.

    Returns:
        pos_counts:
            Counter mapping POS → count of lemmas.
        total_human_nouns:
            Count of lemmas with pos=NOUN and human=true.
        total_nationality_adjs:
            Count of lemmas with pos=ADJ and nationality=true.
        total_lemmas:
            Total number of lemma entries.
    """
    pos_counts: Counter = Counter()
    human_nouns = 0
    nationality_adjs = 0

    for lemma, entry in lemmas.items():
        if not isinstance(entry, dict):
            continue
        pos = entry.get("pos", "").upper().strip()
        if pos:
            pos_counts[pos] += 1

        if pos == "NOUN" and bool(entry.get("human", False)):
            human_nouns += 1

        if pos == "ADJ" and bool(entry.get("nationality", False)):
            nationality_adjs += 1

    total_lemmas = len(lemmas)
    return pos_counts, human_nouns, nationality_adjs, total_lemmas


def print_stats(
    lang: str,
    files: List[str],
    pos_counts: Counter,
    human_nouns: int,
    nationality_adjs: int,
    total_lemmas: int,
) -> None:
    """
    Pretty-print stats for a single language.
    """
    print(f"\n=== Lexicon stats for '{lang}' ===")
    print(f"Files: {', '.join(os.path.basename(f) for f in files)}")
    print(f"Total lemmas: {total_lemmas}")

    if total_lemmas == 0:
        print("No lemmas found.")
        return

    print("\nBy POS:")
    for pos, count in pos_counts.most_common():
        pct = 100.0 * count / total_lemmas
        print(f"  {pos:<8} {count:5d} ({pct:5.1f}%)")

    print("\nSelected categories:")
    print(f"  Human nouns:          {human_nouns}")
    print(f"  Nationality adjectives: {nationality_adjs}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dump basic statistics about lexicon JSON files."
    )
    parser.add_argument(
        "--lexicon-dir",
        "-d",
        default=DEFAULT_LEXICON_DIR,
        help=f"Directory containing lexicon JSON files (default: {DEFAULT_LEXICON_DIR})",
    )
    parser.add_argument(
        "--langs",
        "-l",
        nargs="*",
        help="Optional list of language codes to restrict to (e.g. en fr ru). "
        "If omitted, all languages found in the directory are included.",
    )
    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    lexicon_dir = os.path.abspath(args.lexicon_dir)
    lang_files = find_lexicon_files(lexicon_dir, langs=args.langs)

    if not lang_files:
        if args.langs:
            print(
                f"No lexicon JSON files found for languages {args.langs} in {lexicon_dir}."
            )
        else:
            print(f"No lexicon JSON files found in {lexicon_dir}.")
        return

    print(f"Lexicon directory: {lexicon_dir}")
    print(f"Languages found: {', '.join(sorted(lang_files.keys()))}")

    for lang, files in sorted(lang_files.items()):
        lemmas = load_lemmas_from_files(files)
        pos_counts, human_nouns, nationality_adjs, total_lemmas = compute_stats_for_lang(
            lang, lemmas
        )
        print_stats(lang, files, pos_counts, human_nouns, nationality_adjs, total_lemmas)

    print("")  # final newline


if __name__ == "__main__":
    main()

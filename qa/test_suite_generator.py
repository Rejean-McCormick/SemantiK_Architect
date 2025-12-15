#!/usr/bin/env python
# qa\test_suite_generator.py
"""
qa/test_suite_generator.py

Generate CSV test-suite templates for all (or a subset of) languages defined
in `language_profiles/profiles.json`.

The goal is to provide a uniform, construction-oriented template that
contributors (or an LLM) can fill with:

    - Lemmas / slot specifications for each test case.
    - The EXPECTED_FULL_SENTENCE string in the target language.

Example usage:

    python qa/test_suite_generator.py
    python qa/test_suite_generator.py --langs en fr --rows-per-construction 20

Output (by default):

    qa/generated_datasets/test_suite_en.csv
    qa/generated_datasets/test_suite_fr.csv
    ...

Each CSV contains rows like:

    ID,LANGUAGE,CONSTRUCTION_ID,SUBJECT_LEMMA,OBJECT_LEMMA,VERB_LEMMA,ADJ_LEMMA,
    STANDARD_LEMMA,DOMAIN_NP,TENSE,DEGREE,RAW_SLOTS_JSON,EXPECTED_FULL_SENTENCE

Most fields start empty and are meant to be filled manually / by an LLM.
"""

import argparse
import csv
import json
import os
from typing import Dict, List, Any


# --------------------------------------------------------------------------- #
# Constructions inventory
# --------------------------------------------------------------------------- #

CONSTRUCTION_IDS: List[str] = [
    "COPULA_EQUATIVE_SIMPLE",
    "COPULA_EQUATIVE_CLASSIFICATION",
    "COPULA_ATTRIBUTIVE_ADJ",
    "COPULA_ATTRIBUTIVE_NP",
    "COPULA_LOCATIVE",
    "COPULA_EXISTENTIAL",
    "POSSESSION_HAVE",
    "POSSESSION_EXISTENTIAL",
    "INTRANSITIVE_EVENT",
    "TRANSITIVE_EVENT",
    "DITRANSITIVE_EVENT",
    "PASSIVE_EVENT",
    "CAUSATIVE_EVENT",
    "TOPIC_COMMENT_COPULAR",
    "TOPIC_COMMENT_EVENTIVE",
    "APPOSITION_NP",
    "RELATIVE_CLAUSE_SUBJECT_GAP",
    "RELATIVE_CLAUSE_OBJECT_GAP",
    "COORDINATION_CLAUSES",
    "COMPARATIVE_SUPERLATIVE",
]


# --------------------------------------------------------------------------- #
# I/O helpers
# --------------------------------------------------------------------------- #


def load_language_profiles(path: str) -> Dict[str, Any]:
    """
    Load language profiles from a JSON file.

    The file is expected to map language codes to profile objects, e.g.:

        {
          "en": { "language_code": "en", ... },
          "fr": { "language_code": "fr", ... }
        }
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Normalize keys: ensure each entry has a "language_code"
    normalized: Dict[str, Any] = {}
    for code, profile in data.items():
        if isinstance(profile, dict):
            if "language_code" not in profile:
                profile["language_code"] = code
            normalized[code] = profile
    return normalized


def ensure_dir(path: str) -> None:
    """
    Ensure that a directory exists (mkdir -p).
    """
    os.makedirs(path, exist_ok=True)


# --------------------------------------------------------------------------- #
# Test-suite generation
# --------------------------------------------------------------------------- #

CSV_HEADERS: List[str] = [
    "ID",
    "LANGUAGE",
    "CONSTRUCTION_ID",
    "SUBJECT_LEMMA",
    "OBJECT_LEMMA",
    "VERB_LEMMA",
    "ADJ_LEMMA",
    "STANDARD_LEMMA",
    "DOMAIN_NP",
    "TENSE",
    "DEGREE",
    "RAW_SLOTS_JSON",
    "EXPECTED_FULL_SENTENCE",
]


def generate_rows_for_language(
    lang_code: str,
    rows_per_construction: int,
) -> List[Dict[str, str]]:
    """
    Generate empty skeleton rows for a given language.

    Each construction gets `rows_per_construction` rows with:
      - ID set to: {lang}-{construction}-{index}
      - LANGUAGE set to: lang_code
      - CONSTRUCTION_ID set to: the construction identifier
      - Other fields blank, ready to be filled.
    """
    rows: List[Dict[str, str]] = []

    for construction_id in CONSTRUCTION_IDS:
        for idx in range(1, rows_per_construction + 1):
            row_id = f"{lang_code}-{construction_id}-{idx}"

            row: Dict[str, str] = {
                "ID": row_id,
                "LANGUAGE": lang_code,
                "CONSTRUCTION_ID": construction_id,
                "SUBJECT_LEMMA": "",
                "OBJECT_LEMMA": "",
                "VERB_LEMMA": "",
                "ADJ_LEMMA": "",
                "STANDARD_LEMMA": "",
                "DOMAIN_NP": "",
                "TENSE": "",
                "DEGREE": "",
                # RAW_SLOTS_JSON can optionally be used by advanced users
                # to store a full slot-spec object (in JSON) for this row.
                "RAW_SLOTS_JSON": "",
                # EXPECTED_FULL_SENTENCE is the human/LLM-provided
                # gold-standard surface form in the target language.
                "EXPECTED_FULL_SENTENCE": "",
            }
            rows.append(row)

    return rows


def write_csv(path: str, rows: List[Dict[str, str]]) -> None:
    """
    Write the given rows to a CSV file at `path` using UTF-8.

    Overwrites any existing file.
    """
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate CSV test-suite templates for each language."
    )
    parser.add_argument(
        "--profiles-path",
        default="language_profiles/profiles.json",
        help="Path to language profiles JSON file.",
    )
    parser.add_argument(
        "--output-dir",
        default="qa/generated_datasets",
        help="Directory where CSV test suites will be written.",
    )
    parser.add_argument(
        "--langs",
        nargs="*",
        help=(
            "Optional list of language codes to generate. "
            "If omitted, all languages in the profiles file are used."
        ),
    )
    parser.add_argument(
        "--rows-per-construction",
        type=int,
        default=10,
        help="Number of rows per construction per language.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    profiles = load_language_profiles(args.profiles_path)
    if args.langs:
        target_langs = [code for code in args.langs if code in profiles]
    else:
        target_langs = sorted(profiles.keys())

    ensure_dir(args.output_dir)

    for lang_code in target_langs:
        rows = generate_rows_for_language(
            lang_code=lang_code,
            rows_per_construction=args.rows_per_construction,
        )
        out_path = os.path.join(args.output_dir, f"test_suite_{lang_code}.csv")
        write_csv(out_path, rows)


if __name__ == "__main__":
    main()

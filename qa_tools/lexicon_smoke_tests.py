"""
qa_tools/lexicon_smoke_tests.py
===============================

Lightweight structural checks for all lexicon JSON files.

This module is designed to work both:

- As a pytest test file (functions named `test_*`), and
- As a standalone script:

      python qa_tools/lexicon_smoke_tests.py

It validates:

1. That there is at least one *_lexicon.json file in data/lexicon/.
2. That each such file is valid JSON and passes the structural checks
   in `lexicon.schema.validate_lexicon_structure` (no errors).
3. That basic metadata (language, schema_version) is reasonable.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

from lexicon.loader import available_languages
from lexicon.schema import SchemaIssue, validate_lexicon_structure

from utils.logging_setup import get_logger

log = get_logger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEXICON_DIR = os.path.join(PROJECT_ROOT, "data", "lexicon")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _lexicon_path_for_lang(lang: str) -> str:
    """
    Compute the expected lexicon JSON path for a given language code.
    """
    filename = f"{lang}_lexicon.json"
    return os.path.join(LEXICON_DIR, filename)


def _load_json(path: str) -> Dict[str, Any]:
    """
    Load a JSON file and return the parsed object.
    Raises ValueError on decode errors.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _collect_schema_issues() -> List[Tuple[str, List[SchemaIssue]]]:
    """
    For all available lexica, run schema validation and return a list of
    (lang_code, issues) pairs.
    """
    results: List[Tuple[str, List[SchemaIssue]]] = []

    langs = available_languages()
    for lang in langs:
        path = _lexicon_path_for_lang(lang)
        try:
            data = _load_json(path)
        except Exception as e:
            # Treat a JSON load failure as a single fatal error issue
            issue = SchemaIssue(
                path="",
                message=f"Failed to parse JSON: {e}",
                level="error",
            )
            results.append((lang, [issue]))
            continue

        issues = validate_lexicon_structure(lang, data)
        results.append((lang, issues))

    return results


# ---------------------------------------------------------------------------
# Pytest tests
# ---------------------------------------------------------------------------


def test_lexicon_directory_exists() -> None:
    """
    Ensure the data/lexicon directory exists.
    """
    assert os.path.isdir(LEXICON_DIR), f"Lexicon directory not found: {LEXICON_DIR}"


def test_at_least_one_lexicon_file() -> None:
    """
    Ensure there is at least one *_lexicon.json file.
    """
    langs = available_languages()
    assert (
        len(langs) > 0
    ), f"No *_lexicon.json files found in {LEXICON_DIR}. Expected at least one."


def test_all_lexicon_files_exist() -> None:
    """
    For every language discovered by available_languages(), the
    corresponding JSON file must exist on disk.
    """
    missing = []
    for lang in available_languages():
        path = _lexicon_path_for_lang(lang)
        if not os.path.isfile(path):
            missing.append((lang, path))

    assert not missing, f"Missing lexicon files: {missing}"


def test_lexicon_schema_has_no_errors() -> None:
    """
    Validate lexicon structure for each language and ensure there are
    no *error*-level issues. Warnings are allowed.
    """
    problems: List[str] = []

    for lang, issues in _collect_schema_issues():
        error_messages = [
            f"{lang}::{issue.path}: {issue.message}"
            for issue in issues
            if issue.level.lower() == "error"
        ]
        if error_messages:
            problems.extend(error_messages)

    assert not problems, (
        "Lexicon schema validation failed:\n  - " + "\n  - ".join(problems)
    )


# ---------------------------------------------------------------------------
# Standalone CLI runner
# ---------------------------------------------------------------------------


def _print_human_report() -> int:
    """
    Run schema checks and print a human-readable report.

    Returns:
        0 if all lexica pass without errors, 1 otherwise.
    """
    if not os.path.isdir(LEXICON_DIR):
        print(f"❌ Lexicon directory not found: {LEXICON_DIR}")
        return 1

    langs = available_languages()
    if not langs:
        print(f"❌ No *_lexicon.json files found in {LEXICON_DIR}")
        return 1

    print(f"📚 Found {len(langs)} lexicon(s): {', '.join(sorted(langs))}\n")

    all_ok = True
    for lang, issues in _collect_schema_issues():
        errors = [i for i in issues if i.level.lower() == "error"]
        warnings = [i for i in issues if i.level.lower() != "error"]

        if errors:
            all_ok = False
            print(f"❌ {lang}: {len(errors)} error(s), {len(warnings)} warning(s)")
            for issue in errors:
                print(f"    [ERROR] {issue.path}: {issue.message}")
            for issue in warnings:
                print(f"    [WARN ] {issue.path}: {issue.message}")
        else:
            if warnings:
                print(f"⚠️  {lang}: 0 errors, {len(warnings)} warning(s)")
                for issue in warnings:
                    print(f"    [WARN ] {issue.path}: {issue.message}")
            else:
                print(f"✅ {lang}: schema OK (no issues)")

        print("")

    if all_ok:
        print("✅ All lexica passed schema checks without errors.")
        return 0
    else:
        print("❌ Some lexica have schema errors. See report above.")
        return 1


if __name__ == "__main__":
    import sys

    exit_code = _print_human_report()
    sys.exit(exit_code)

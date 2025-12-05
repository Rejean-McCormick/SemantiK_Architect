"""
Config extractor for Wikifunctions deployments.

Usage (from project root):

    python utils/config_extractor.py it
    python utils/config_extractor.py --list
    python utils/config_extractor.py --matrix data/morphology_configs/romance_grammar_matrix.json it

By default, the script will try the following matrix paths (in order):

    1. data/morphology_configs/romance_grammar_matrix.json
    2. data/romance_grammar_matrix.json   (legacy location)

It expects the matrix JSON to have the shape:

    {
        "languages": {
            "it": { ... payload ... },
            "es": { ... },
            ...
        },
        ...
    }

The extracted payload (for a given language code) is printed as compact JSON
suitable for pasting into a Wikifunctions function-call argument field.
"""

import argparse
import json
import os
import sys
from typing import Dict, Any, List, Optional

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Matrix loading
# ---------------------------------------------------------------------------

DEFAULT_MATRIX_CANDIDATES: List[str] = [
    os.path.join("data", "morphology_configs", "romance_grammar_matrix.json"),
    os.path.join("data", "romance_grammar_matrix.json"),  # legacy path
]


def _resolve_default_matrix_path() -> Optional[str]:
    """
    Try default candidate paths and return the first that exists.
    """
    for candidate in DEFAULT_MATRIX_CANDIDATES:
        abs_candidate = os.path.join(PROJECT_ROOT, candidate)
        if os.path.exists(abs_candidate):
            return abs_candidate
    return None


def load_matrix(matrix_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load the grammar matrix JSON.

    Args:
        matrix_path:
            Optional explicit path. If None, use the default resolution
            strategy over DEFAULT_MATRIX_CANDIDATES.

    Returns:
        Parsed JSON object.

    Exits with code 1 if the file cannot be found or parsed.
    """
    if matrix_path is None:
        matrix_path = _resolve_default_matrix_path()
        if matrix_path is None:
            print("❌ Error: No matrix file found.")
            print("   Tried:")
            for c in DEFAULT_MATRIX_CANDIDATES:
                print(f"   - {c}")
            sys.exit(1)
    else:
        # Make matrix_path relative to project root if it isn't absolute
        if not os.path.isabs(matrix_path):
            matrix_path = os.path.join(PROJECT_ROOT, matrix_path)

    try:
        with open(matrix_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: Matrix file not found at: {matrix_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Failed to parse JSON at: {matrix_path}")
        print(f"   {e}")
        sys.exit(1)

    if "languages" not in data or not isinstance(data["languages"], dict):
        print(
            f"❌ Error: Matrix file at '{matrix_path}' "
            f"does not contain a 'languages' dictionary."
        )
        sys.exit(1)

    return data


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------


def list_languages(matrix_data: Dict[str, Any]) -> None:
    """
    Print the list of available language codes and their names.
    """
    print("\n📚 Available languages in matrix:\n")
    langs = matrix_data.get("languages", {})
    for code, payload in sorted(langs.items()):
        name = payload.get("name", code)
        print(f"  {code:<5} → {name}")
    print("")


def extract_config(lang_code: str, matrix_data: Dict[str, Any]) -> None:
    """
    Extract and print the configuration payload for a given language code.
    """
    languages = matrix_data.get("languages", {})

    if lang_code not in languages:
        print(f"❌ Error: Language '{lang_code}' not found in Matrix.")
        print(f"   Available: {sorted(languages.keys())}")
        return

    payload = languages[lang_code]
    lang_name = payload.get("name", lang_code).upper()

    print(f"\n✂️  EXTRACTING CONFIGURATION FOR: {lang_name}")
    print("-" * 60)
    print("Copy the JSON below and paste it into the Wikifunctions argument field:")
    print("-" * 60)
    print(json.dumps(payload, ensure_ascii=False))
    print("-" * 60)
    print("✅ Done.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract per-language configuration chunks "
        "from the Romance Grammar Matrix."
    )
    parser.add_argument(
        "lang_code",
        nargs="?",
        help="Language code to extract (e.g. 'it', 'es', 'fr').",
    )
    parser.add_argument(
        "--matrix",
        "-m",
        dest="matrix_path",
        default=None,
        help="Explicit path to the matrix JSON file. "
        "If omitted, a default Romance matrix path is used.",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available language codes in the matrix and exit.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    # Ensure we run from project root context (for relative paths)
    os.chdir(PROJECT_ROOT)

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    matrix_data = load_matrix(args.matrix_path)

    if args.list:
        list_languages(matrix_data)
        return

    if not args.lang_code:
        print("Usage: python utils/config_extractor.py [lang_code]")
        print("       python utils/config_extractor.py --list")
        print("\nExamples:")
        print("  python utils/config_extractor.py it")
        print(
            "  python utils/config_extractor.py --matrix data/morphology_configs/romance_grammar_matrix.json es"
        )
        return

    extract_config(args.lang_code, matrix_data)


if __name__ == "__main__":
    main()

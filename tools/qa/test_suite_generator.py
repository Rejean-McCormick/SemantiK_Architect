# tools/qa/test_suite_generator.py
import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# --- Configuration ---
# Define paths relative to this script (tools/qa/test_suite_generator.py)
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MATRIX_FILE = DATA_DIR / "indices" / "everything_matrix.json"
OUTPUT_DIR = DATA_DIR / "tests" / "templates"

# Standard Test Cases (The "BioFrame" Smoke Test)
# Used to populate the CSVs with initial challenges for humans/AI to solve.
BASE_TEST_CASES = [
    # (ID Suffix, Name, Gender, Profession, Nationality)
    ("001", "Roberto", "m", "Actor", "Italian"),
    ("002", "Maria", "f", "Actor", "Italian"),
    ("003", "Enrico", "m", "Scientist", "Italian"),  # Test: S+Consonant checks
    ("004", "Sofia", "f", "Scientist", "Italian"),
    ("005", "Pablo", "m", "Painter", "Spanish"),
    ("006", "Frida", "f", "Painter", "Spanish"),
    ("007", "Jean", "m", "Writer", "French"),
    ("008", "Simone", "f", "Writer", "French"),
    ("009", "Dante", "m", "Poet", "Italian"),        # Test: Irregular forms
    ("010", "Marie", "f", "Physicist", "Polish"),
    ("011", "Albert", "m", "Physicist", "German"),
    ("012", "Ada", "f", "Programmer", "British"),
]

def load_everything_matrix() -> Dict[str, Any]:
    """Loads the central language registry."""
    if not MATRIX_FILE.exists():
        print(f"❌ Error: Matrix file not found at {MATRIX_FILE}")
        print("   Run 'python tools/everything_matrix/build_index.py' first.")
        sys.exit(1)
    
    with open(MATRIX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_csv_templates(target_langs: Optional[List[str]] = None) -> None:
    """
    Generates CSV testing templates for languages defined in the Everything Matrix.
    """
    matrix = load_everything_matrix()
    languages = matrix.get("languages", {})

    if not languages:
        print("⚠️  No languages found in the Matrix.")
        return

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📂 Output Directory: {OUTPUT_DIR}")

    count = 0
    for iso_code, lang_data in languages.items():
        # Filter if specific languages requested
        if target_langs and iso_code not in target_langs:
            continue

        meta = lang_data.get("meta", {})
        lang_name = meta.get("name", iso_code)
        
        # Skip skipped languages unless forced? 
        # For now, we generate templates for everything runnable.
        if lang_data.get("verdict", {}).get("build_strategy") == "SKIP":
            continue

        filename = OUTPUT_DIR / f"test_suite_{iso_code}.csv"

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header Columns — Aligned with QA Runner expectations
            writer.writerow([
                "Test_ID",
                "Frame_Type",
                "Name",
                "Gender",
                "Profession_ID",
                "Nationality_ID",
                "EXPECTED_TEXT" 
            ])

            # Write rows
            for suffix, name, gender, prof, nat in BASE_TEST_CASES:
                test_id = f"{iso_code.upper()}_BIO_{suffix}"
                
                # We use placeholder QIDs or English concepts as hints
                writer.writerow([
                    test_id,
                    "bio",
                    name,
                    gender,
                    f"Q_{prof.upper()}", # Placeholder for QID/Concept
                    f"Q_{nat.upper()}",  # Placeholder for QID/Concept
                    "" # Empty column for the Human/Judge to fill
                ])

        print(f"   ✅ Generated: {filename.name} ({lang_name})")
        count += 1

    print(f"\n✨ Done. Generated {count} templates.")

if __name__ == "__main__":
    # Optional CLI args: python tools/qa/test_suite_generator.py en fr
    targets = sys.argv[1:] if len(sys.argv) > 1 else None
    generate_csv_templates(targets)
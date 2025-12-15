# scripts\lexicon\missing_word_reporter.py
# scripts/lexicon/missing_word_reporter.py
# =========================================================================
# MISSING WORD REPORTER
#
# This script generates a coverage report for your multilingual lexicon.
# It answers the question: "Which concepts can't we express in Language X yet?"
#
# Workflow:
# 1. Fetches all abstract concepts (LexiconEntries) from the database.
# 2. Checks against the 'Translation' table for specific target languages.
# 3. Generates a summary CSV report identifying gaps.
# =========================================================================

import sys
import os
import csv
import logging
from typing import List, Dict, Set
from sqlalchemy.orm import joinedload

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from architect_http_api.db.session import get_db_session
from architect_http_api.db.models import LexiconEntry, Translation
from architect_http_api.gf.language_map import get_all_rgl_codes

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
OUTPUT_FILE = "lexicon_coverage_report.csv"
# Define 'Priority' languages to check explicitly in the summary
PRIORITY_LANGUAGES = ['eng', 'fra', 'deu', 'zho', 'ara', 'spa']

def generate_report():
    session = get_db_session()
    logger.info("Fetching lexicon data for analysis...")

    # Eager load translations to avoid N+1 query problems
    entries = session.query(LexiconEntry).options(joinedload(LexiconEntry.translations)).all()
    
    if not entries:
        logger.warning("No lexicon entries found in database. Run sync_rgl.py first.")
        return

    logger.info(f"Analyzing {len(entries)} abstract concepts...")

    # Data structure for report
    report_data = []
    
    # Calculate global stats
    total_entries = len(entries)
    language_stats: Dict[str, int] = {lang: 0 for lang in PRIORITY_LANGUAGES}

    for entry in entries:
        # Get set of languages this entry supports
        supported_langs = {t.language_code for t in entry.translations}
        
        # Calculate missing priority languages
        missing_priority = [lang for lang in PRIORITY_LANGUAGES if lang not in supported_langs]
        
        # Update stats
        for lang in PRIORITY_LANGUAGES:
            if lang in supported_langs:
                language_stats[lang] += 1

        # Add row to report
        report_data.append({
            "Function_ID": entry.gf_function_id,
            "Category": entry.category,
            "Wikidata_ID": entry.wikidata_id or "N/A",
            "Total_Languages": len(supported_langs),
            "Missing_Priority_Langs": ", ".join(missing_priority) if missing_priority else "None"
        })

    # --- WRITE CSV REPORT ---
    try:
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ["Function_ID", "Category", "Wikidata_ID", "Total_Languages", "Missing_Priority_Langs"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for row in report_data:
                writer.writerow(row)
        
        logger.info(f"Report generated successfully: {OUTPUT_FILE}")
        
    except IOError as e:
        logger.error(f"Failed to write report file: {e}")

    # --- PRINT SUMMARY TO CONSOLE ---
    print("\n=== LEXICON COVERAGE SUMMARY ===")
    print(f"Total Abstract Concepts: {total_entries}")
    print("-" * 30)
    print(f"{'Language':<10} | {'Count':<8} | {'Coverage':<8}")
    print("-" * 30)
    
    for lang in PRIORITY_LANGUAGES:
        count = language_stats[lang]
        percentage = (count / total_entries * 100) if total_entries > 0 else 0
        print(f"{lang:<10} | {count:<8} | {percentage:.1f}%")
    print("-" * 30)

    session.close()

if __name__ == "__main__":
    generate_report()
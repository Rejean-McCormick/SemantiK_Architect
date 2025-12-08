# scripts/lexicon/sync_rgl.py
# =========================================================================
# GF LEXICON SYNCHRONIZER
#
# This script performs the "Big Pull" from the compiled Grammar into the Database.
#
# Workflow:
# 1. Loads the compiled 'Wiki.pgf' via the GFEngine.
# 2. Identifies all abstract functions in the 'Vocabulary' module.
# 3. For each abstract word (e.g., 'apple_Entity'):
#    a. Ensures a master 'LexiconEntry' exists in the DB.
#    b. Iterates through ALL supported languages (eng, fra, zho, etc.).
#    c. Extracts the full inflection table (Singular, Plural, Cases, etc.).
#    d. Upserts a 'Translation' record with this linguistic data.
# =========================================================================

import sys
import os
import json
import logging
from typing import List, Dict, Set

# Add the project root to the path so we can import internal modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from architect_http_api.gf.engine import GFEngine, GFEngineError
from architect_http_api.gf.morphology import MorphologyHelper, MorphologyError
from architect_http_api.db.session import get_db_session
from architect_http_api.db.models import LexiconEntry, Translation

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
BATCH_SIZE = 50  # Commit to DB after processing this many words

def get_lexical_category(fun_name: str) -> str:
    """
    Infers the category from the function name suffix (convention used in Vocabulary.gf).
    E.g., 'apple_Entity' -> 'Entity', 'run_VP' -> 'Predicate'
    """
    if "_" in fun_name:
        return fun_name.split("_")[-1]
    return "Unknown"

def sync_lexicon():
    logger.info("Starting GF Lexicon Synchronization...")

    # 1. Initialize GF Engine
    try:
        engine = GFEngine.get_instance()
        logger.info(f"GF Engine loaded. PGF: {engine.pgf_path}")
    except GFEngineError as e:
        logger.error(f"Could not load GF Engine: {e}")
        return

    # 2. Get all target languages
    languages = engine.get_all_languages()
    logger.info(f"Target Languages found: {len(languages)} ({', '.join(languages[:5])}...)")

    # 3. Get all abstract functions (vocabulary)
    # We filter for functions that look like our vocabulary items (e.g., ending in _Entity, _Property)
    all_functions = engine.get_lexicon_function_names()
    lexical_functions = [f for f in all_functions if f.endswith(('_Entity', '_Property', '_VP', '_Mod'))]
    
    logger.info(f"Found {len(lexical_functions)} lexical items to sync.")

    session = get_db_session()
    count = 0

    try:
        for abstract_fun in lexical_functions:
            category = get_lexical_category(abstract_fun)
            
            # --- A. Upsert Abstract Entry ---
            lex_entry = session.query(LexiconEntry).filter_by(gf_function_id=abstract_fun).first()
            if not lex_entry:
                lex_entry = LexiconEntry(
                    gf_function_id=abstract_fun,
                    category=category,
                    source="RGL_SYNC"
                )
                session.add(lex_entry)
                session.flush() # Flush to get the ID
                logger.debug(f"Created new abstract entry: {abstract_fun}")
            
            # --- B. Sync Concrete Languages ---
            for concrete_name in languages:
                # Extract the ISO code from the concrete name (e.g., 'WikiEng' -> 'eng')
                # Assuming concrete names are formatted as "Wiki" + capitalized code
                if concrete_name.startswith("Wiki"):
                    lang_code = concrete_name[4:].lower() # WikiEng -> eng
                else:
                    # Fallback if concrete name doesn't match convention
                    lang_code = concrete_name 

                try:
                    # 1. Get Inflection Table (All forms)
                    # Note: We pass the standard ISO code to the helper, which handles mapping
                    inflections = MorphologyHelper.get_inflection_table(abstract_fun, lang_code)
                    
                    if not inflections:
                        continue

                    # 2. Determine the "Base Form" (usually the first entry or specific tag)
                    # For simplicity, we take the form of the first entry as the primary representation
                    base_form = inflections[0]['form']
                    
                    # 3. Upsert Translation Record
                    translation = session.query(Translation).filter_by(
                        lexicon_entry_id=lex_entry.id,
                        language_code=lang_code
                    ).first()

                    forms_json = json.dumps(inflections)

                    if translation:
                        # Update existing
                        if translation.forms_json != forms_json:
                            translation.base_form = base_form
                            translation.forms_json = forms_json
                            translation.updated_at = session.query(func.now()).scalar() # optional timestamp update
                    else:
                        # Create new
                        translation = Translation(
                            lexicon_entry_id=lex_entry.id,
                            language_code=lang_code,
                            base_form=base_form,
                            forms_json=forms_json
                        )
                        session.add(translation)

                except MorphologyError:
                    # Some words might be missing in specific languages (RGL gaps)
                    continue
                except Exception as e:
                    logger.warning(f"Error syncing {abstract_fun} for {lang_code}: {e}")

            count += 1
            if count % BATCH_SIZE == 0:
                session.commit()
                logger.info(f"Progress: Synced {count}/{len(lexical_functions)} words...")

        session.commit()
        logger.info("Lexicon Synchronization Completed Successfully.")

    except Exception as e:
        logger.error(f"Critical error during sync: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    sync_lexicon()
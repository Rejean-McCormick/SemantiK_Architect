# scripts/lexicon/wikidata_importer.py
# =========================================================================
# WIKIDATA IMPORTER & LINKER
#
# This script enriches the existing Lexicon database (populated by sync_rgl.py)
# by linking GF abstract functions to Wikidata Items (Q-IDs).
#
# Workflow:
# 1. Reads 'LexiconEntry' rows that lack a Wikidata ID.
# 2. Retrieves the English 'base_form' from the 'Translation' table.
# 3. Queries the Wikidata SPARQL endpoint to find matching Q-IDs.
# 4. Updates the database with the best candidate Q-ID.
#
# NOTE: This uses a heuristic (Label Match). Manual review is recommended
# for ambiguous terms (e.g., 'bank' -> Financial Bank vs. River Bank).
# =========================================================================

import sys
import os
import requests
import time
import logging
from typing import List, Dict, Optional, Tuple
from sqlalchemy import or_

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from architect_http_api.db.session import get_db_session
from architect_http_api.db.models import LexiconEntry, Translation

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
BATCH_SIZE = 20  # Number of labels to query at once (SPARQL limits apply)
USER_AGENT = "AbstractWikiArchitect/1.0 (mailto:your_email@example.com)"

def fetch_wikidata_ids(labels: List[str]) -> Dict[str, str]:
    """
    Queries Wikidata for a batch of English labels and returns the likely Q-ID.
    Returns: Dict { "apple": "Q312", "dog": "Q144", ... }
    """
    if not labels:
        return {}
    
    # Construct a VALUES clause for batch querying
    # Escaping quotes in labels is important
    values_str = " ".join([f'"{l.replace("`", "").replace('"', "")}"@en' for l in labels])
    
    query = f"""
    SELECT ?label ?item WHERE {{
      VALUES ?label {{ {values_str} }}
      ?item rdfs:label ?label .
      ?item wdt:P31 ?instance . 
      # Optimization: Filter for common concepts (Taxon, Object, Concept)
      # to avoid obscure matches (like a random street named 'Apple').
      # This is heuristic and can be adjusted.
      FILTER(
        ?instance = wd:Q16521 || # Taxon (animal/plant)
        ?instance = wd:Q5 ||     # Human
        ?instance = wd:Q488383 || # Object
        ?instance = wd:Q7020 ||  # Musical instrument
        ?instance = wd:Q223557 || # Physical object
        ?instance = wd:Q151885    # Concept
      ) 
    }}
    LIMIT 100
    """

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    
    try:
        response = requests.get(WIKIDATA_SPARQL_URL, params={'format': 'json', 'query': query}, headers=headers)
        if response.status_code != 200:
            logger.error(f"SPARQL Error {response.status_code}: {response.text}")
            return {}
            
        data = response.json()
        results = {}
        
        for binding in data['results']['bindings']:
            label = binding['label']['value']
            qid = binding['item']['value'].split('/')[-1] # Extract 'Q312' from URL
            
            # Simple disambiguation: taking the first result provided by Wikidata
            # (which is often sorted by relevance/sitelinks).
            if label not in results:
                results[label] = qid
                
        return results

    except Exception as e:
        logger.error(f"Request failed: {e}")
        return {}


def run_importer():
    session = get_db_session()
    
    # 1. Find LexiconEntries that have an English translation but NO Wikidata ID
    #    (Assuming LexiconEntry has a 'wikidata_id' column or 'metadata' field)
    #    We check Translation for language_code='eng' or 'en'
    
    logger.info("Fetching unlinked lexicon entries...")
    
    # This query joins LexiconEntry and Translation to find candidates
    candidates = (
        session.query(LexiconEntry, Translation.base_form)
        .join(Translation, LexiconEntry.id == Translation.lexicon_entry_id)
        .filter(Translation.language_code.in_(['eng', 'en']))
        .filter(or_(LexiconEntry.wikidata_id == None, LexiconEntry.wikidata_id == ''))
        .all()
    )
    
    logger.info(f"Found {len(candidates)} entries needing Wikidata links.")
    
    # Process in batches
    for i in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[i : i + BATCH_SIZE]
        
        # Prepare labels for query
        # batch is list of tuples (LexiconEntry, base_form)
        label_map = {entry.id: base_form for entry, base_form in batch}
        unique_labels = list(set(label_map.values()))
        
        logger.info(f"Querying batch {i//BATCH_SIZE + 1} ({len(unique_labels)} labels)...")
        
        # 2. Fetch from Wikidata
        wikidata_results = fetch_wikidata_ids(unique_labels)
        
        # 3. Update Database
        updates_count = 0
        for entry, base_form in batch:
            if base_form in wikidata_results:
                qid = wikidata_results[base_form]
                entry.wikidata_id = qid
                updates_count += 1
                logger.debug(f"Linked {entry.gf_function_id} ('{base_form}') -> {qid}")
        
        session.commit()
        logger.info(f"Updated {updates_count} entries in this batch.")
        
        # Be nice to the API
        time.sleep(1)

    session.close()
    logger.info("Wikidata Import Completed.")

if __name__ == "__main__":
    run_importer()
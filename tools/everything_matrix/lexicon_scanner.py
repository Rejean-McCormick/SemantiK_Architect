# tools/everything_matrix/lexicon_scanner.py
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Setup Logging
logger = logging.getLogger(__name__)

# v2.1 Maturity Targets (Score of 10)
TARGETS = {
    "core": 150,      # "Glue" words needed for basic sentences
    "conc": 500,      # Domain words needed for specific topics
    "bio_min": 50     # Entities needed to act as a Biography Generator
}

def scan_lexicon_health(lang_code: str, data_dir: Path) -> Dict[str, float]:
    """
    Performs a Deep-Tissue scan of Zone B (Lexicon) and Zone C (Application).
    
    Args:
        lang_code (str): ISO 639-3 code (e.g., 'fra').
        data_dir (Path): Path to 'data/lexicon'.
        
    Returns:
        dict: Normalized scores (0.0 - 10.0) for:
              [Zone B] SEED, CONC, WIDE, SEM
              [Zone C] PROF, ASST, ROUT
    """
    # Initialize Stats with empty values
    stats = {
        # Zone B: Data
        "SEED": 0.0, "CONC": 0.0, "WIDE": 0.0, "SEM": 0.0,
        # Zone C: Application
        "PROF": 0.0, "ASST": 0.0, "ROUT": 0.0
    }

    # Resolve path (Handle potential 2-letter vs 3-letter folders if necessary)
    # V2 Standard is strict ISO-639-3, but we check existence safely.
    lang_path = data_dir / lang_code
    if not lang_path.exists():
        # Fallback for legacy 2-letter codes (e.g., 'es' instead of 'spa')
        if len(lang_code) == 3:
            legacy_path = data_dir / lang_code[:2]
            if legacy_path.exists():
                lang_path = legacy_path
            else:
                return stats # Path not found, return zeros
        else:
            return stats

    total_entries = 0
    qid_entries = 0

    # --- SCAN SHARDS (Zone B & C) ---

    # 1. Core Vocabulary (SEED) -> core.json
    core_file = lang_path / "core.json"
    if core_file.exists():
        data = _safe_load(core_file)
        count = len(data)
        # Score calculation: Linear scale up to target
        stats["SEED"] = min(10.0, round((count / TARGETS["core"]) * 10, 1))
        total_entries += count
        qid_entries += _count_qids(data)

    # 2. Domain Concepts (CONC) -> people.json
    people_file = lang_path / "people.json"
    if people_file.exists():
        data = _safe_load(people_file)
        count = len(data)
        stats["CONC"] = min(10.0, round((count / TARGETS["conc"]) * 10, 1))
        
        # Zone C: Biography Readiness (PROF)
        # We need a minimum number of professions/nationalities to generate bios
        if count >= TARGETS["bio_min"]:
            stats["PROF"] = 1.0 # Boolean-like score (Ready)
        
        total_entries += count
        qid_entries += _count_qids(data)

    # 3. Wide Imports (WIDE) -> ../imports/{lang}_wide.csv
    # Check if a bulk CSV import exists in the staging area
    import_dir = data_dir.parent / "imports"
    wide_csv = import_dir / f"{lang_code}_wide.csv"
    
    if wide_csv.exists():
        stats["WIDE"] = 10.0
    elif (lang_path / "wide_import.json").exists():
         stats["WIDE"] = 10.0

    # 4. Semantic Alignment (SEM)
    # Percentage of total entries that have a Wikidata QID
    if total_entries > 0:
        stats["SEM"] = min(10.0, round((qid_entries / total_entries) * 10, 1))

    # --- SCAN CONFIG (Zone C) ---

    # 5. Assistant Ready (ASST) -> dialog.json (Future)
    # Currently a placeholder for chat capabilities
    if (lang_path / "dialog.json").exists():
        stats["ASST"] = 1.0

    # 6. Routing/Topology (ROUT) -> topology_weights.json
    # Does the system know how to linearize this language (SVO/SOV)?
    # We check if we have enough data (SEED) to justify routing.
    # In V2.1, existence of core data implies routing is possible via Factory.
    if stats["SEED"] >= 2.0:
        stats["ROUT"] = 1.0

    return stats

def _safe_load(path: Path) -> Dict:
    """Safely loads JSON, returning empty dict on failure."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning(f"⚠️  Corrupt JSON found at {path}")
        return {}

def _count_qids(data: Dict) -> int:
    """Counts entries containing a 'qid' field."""
    return sum(1 for entry in data.values() if isinstance(entry, dict) and "qid" in entry)

if __name__ == "__main__":
    # Test Stub for CLI execution
    import os
    test_root = Path(__file__).parent.parent.parent / "data" / "lexicon"
    print(f"Testing lexicon scan in: {test_root}")
    
    # Mock scan for 'eng' or 'fra'
    result = scan_lexicon_health("eng", test_root)
    print(json.dumps(result, indent=2))
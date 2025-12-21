import os
import json
import logging
import glob

# Setup Logging
logger = logging.getLogger(__name__)

# Standard domains defined in Lexicon Architecture
DOMAINS = ["core", "people", "science", "geography"]

def resolve_lexicon_path(iso_code, root_dir):
    """
    Resolves the directory path, handling the mismatch between 
    ISO-639-3 (eng, fra) and ISO-639-1 (en, fr) often found in data folders.
    """
    # Try exact match (3-letter)
    path_3 = os.path.join(root_dir, iso_code)
    if os.path.isdir(path_3):
        return path_3
    
    # Try 2-letter prefix (if applicable)
    if len(iso_code) == 3:
        path_2 = os.path.join(root_dir, iso_code[:2])
        if os.path.isdir(path_2):
            return path_2
            
    return None

def audit_lexicon(iso_code, lexicon_root):
    """
    Audits the vocabulary depth for a specific language.
    Called by build_index.py.
    
    Args:
        iso_code (str): 'eng'
        lexicon_root (str): '/path/to/data/lexicon'
        
    Returns:
        dict: {
            "seed_score": int (0-10),
            "wide_score": int (0-10),
            "total_count": int,
            "domains": ["core", "people"]
        }
    """
    lang_path = resolve_lexicon_path(iso_code, lexicon_root)
    
    stats = {
        "seed_score": 0,
        "wide_score": 0,
        "total_count": 0,
        "domains_present": []
    }

    if not lang_path:
        return stats

    # 1. Audit Semantic Domains (JSON Shards)
    # ----------------------------------------
    total_words = 0
    valid_domains = 0
    
    for domain in DOMAINS:
        file_path = os.path.join(lang_path, f"{domain}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    count = len(data)
                    if count > 0:
                        total_words += count
                        stats["domains_present"].append(domain)
                        valid_domains += 1
            except (json.JSONDecodeError, OSError):
                logger.warning(f"⚠️  {iso_code}: Corrupt JSON in {domain}.json")

    stats["total_count"] = total_words

    # 2. Calculate Seed Score (Zone B Readiness)
    # ----------------------------------------
    # Score 0: No data
    # Score 3: Empty files
    # Score 5: Minimal Core (>10 words)
    # Score 8: Core + Bio (>50 words)
    # Score 10: Rich Vocabulary (>200 words)
    
    if total_words == 0:
        stats["seed_score"] = 0
    elif total_words < 10:
        stats["seed_score"] = 3
    elif "core" in stats["domains_present"] and total_words >= 10:
        if total_words > 200:
            stats["seed_score"] = 10
        elif "people" in stats["domains_present"] and total_words > 50:
            stats["seed_score"] = 8
        else:
            stats["seed_score"] = 5
    else:
        stats["seed_score"] = 3  # Has files but missing 'core' is critical

    # 3. Audit Wide Imports (CSV / Raw)
    # ----------------------------------------
    # Check for bulk imports (e.g., 'data/imports/eng_wide.csv')
    # Assuming imports dir is sibling to lexicon dir (standard structure)
    imports_dir = os.path.join(os.path.dirname(lexicon_root), "imports")
    
    wide_files = [
        os.path.join(imports_dir, f"{iso_code}_wide.csv"),
        os.path.join(lang_path, "wide_import.json")
    ]
    
    for wf in wide_files:
        if os.path.exists(wf):
            stats["wide_score"] = 10
            break

    return stats

if __name__ == "__main__":
    # Test Stub
    test_root = os.path.join(os.path.dirname(__file__), "../../data/lexicon")
    print(f"Testing lexicon scan in: {test_root}")
    # Mock a check for 'eng'
    print(json.dumps(audit_lexicon("eng", test_root), indent=2))
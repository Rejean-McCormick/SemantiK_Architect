# tools\everything_matrix\rgl_auditor.py
import os
import logging

# Setup Logging
logger = logging.getLogger(__name__)

# Essential RGL Modules required for a "High Road" strategy
REQUIRED_MODULES = [
    "Cat",        # Categorization (Nouns, Verbs definitions)
    "Noun",       # Noun morphology (Inflection)
    "Grammar",    # The structural core
    "Paradigms",  # The constructor API (mkN, mkV)
    "Syntax"      # High-level sentence building
]

def detect_rgl_suffix(path):
    """
    Scans a directory to find the RGL 3-letter suffix (e.g. 'Fre' in 'CatFre.gf').
    Returns 'Fre', 'Eng', etc., or None if not found.
    """
    try:
        files = os.listdir(path)
        for f in files:
            if f.startswith("Cat") and f.endswith(".gf"):
                # Extract 'Fre' from 'CatFre.gf'
                return f[3:-3]
    except FileNotFoundError:
        return None
    return None

def audit_language(iso_code, path):
    """
    Physically inspects the RGL folder to determine maturity.
    Called by build_index.py.
    
    Args:
        iso_code (str): 'fra', 'eng'
        path (str): '/path/to/gf-rgl/src/french'
        
    Returns:
        dict: {
            "score": int (0-10),
            "blocks": { "rgl_cat": 10, "rgl_noun": 0 ... }
        }
    """
    suffix = detect_rgl_suffix(path)
    
    if not suffix:
        logger.warning(f"⚠️  {iso_code}: Could not detect RGL suffix in {path}")
        return {
            "score": 0,
            "blocks": {k: 0 for k in ["rgl_cat", "rgl_noun", "rgl_grammar", "rgl_paradigms", "rgl_syntax"]}
        }

    blocks = {}
    present_count = 0
    
    # Check for physical file existence
    for module in REQUIRED_MODULES:
        filename = f"{module}{suffix}.gf"
        
        # Check standard path
        file_path = os.path.join(path, filename)
        
        # Check 'api' subfolder for Syntax/Paradigms often hidden there
        api_path = os.path.join(os.path.dirname(path), "api", filename)
        
        if os.path.exists(file_path) or os.path.exists(api_path):
            blocks[f"rgl_{module.lower()}"] = 10
            present_count += 1
        else:
            blocks[f"rgl_{module.lower()}"] = 0
            # logger.debug(f"    Missing: {filename}")

    # Scoring Logic
    # 5 modules * 2 points each = 10
    score = (present_count / len(REQUIRED_MODULES)) * 10
    
    # Bonus: Check for extra stability (Abstract file existence)
    # This is a heuristic for "Tier 1" stability
    return {
        "score": round(score, 1),
        "blocks": blocks,
        "suffix": suffix
    }

if __name__ == "__main__":
    # Test stub
    print("Running Auditor Test on current directory...")
    print(audit_language("test", "."))
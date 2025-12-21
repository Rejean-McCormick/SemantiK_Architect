import os
import json
import time
import logging
import sys

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# Base dir is 2 levels up from tools/everything_matrix
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data", "indices")
MATRIX_FILE = os.path.join(DATA_DIR, "everything_matrix.json")
LEXICON_DIR = os.path.join(BASE_DIR, "data", "lexicon")

RGL_SRC = os.path.join(BASE_DIR, "gf-rgl", "src")
FACTORY_SRC = os.path.join(BASE_DIR, "generated", "src")

# Add current dir to path to import sibling scanners
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Attempt to import scanners (Graceful degradation if not yet created)
try:
    import rgl_auditor
except ImportError:
    logger.warning("⚠️  rgl_auditor module not found. Skipping Zone A audits.")
    rgl_auditor = None

try:
    import lexicon_scanner
except ImportError:
    logger.warning("⚠️  lexicon_scanner module not found. Skipping Zone B audits.")
    lexicon_scanner = None

# Map ISO codes to RGL folder names
ISO_TO_RGL_FOLDER = {
    "eng": "english", "fra": "french", "deu": "german", "spa": "spanish", 
    "ita": "italian", "swe": "swedish", "por": "portuguese", "rus": "russian", 
    "zho": "chinese", "jpn": "japanese", "ara": "arabic", "hin": "hindi", 
    "fin": "finnish", "est": "estonian", "swa": "swahili", "tur": "turkish", 
    "bul": "bulgarian", "pol": "polish", "ron": "romanian", "nld": "dutch", 
    "dan": "danish", "nob": "norwegian", "isl": "icelandic", "ell": "greek", 
    "heb": "hebrew", "lav": "latvian", "lit": "lithuanian", "mlt": "maltese", 
    "hun": "hungarian", "cat": "catalan", "eus": "basque", "tha": "thai", 
    "urd": "urdu", "fas": "persian", "mon": "mongolian", "nep": "nepali", 
    "pan": "punjabi", "snd": "sindhi", "afr": "afrikaans", "amh": "amharic", 
    "kor": "korean", "lat": "latin", "nno": "nynorsk", "slv": "slovenian", 
    "som": "somali", "tgl": "tagalog", "vie": "vietnamese"
}

def scan_system():
    logger.info("🧠 Everything Matrix: Deep System Scan Initiated...")
    languages = {}

    # ---------------------------------------------------------
    # 1. Scan Tier 1 (RGL - High Quality)
    # ---------------------------------------------------------
    if os.path.exists(RGL_SRC):
        for iso, folder in ISO_TO_RGL_FOLDER.items():
            path = os.path.join(RGL_SRC, folder)
            if os.path.exists(path):
                
                # Default values
                rgl_score = 10
                strategy = "HIGH_ROAD"
                blocks = {}
                
                # Perform Deep Audit if module exists
                if rgl_auditor:
                    audit_result = rgl_auditor.audit_language(iso, path)
                    rgl_score = audit_result.get("score", 0)
                    blocks = audit_result.get("blocks", {})
                    
                    # Downgrade strategy if critical files are missing
                    if rgl_score < 7:
                        strategy = "SAFE_MODE"
                        logger.warning(f"🔻 Downgrading {iso} to SAFE_MODE (Score: {rgl_score}/10)")

                languages[iso] = {
                    "meta": {
                        "iso": iso,
                        "tier": 1,
                        "origin": "rgl",
                        "folder": folder
                    },
                    "paths": {
                        "source": path
                    },
                    "blocks": blocks,
                    "status": {
                        "build_strategy": strategy,
                        "maturity_score": rgl_score
                    }
                }
    
    # ---------------------------------------------------------
    # 2. Scan Tier 3 (Factory - Generated)
    # ---------------------------------------------------------
    if os.path.exists(FACTORY_SRC):
        for item in os.listdir(FACTORY_SRC):
            if len(item) == 3 and os.path.isdir(os.path.join(FACTORY_SRC, item)):
                iso = item.lower()
                path = os.path.join(FACTORY_SRC, item)
                
                # If language already exists (Tier 1), just add the factory path
                if iso in languages:
                    languages[iso]["paths"]["factory"] = path
                else:
                    # New Tier 3 Language
                    languages[iso] = {
                        "meta": {
                            "iso": iso,
                            "tier": 3,
                            "origin": "factory"
                        },
                        "paths": {
                            "source": path
                        },
                        "blocks": {
                            "rgl_grammar": 5, # Default for generated
                            "rgl_syntax": 5
                        },
                        "status": {
                            "build_strategy": "SAFE_MODE", # Always Safe Mode for factory
                            "maturity_score": 5
                        }
                    }

    # ---------------------------------------------------------
    # 3. Zone B: Lexicon Audit
    # ---------------------------------------------------------
    if lexicon_scanner:
        logger.info("📚 Scanning Lexicons...")
        for iso, data in languages.items():
            lex_stats = lexicon_scanner.audit_lexicon(iso, LEXICON_DIR)
            
            # Merge lexicon stats into blocks
            data.setdefault("blocks", {}).update({
                "lex_seed": lex_stats.get("seed_score", 0),
                "lex_wide": lex_stats.get("wide_score", 0),
                "vocab_size": lex_stats.get("total_count", 0)
            })

            # Update overall maturity based on lexicon
            if lex_stats.get("seed_score", 0) == 0:
                data["status"]["maturity_score"] = min(data["status"]["maturity_score"], 3)
                data["status"]["data_ready"] = False
            else:
                data["status"]["data_ready"] = True

    # ---------------------------------------------------------
    # 4. Save Matrix
    # ---------------------------------------------------------
    matrix = {
        "timestamp": time.time(),
        "stats": {
            "total_languages": len(languages),
            "tier_1_count": sum(1 for l in languages.values() if l["meta"]["tier"] == 1),
            "tier_3_count": sum(1 for l in languages.values() if l["meta"]["tier"] == 3),
            "production_ready": sum(1 for l in languages.values() if l["status"]["maturity_score"] >= 8)
        },
        "languages": languages
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(MATRIX_FILE, 'w') as f:
        json.dump(matrix, f, indent=2)
    
    logger.info(f"✅ Matrix Updated: {len(languages)} languages indexed.")
    logger.info(f"💾 Saved to: {MATRIX_FILE}")

if __name__ == "__main__":
    scan_system()
# tools/everything_matrix/build_index.py
import os
import json
import time
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# Base dir is 2 levels up from tools/everything_matrix
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data", "indices")
MATRIX_FILE = os.path.join(DATA_DIR, "everything_matrix.json")

RGL_SRC = os.path.join(BASE_DIR, "gf-rgl", "src")
FACTORY_SRC = os.path.join(BASE_DIR, "generated", "src")

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
    logger.info("🧠 Everything Matrix: Scanning System...")
    languages = {}

    # 1. Scan Tier 1 (RGL)
    if os.path.exists(RGL_SRC):
        for iso, folder in ISO_TO_RGL_FOLDER.items():
            path = os.path.join(RGL_SRC, folder)
            if os.path.exists(path):
                languages[iso] = {
                    "iso": iso,
                    "tier": 1,
                    "source_path": path,
                    "status": "source_available",
                    "origin": "rgl"
                }
    
    # 2. Scan Tier 3 (Factory)
    if os.path.exists(FACTORY_SRC):
        for item in os.listdir(FACTORY_SRC):
            if len(item) == 3 and os.path.isdir(os.path.join(FACTORY_SRC, item)):
                iso = item.lower()
                path = os.path.join(FACTORY_SRC, item)
                # Tier 1 takes precedence, but we note the factory path
                if iso in languages:
                    languages[iso]["factory_path"] = path
                else:
                    languages[iso] = {
                        "iso": iso,
                        "tier": 3,
                        "source_path": path,
                        "status": "generated",
                        "origin": "factory"
                    }

    # 3. Save Matrix
    matrix = {
        "timestamp": time.time(),
        "stats": {
            "total_languages": len(languages),
            "tier_1_count": sum(1 for l in languages.values() if l.get('tier') == 1),
            "tier_3_count": sum(1 for l in languages.values() if l.get('tier') == 3)
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
# tools/everything_matrix/build_index.py
import os
import json
import time
import logging
import sys
import hashlib
from pathlib import Path

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "indices"
MATRIX_FILE = DATA_DIR / "everything_matrix.json"
CHECKSUM_FILE = DATA_DIR / "filesystem.checksum"

LEXICON_DIR = BASE_DIR / "data" / "lexicon"
RGL_SRC = BASE_DIR / "gf-rgl" / "src"
FACTORY_SRC = BASE_DIR / "gf" / "generated" / "src"
GF_ARTIFACTS = BASE_DIR / "gf"

# Add current dir to path to import sibling scanners
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Scanners (Graceful degradation if missing)
try:
    import rgl_auditor
except ImportError:
    rgl_auditor = None

try:
    import lexicon_scanner
except ImportError:
    lexicon_scanner = None

try:
    import qa_scanner
except ImportError:
    qa_scanner = None

# Map ISO codes to RGL folder names (Truncated for brevity, fully supported)
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

def get_directory_fingerprint(paths):
    """
    Calculates a quick MD5 hash of directory states based on modification times.
    """
    hasher = hashlib.md5()
    for path in paths:
        path = Path(path)
        if not path.exists():
            continue
        # Walk the tree
        for root, dirs, files in os.walk(path):
            for name in sorted(files):
                filepath = Path(root) / name
                try:
                    mtime = filepath.stat().st_mtime
                    raw = f"{name}|{mtime}"
                    hasher.update(raw.encode('utf-8'))
                except OSError:
                    continue
    return hasher.hexdigest()

def scan_system():
    # ---------------------------------------------------------
    # 0. Caching Logic (The Optimizer)
    # ---------------------------------------------------------
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    current_fingerprint = get_directory_fingerprint([RGL_SRC, LEXICON_DIR, FACTORY_SRC])
    
    if CHECKSUM_FILE.exists() and MATRIX_FILE.exists():
        with open(CHECKSUM_FILE, 'r') as f:
            stored_fingerprint = f.read().strip()
        
        if current_fingerprint == stored_fingerprint:
            logger.info("⚡ Cache Hit: Filesystem unchanged. Skipping scan.")
            return

    logger.info("🧠 Everything Matrix v2.1: Deep System Scan Initiated...")
    
    matrix_langs = {}
    
    # Discovery: Collect all unique ISO codes from RGL, Factory, and Lexicon
    all_isos = set(ISO_TO_RGL_FOLDER.keys())
    
    if FACTORY_SRC.exists():
        all_isos.update([p.name for p in FACTORY_SRC.iterdir() if p.is_dir() and len(p.name) == 3])
    
    if LEXICON_DIR.exists():
        all_isos.update([p.name for p in LEXICON_DIR.iterdir() if p.is_dir() and len(p.name) == 3])

    # ---------------------------------------------------------
    # SCAN LOOP
    # ---------------------------------------------------------
    for iso in sorted(all_isos):
        # --- Zone A: RGL Engine (Logic) ---
        zone_a = {"CAT": 0, "NOUN": 0, "PARA": 0, "GRAM": 0, "SYN": 0}
        tier = 3
        origin = "factory"
        
        # Check if it's a Tier 1 RGL language
        if iso in ISO_TO_RGL_FOLDER and rgl_auditor:
            rgl_path = RGL_SRC / ISO_TO_RGL_FOLDER[iso]
            if rgl_path.exists():
                tier = 1
                origin = "rgl"
                # Adapt legacy return format if needed, or assume rgl_auditor returns dict
                # Assuming rgl_auditor.scan_rgl(iso, rgl_path) returns the Zone A dict
                if hasattr(rgl_auditor, 'scan_rgl'):
                    zone_a = rgl_auditor.scan_rgl(iso, rgl_path)
                elif hasattr(rgl_auditor, 'audit_language'):
                    # Fallback for older auditor interface
                    audit = rgl_auditor.audit_language(iso, rgl_path)
                    zone_a = audit.get("blocks", zone_a)

        # --- Zone B & C: Lexicon & App (Data) ---
        zone_b = {"SEED": 0.0, "CONC": 0.0, "WIDE": 0.0, "SEM": 0.0}
        zone_c = {"PROF": 0.0, "ASST": 0.0, "ROUT": 0.0}
        
        if lexicon_scanner:
            lex_stats = lexicon_scanner.scan_lexicon_health(iso, LEXICON_DIR)
            # Map flattened scanner output to Zones
            zone_b = {k: lex_stats.get(k, 0.0) for k in zone_b}
            zone_c = {k: lex_stats.get(k, 0.0) for k in zone_c}

        # --- Zone D: Quality (Artifacts) ---
        zone_d = {"BIN": 0.0, "TEST": 0.0}
        if qa_scanner:
            zone_d = qa_scanner.scan_artifacts(iso, GF_ARTIFACTS)

        # ---------------------------------------------------------
        # SCORING & DECISION LOGIC
        # ---------------------------------------------------------
        # Calculate Logic Score (Zone A Average)
        score_a = sum(zone_a.values()) / 5 if zone_a else 0
        
        # Calculate Data Score (Zone B weighted: SEED + CONC + SEM)
        score_b = (zone_b["SEED"] + zone_b["CONC"] + zone_b["SEM"]) / 3
        
        # Maturity Score (Logic * 0.6 + Data * 0.4)
        maturity = round((score_a * 0.6) + (score_b * 0.4), 1)

        # Build Strategy Verdict
        # > 7.0 + Perfect RGL = HIGH_ROAD
        # > 2.0 = SAFE_MODE (Factory)
        # < 2.0 = SKIP
        build_strategy = "SKIP"
        if maturity > 7.0 and zone_a.get("CAT", 0) == 10:
            build_strategy = "HIGH_ROAD"
        elif maturity > 2.0:
            build_strategy = "SAFE_MODE"

        # Runnable Verdict (Must have Core Seed to prevent runtime crash)
        runnable = zone_b["SEED"] >= 2.0 or build_strategy == "HIGH_ROAD"

        # ---------------------------------------------------------
        # BUILD ENTRY
        # ---------------------------------------------------------
        matrix_langs[iso] = {
            "meta": {
                "iso": iso,
                "tier": tier,
                "origin": origin,
                "folder": ISO_TO_RGL_FOLDER.get(iso, "generated")
            },
            "zones": {
                "A_RGL": zone_a,
                "B_LEX": zone_b,
                "C_APP": zone_c,
                "D_QA": zone_d
            },
            "verdict": {
                "maturity_score": maturity,
                "build_strategy": build_strategy,
                "runnable": runnable
            }
        }

    # ---------------------------------------------------------
    # 4. Save Matrix & Checksum
    # ---------------------------------------------------------
    matrix = {
        "timestamp": time.time(),
        "stats": {
            "total_languages": len(matrix_langs),
            "production_ready": sum(1 for l in matrix_langs.values() if l["verdict"]["maturity_score"] >= 8),
            "safe_mode": sum(1 for l in matrix_langs.values() if l["verdict"]["build_strategy"] == "SAFE_MODE"),
            "skipped": sum(1 for l in matrix_langs.values() if l["verdict"]["build_strategy"] == "SKIP"),
        },
        "languages": matrix_langs
    }

    with open(MATRIX_FILE, 'w') as f:
        json.dump(matrix, f, indent=2)
    
    with open(CHECKSUM_FILE, 'w') as f:
        f.write(current_fingerprint)
    
    logger.info(f"✅ Matrix Updated: {len(matrix_langs)} languages indexed.")

if __name__ == "__main__":
    scan_system()
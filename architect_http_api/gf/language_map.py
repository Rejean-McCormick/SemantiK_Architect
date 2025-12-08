# architect_http_api/gf/language_map.py
# =========================================================================
# LANGUAGE MAPPING: Centralized registry for converting language identifiers
#
# This module converts between:
# 1. Internal Z-Language IDs (used by your system/Wikifunctions)
# 2. ISO 639-1 (2-letter) codes (common public standard)
# 3. ISO 639-3 (3-letter) RGL codes (required by Grammatical Framework)
#
# Only the ISO 639-3 codes are guaranteed to be supported by the GF engine.
# =========================================================================

from typing import Dict, Optional

# --- LANGUAGE DATA MAPPING ---
# NOTE: This is an abbreviated dictionary. The production version must 
# include entries for all 300+ languages supported by your RGL build.

# Structure: { RGL (ISO 639-3) : { 'iso1': ISO 639-1, 'z_id': Z-ID } }
LANGUAGE_MAP: Dict[str, Dict[str, str]] = {
    "eng": {"iso1": "en", "z_id": "Z1002"},  # English
    "fra": {"iso1": "fr", "z_id": "Z1003"},  # French
    "deu": {"iso1": "de", "z_id": "Z1004"},  # German
    "spa": {"iso1": "es", "z_id": "Z1005"},  # Spanish
    "rus": {"iso1": "ru", "z_id": "Z1007"},  # Russian
    "zho": {"iso1": "zh", "z_id": "Z1008"},  # Chinese (Mandarin)
    "jpn": {"iso1": "ja", "z_id": "Z1009"},  # Japanese
    "arb": {"iso1": "ar", "z_id": "Z1011"},  # Arabic (Standard)
    "hin": {"iso1": "hi", "z_id": "Z1012"},  # Hindi
    "fin": {"iso1": "fi", "z_id": "Z1013"},  # Finnish
    "swe": {"iso1": "sv", "z_id": "Z1014"},  # Swedish
    "swa": {"iso1": "sw", "z_id": "Z1016"},  # Swahili
    # ... Add all 300+ RGL languages here ...
}

# --- REVERSE LOOKUP TABLES ---

# { ISO 639-1 : RGL (ISO 639-3) }
ISO1_TO_RGL_MAP: Dict[str, str] = {
    data['iso1']: rgl_code for rgl_code, data in LANGUAGE_MAP.items()
}

# { Z-ID : RGL (ISO 639-3) }
ZID_TO_RGL_MAP: Dict[str, str] = {
    data['z_id']: rgl_code for rgl_code, data in LANGUAGE_MAP.items()
}

# --- PUBLIC FUNCTIONS ---

def get_rgl_code(identifier: str) -> Optional[str]:
    """
    Converts any known identifier (ISO-1, Z-ID, or RGL itself) to the 
    required RGL (ISO 639-3) code for the GF Engine.
    
    Args:
        identifier: A language identifier (e.g., 'en', 'Z1002', 'fra').
        
    Returns:
        The 3-letter RGL code (e.g., 'eng') or None if not found.
    """
    if len(identifier) == 3 and identifier.lower() in LANGUAGE_MAP:
        # Already an RGL code
        return identifier.lower()
    
    if len(identifier) == 2 and identifier.lower() in ISO1_TO_RGL_MAP:
        # ISO 639-1 to RGL lookup
        return ISO1_TO_RGL_MAP[identifier.lower()]
    
    if identifier.upper().startswith('Z') and identifier.upper() in ZID_TO_RGL_MAP:
        # Z-ID to RGL lookup
        return ZID_TO_RGL_MAP[identifier.upper()]
        
    return None

def get_z_language(identifier: str) -> Optional[str]:
    """
    Converts any known identifier to the Z-ID.
    
    Args:
        identifier: A language identifier (e.g., 'en', 'fra', 'Z1002').
        
    Returns:
        The Z-ID (e.g., 'Z1002') or None if not found.
    """
    rgl_code = get_rgl_code(identifier)
    if rgl_code and rgl_code in LANGUAGE_MAP:
        return LANGUAGE_MAP[rgl_code]['z_id']
    return None

def get_iso1_code(identifier: str) -> Optional[str]:
    """
    Converts any known identifier to the ISO 639-1 (2-letter) code.
    
    Args:
        identifier: A language identifier (e.g., 'eng', 'Z1002', 'fr').
        
    Returns:
        The ISO 639-1 code (e.g., 'en') or None if not found.
    """
    rgl_code = get_rgl_code(identifier)
    if rgl_code and rgl_code in LANGUAGE_MAP:
        return LANGUAGE_MAP[rgl_code]['iso1']
    return None

def get_all_rgl_codes() -> List[str]:
    """Returns a list of all 3-letter RGL codes supported."""
    return list(LANGUAGE_MAP.keys())
# architect_http_api\logic\bridge\literals.py
# architect_http_api/logic/bridge/literals.py
# =========================================================================
# GF LITERAL CONVERTER: Handling Raw Data Types
#
# This module converts simple Z-Objects (Strings, Numbers) into their
# Grammatical Framework representations.
#
# Target GF Abstract Syntax:
#   mkLiteral "some string"
#
# Where 'mkLiteral' is defined in AbstractWiki as:
#   fun mkLiteral : Value -> Entity
# =========================================================================

import logging
from typing import Any, Dict, Union

# --- LOGGING SETUP ---
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# Z-Types that are considered literals
LITERAL_TYPES = {
    "Z6",   # String
    "Z40",  # Boolean (often rendered as string literal for now)
    "Z0"    # Null/Void (sometimes treated as empty string)
    # Add other primitive Z-types here (Integers, Dates, etc.)
}

def is_literal_type(z_type: str) -> bool:
    """Checks if a given Z-Type identifier represents a literal value."""
    return z_type in LITERAL_TYPES

def _escape_gf_string(raw_text: str) -> str:
    """
    Escapes a string for use in GF.
    GF strings are enclosed in double quotes. Quotes inside must be escaped.
    """
    if not isinstance(raw_text, str):
        raw_text = str(raw_text)
    
    # Escape backslashes first, then double quotes
    escaped = raw_text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'

def convert_literal(z_object: Union[Dict[str, Any], str, int, float]) -> str:
    """
    Converts a literal Z-Object or Python primitive into a GF 'mkLiteral' call.
    
    Args:
        z_object: A Z6 dictionary (e.g., {'Z1K1': 'Z6', 'Z6K1': 'Hello'}) 
                  or a raw primitive (e.g., "Hello", 42).
                  
    Returns:
        A GF AST string, e.g., 'mkLiteral "Hello"'
    """
    raw_value = ""

    # 1. Handle Python Primitives
    if isinstance(z_object, (str, int, float)):
        raw_value = str(z_object)

    # 2. Handle Z-Objects (Dictionaries)
    elif isinstance(z_object, dict):
        z_type = z_object.get("Z1K1")
        
        if z_type == "Z6":
            # Z6 Strings store value in Z6K1
            raw_value = z_object.get("Z6K1", "")
        
        elif z_type == "Z40":
            # Z40 Booleans usually store 'true'/'false' or mapped strings
            # For simplicity, we convert to string. 
            # (Ideally, specific boolean logic exists, but literals handle raw output)
            val = z_object.get("Z40K1")
            raw_value = "true" if val else "false"
            
        else:
            # Fallback for other literal types
            logger.warning(f"converting unknown literal type {z_type} to string.")
            raw_value = str(z_object)
            
    else:
        logger.warning(f"Unexpected input type for literal conversion: {type(z_object)}")
        raw_value = str(z_object)

    # 3. Format for GF
    # We wrap the raw string in quotes and apply the 'mkLiteral' constructor
    # defined in AbstractWiki.gf.
    gf_string_literal = _escape_gf_string(raw_value)
    return f"mkLiteral {gf_string_literal}"
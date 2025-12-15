# architect_http_api\logic\bridge\ast_utils.py
# architect_http_api/logic/bridge/ast_utils.py
# =========================================================================
# GF AST UTILITIES: Safe Tree Construction Helper
#
# This module provides low-level string manipulation functions to build
# Grammatical Framework Abstract Syntax Trees (ASTs) programmatically.
#
# It ensures:
# 1. Parentheses are balanced and applied correctly.
# 2. Function names are sanitized (no illegal characters).
# 3. Arguments are joined properly.
# =========================================================================

import re
import logging
from typing import List, Optional

# --- LOGGING SETUP ---
logger = logging.getLogger(__name__)

# --- CONSTANTS ---
# Regex for valid GF identifiers (alphanumeric + underscore)
VALID_ID_REGEX = re.compile(r'^[a-zA-Z0-9_]+$')

def sanitize_function_name(name: str) -> str:
    """
    Ensures a string is a valid GF identifier.
    Replaces illegal characters (spaces, dashes, etc.) with underscores.
    
    Args:
        name: The raw identifier (e.g., 'apple-Entity', 'Z401').
        
    Returns:
        A safe string (e.g., 'apple_Entity', 'Z401').
    """
    if not name:
        return "meta_UnknownFunction"
        
    # Check if already valid (fast path)
    if VALID_ID_REGEX.match(name):
        return name
        
    # Replace invalid chars with underscore
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    
    # GF identifiers cannot start with a number or underscore in some contexts,
    # but usually standard vocab functions are fine.
    # We strip leading underscores just in case.
    return safe_name.lstrip('_')

def wrap_gf_call(function_name: str, *args: str) -> str:
    """
    Constructs a GF function application string wrapped in parentheses.
    
    Format: (FunctionName arg1 arg2 ...)
    
    Args:
        function_name: The name of the GF function (e.g., 'mkFact').
        *args: The string representations of the arguments (already converted ASTs).
        
    Returns:
        The full AST string.
    """
    # Sanity check
    if not function_name:
        logger.warning("Attempted to wrap GF call with empty function name.")
        return "meta_MissingFunction"

    safe_func = sanitize_function_name(function_name)
    
    # Filter out empty/None arguments
    valid_args = [arg for arg in args if arg and arg.strip()]
    
    if not valid_args:
        # If no arguments, it's just the function/constant (e.g., 'apple_N')
        # Constants do not need parentheses.
        return safe_func
        
    # Join arguments with space
    args_str = " ".join(valid_args)
    
    # Wrap in parentheses: (Fun arg1 arg2)
    return f"({safe_func} {args_str})"

def is_valid_ast(ast_string: str) -> bool:
    """
    Basic validation to check if parens are balanced.
    Does not check actual grammar validity (that requires the PGF engine).
    """
    balance = 0
    for char in ast_string:
        if char == '(':
            balance += 1
        elif char == ')':
            balance -= 1
        if balance < 0:
            return False
    return balance == 0
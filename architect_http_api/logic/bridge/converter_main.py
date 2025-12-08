# architect_http_api/logic/bridge/converter_main.py
# =========================================================================
# Z-OBJECT TO GF CONVERTER (MAIN ENTRY POINT)
#
# This module serves as the primary bridge between Abstract Wikipedia Logic
# (Z-Objects) and the Grammatical Framework (GF).
#
# Responsibility:
# 1. Inspect the input Z-Object to determine its type (String, Ref, Function Call).
# 2. Recursively convert children/arguments.
# 3. Assemble the final GF Abstract Syntax Tree (AST) string.
# =========================================================================

import logging
from typing import Any, Dict, Union, Optional

from .literals import convert_literal, is_literal_type
from .construct_mappers import get_mapper_for_function
from .ast_utils import sanitize_function_name

# --- LOGGING SETUP ---
logger = logging.getLogger(__name__)

class ConversionError(Exception):
    """Raised when a Z-Object cannot be converted to GF."""
    pass

class ZToGFConverter:
    """
    Orchestrates the conversion of Z-Objects into GF Abstract Syntax Trees.
    """

    @staticmethod
    def convert(z_object: Any) -> str:
        """
        Main entry point. Recursively converts a Z-Object to a GF string.
        
        Args:
            z_object: A dictionary (Z-Object) or primitive (str/int for literals).
            
        Returns:
            A string representing the GF AST (e.g., "mkFact (apple_Entity) (red_Property)")
        """
        # 1. Handle Primitives (Raw strings/ints passed directly)
        if isinstance(z_object, (str, int, float)):
            # Treat raw strings as Z6 Strings for convenience
            return convert_literal(z_object)

        # 2. Validate Input
        if not isinstance(z_object, dict):
            logger.warning(f"Invalid Z-Object received: {type(z_object)}")
            return "empty_Entity" # Safe fallback

        # 3. Determine Z-Object Type (Z1K1)
        # Z1K1 usually holds the type identifier (e.g., "Z6", "Z9", "Z7")
        z_type = z_object.get("Z1K1")

        # --- CASE A: LITERALS (Z6 String, Numbers) ---
        if z_type == "Z6" or is_literal_type(z_type):
            return convert_literal(z_object)

        # --- CASE B: REFERENCES (Z9) ---
        # A Z9 is a pointer to another object. In the context of GF, 
        # this is usually a pointer to a specific vocabulary item (e.g., "apple_Entity").
        if z_type == "Z9":
            ref_id = z_object.get("Z9K1")
            # We assume the Z9 Key maps directly to our GF Function ID.
            # (The Lexicon Syncer ensures these exist in the DB and Grammar).
            return sanitize_function_name(ref_id)

        # --- CASE C: FUNCTION CALLS (Z7) ---
        # A Z7 represents a "Construction" or "Function Call" (e.g., "IsA(Apple, Fruit)").
        if z_type == "Z7":
            return ZToGFConverter._handle_function_call(z_object)

        # --- CASE D: TYPED LISTS (Z881) ---
        if z_type == "Z881":
            return ZToGFConverter._handle_list(z_object)

        # Fallback for unknown types
        logger.warning(f"Unknown Z-Type encountered: {z_type}")
        return "meta_UnknownType"

    @staticmethod
    def _handle_function_call(z_object: Dict[str, Any]) -> str:
        """
        Handles Z7 Function Calls (Constructions).
        Finds the specific mapper for the function and applies it.
        """
        # The function being called is usually in Z7K1
        # It might be a Z9 object (reference) or a direct string ID.
        function_ref = z_object.get("Z7K1")
        
        function_id = ""
        if isinstance(function_ref, dict) and function_ref.get("Z1K1") == "Z9":
             function_id = function_ref.get("Z9K1")
        elif isinstance(function_ref, str):
            function_id = function_ref
        
        if not function_id:
            raise ConversionError("Z7 Function Call missing function identifier (Z7K1).")

        # 1. Get the Mapper
        # The mapper knows how to translate "Z_IsA" into "mkIsAProperty arg1 arg2"
        mapper = get_mapper_for_function(function_id)
        
        if not mapper:
            logger.warning(f"No GF Mapper found for Z-Function: {function_id}")
            return "meta_UnsupportedConstruction"

        # 2. Extract Arguments
        # Z7 arguments are usually stored in generic keys like Z7K1, K2... 
        # or semantic keys defined by the function.
        # The mapper is responsible for knowing WHICH keys to look for.
        
        try:
            # We pass the converter itself so the mapper can recurse on arguments
            gf_ast = mapper(z_object, ZToGFConverter.convert)
            return gf_ast
        except Exception as e:
            logger.error(f"Error mapping function {function_id}: {e}")
            return "meta_MappingError"

    @staticmethod
    def _handle_list(z_object: Dict[str, Any]) -> str:
        """
        Handles Z881 Lists.
        Maps to GF List categories (e.g., BaseNP, ConsNP).
        """
        # Z881K1 usually defines the list content type
        # Z881K2 is the list of items
        items = z_object.get("Z881K2", [])
        
        if not items:
            return "BaseEntity" # Placeholder for empty list logic
            
        # Recursively convert all items
        converted_items = [ZToGFConverter.convert(item) for item in items]
        
        # Join them using a generic list constructor (simplified)
        # Real GF lists are recursive: ConsX a (ConsX b (BaseX c))
        # Here we assume a helper 'mkList' exists or simply return a sequence
        # For this implementation, we return a comma-separated string which 
        # assumes a helper like 'mkList : Entity -> Entity -> Entity' is not strict.
        
        # Ideally: convert [a,b,c] -> ConsEntity a (ConsEntity b (BaseEntity c))
        return ZToGFConverter._build_recursive_list(converted_items)

    @staticmethod
    def _build_recursive_list(items: list[str]) -> str:
        """Helper to build GF recursive lists (Cons/Base)."""
        if not items:
            return "" # Should be handled by caller
        
        if len(items) == 1:
            return f"(BaseEntity {items[0]})"
        
        head = items[0]
        tail = items[1:]
        return f"(ConsEntity {head} {ZToGFConverter._build_recursive_list(tail)})"

# Convenience function for external callers
def convert_z_object(z_object: Any) -> str:
    return ZToGFConverter.convert(z_object)
# architect_http_api/gf/morphology.py
# =========================================================================
# MORPHOLOGY UTILITIES: Inflection and Lemma Analysis
#
# This module provides tools to inspect the internal structure of words
# within the loaded grammar. It is primarily used to:
# 1. Generate inflection tables (e.g., singular/plural, tenses).
# 2. Analyze raw text to find potential matching abstract functions (lemmatization).
# =========================================================================

import pgf
from typing import List, Dict, Optional, Any
from .engine import GFEngine, GFEngineError

class MorphologyError(Exception):
    """Specific exception for morphological operations."""
    pass

class MorphologyHelper:
    """
    A helper class for accessing deep linguistic data from the PGF.
    It does not hold state itself but queries the singleton GFEngine.
    """

    @staticmethod
    def get_inflection_table(abstract_fun: str, lang_code: str) -> List[Dict[str, str]]:
        """
        Retrieves the full inflection table for a specific abstract function 
        (word) in a target language.
        
        Args:
            abstract_fun: The abstract function name (e.g., 'apple_N', 'run_V').
            lang_code: The RGL ISO 639-3 code (e.g., 'eng', 'fra').
            
        Returns:
            A list of dictionaries containing the form and its grammatical label.
            Example:
            [
                {'form': 'apple',  'label': 'sg indef nom'}, 
                {'form': 'apples', 'label': 'pl indef nom'},
                ...
            ]
        """
        engine = GFEngine.get_instance()
        
        # Access internal PGF object to get the concrete grammar
        if not engine._grammar:
            raise GFEngineError("Grammar is not loaded.")
            
        concrete_name = engine._get_concrete_name(lang_code)
        if concrete_name not in engine._grammar.languages:
            raise MorphologyError(f"Language '{lang_code}' unavailable.")
            
        concrete = engine._grammar.languages[concrete_name]
        
        try:
            # 1. Parse the abstract function as an expression
            expr = pgf.readExpr(abstract_fun)
            
            # 2. Use tabularLinearize to get all forms
            # This returns a list of (label, string) tuples
            raw_table = concrete.tabularLinearize(expr)
            
            # 3. Format the output
            results = []
            for label, form in raw_table:
                results.append({
                    "label": label,
                    "form": form
                })
            return results
            
        except pgf.HelperError:
            raise MorphologyError(f"Abstract function '{abstract_fun}' not found or invalid.")
        except Exception as e:
            raise MorphologyError(f"Failed to generate table: {e}")

    @staticmethod
    def analyze_text(text: str, lang_code: str) -> List[Dict[str, Any]]:
        """
        Attempts to reverse-engineer raw text back to its abstract function 
        (Lemmatization / Parsing).
        
        Args:
            text: The raw string (e.g., "apples").
            lang_code: The language of the text.
            
        Returns:
            A list of possible abstract matches.
            Example: [{'function': 'apple_N', 'cat': 'Entity', 'prob': 0.8}, ...]
        """
        engine = GFEngine.get_instance()
        if not engine._grammar:
            raise GFEngineError("Grammar not loaded.")

        concrete_name = engine._get_concrete_name(lang_code
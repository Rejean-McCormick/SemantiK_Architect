# tests/test_multilingual_generation.py
# =========================================================================
# INTEGRATION TEST: Multilingual Ninai Generation
#
# This test suite verifies the end-to-end pipeline:
# 1. Takes a Ninai Protocol Object (Recursive JSON).
# 2. Converts it to a GF Abstract Syntax Tree (AST) via NinaiToGFConverter.
# 3. Linearizes it into multiple languages using the GFGrammarEngine.
#
# It serves as the proof of concept for the "300 Languages" architecture.
# =========================================================================

import pytest
import os
import sys

# Add project root to path to ensure imports work during testing
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.adapters.engines.gf_wrapper import GFGrammarEngine
from app.adapters.converters.ninai_to_gf import NinaiToGFConverter
from app.core.domain.exceptions import DomainError

# --- FIXTURES ---

@pytest.fixture(scope="module")
def gf_engine():
    """
    Initializes the GF Engine once for the test module.
    Skips tests if the PGF file is not found (haven't run build script yet).
    """
    engine = GFGrammarEngine()
    if not engine.grammar:
        pytest.skip("Wiki.pgf not found or failed to load. Run build pipeline first.")
    return engine

@pytest.fixture(scope="module")
def converter():
    """
    Initializes the Ninai -> GF Converter.
    """
    return NinaiToGFConverter()

# --- HELPER ---
def linearize(engine, ast_expr, lang_code):
    """Helper to linearize a PGF Expression using the engine's loaded grammar."""
    # Resolve the concrete grammar name (e.g. 'eng' -> 'WikiEng')
    conc_name = engine._resolve_concrete_name(lang_code)
    if not conc_name:
        return f"[{lang_code} NOT FOUND]"
    
    concrete = engine.grammar.languages[conc_name]
    return concrete.linearize(ast_expr)

# --- TEST CASES ---

def test_engine_languages(gf_engine):
    """Verify that the engine loaded the expected languages."""
    # Use the async method or check internal property if available for testing
    langs = list(gf_engine.grammar.languages.keys())
    assert "WikiEng" in langs, "English concrete syntax (WikiEng) missing."
    
    print(f"\nLoaded Languages: {langs}")

def test_literal_generation(gf_engine, converter):
    """Test converting simple string literals."""
    # Ninai Protocol: Raw strings are literals
    ninai_input = "Hello World"
    
    # 1. Convert to AST (pgf.Expr)
    ast = converter.convert(ninai_input)
    # The string representation of the GF Expr for a literal is just the string in quotes
    assert str(ast) == '"Hello World"'
    
    # 2. Linearize (English)
    text = linearize(gf_engine, ast, "eng")
    assert "Hello World" in text

def test_copula_construction(gf_engine, converter):
    """
    Test: 'The apple is red'
    Uses Generic GF Constructors (RGL style) via Ninai Protocol.
    """
    # Ninai Protocol (Tree Structure)
    # Equivalent to: mkCl (mkNP (mkN "apple")) (mkAP (mkA "red"))
    ninai_obj = {
        "function": "mkCl",
        "args": [
            {
                "function": "mkNP",
                "args": [
                    {"function": "mkN", "args": ["apple"]}
                ]
            },
            {
                "function": "mkAP",
                "args": [
                    {"function": "mkA", "args": ["red"]}
                ]
            }
        ]
    }

    # 1. Convert to AST
    ast = converter.convert(ninai_obj)
    print(f"Generated AST: {ast}")
    
    # Check if AST structure contains key functions
    ast_str = str(ast)
    assert "mkCl" in ast_str
    assert "mkNP" in ast_str
    assert "apple" in ast_str

    # 2. Linearize - English
    text_en = linearize(gf_engine, ast, "eng")
    print(f"English: {text_en}")
    
    # RGL Linearization check (approximate, as determiners may vary)
    assert "apple" in text_en.lower()
    assert "red" in text_en.lower()

    # 3. Linearize - French (if available)
    if "WikiFra" in gf_engine.grammar.languages:
        text_fr = linearize(gf_engine, ast, "fra")
        print(f"French: {text_fr}")
        # Expect: "pomme" (apple), "rouge" (red)
        # Note: Requires lexicon alignment in PGF
        pass

def test_transitive_event(gf_engine, converter):
    """
    Test: 'The cat eats the fish'
    """
    ninai_obj = {
        "function": "mkCl",
        "args": [
            {
                "function": "mkNP",
                "args": [{"function": "mkN", "args": ["cat"]}]
            },
            {
                "function": "mkV2",
                "args": ["eat"]
            },
            {
                "function": "mkNP",
                "args": [{"function": "mkN", "args": ["fish"]}]
            }
        ]
    }

    ast = converter.convert(ninai_obj)
    print(f"Generated AST: {ast}")
    
    assert "mkV2" in str(ast)
    
    text_en = linearize(gf_engine, ast, "eng")
    print(f"English: {text_en}")
    
    assert "cat" in text_en.lower()
    assert "fish" in text_en.lower()
    # "eats" or "eat"
    assert "eat" in text_en.lower()

def test_error_handling(converter):
    """Test that invalid Ninai Objects raise strict errors."""
    invalid_obj = {
        "missing_function_key": "true",
        "args": []
    }
    
    with pytest.raises(ValueError) as excinfo:
        converter.convert(invalid_obj)
    
    assert "missing 'function' key" in str(excinfo.value)
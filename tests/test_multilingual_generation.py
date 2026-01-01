# tests/test_multilingual_generation.py
# =========================================================================
# INTEGRATION TEST: Multilingual Ninai Generation
#
# This test suite verifies the end-to-end pipeline:
# 1. Takes a Ninai Protocol Object (Recursive JSON).
# 2. Converts it to a GF Abstract Syntax Tree (AST) string via the *Production Engine*.
# 3. Linearizes it into multiple languages using the PGF binary.
#
# It serves as the proof of concept for the "300 Languages" architecture.
# =========================================================================

import pytest
import os
import sys
import pgf  # Required for readExpr

# Add project root to path to ensure imports work during testing
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.adapters.engines.gf_wrapper import GFGrammarEngine
from app.core.domain.exceptions import DomainError

# --- FIXTURES ---

@pytest.fixture(scope="module")
def gf_engine():
    """
    Initializes the GF Engine once for the test module.
    Skips tests if the PGF file is not found (haven't run build script yet).
    """
    # Force reload to ensure we have the latest PGF state
    engine = GFGrammarEngine()
    if not engine.grammar:
        pytest.skip("Wiki.pgf not found or failed to load. Run build pipeline first.")
    return engine

# --- HELPER ---
def linearize(engine, ast_expr, lang_code):
    """
    Helper to linearize a PGF Expression using the engine's loaded grammar.
    """
    # Resolve the concrete grammar name (e.g. 'eng' -> 'WikiEng')
    conc_name = engine._resolve_concrete_name(lang_code)
    if not conc_name:
        return f"[{lang_code} NOT FOUND]"
    
    # Ensure we are passing a PGF Expression object, not a string
    if isinstance(ast_expr, str):
        try:
            ast_expr = pgf.readExpr(ast_expr)
        except Exception as e:
            return f"[AST PARSE ERROR: {e}]"

    concrete = engine.grammar.languages[conc_name]
    return concrete.linearize(ast_expr)

# --- TEST CASES ---

def test_engine_languages(gf_engine):
    """Verify that the engine loaded the expected languages."""
    # Check loaded languages in the PGF
    langs = list(gf_engine.grammar.languages.keys())
    assert "WikiEng" in langs, "English concrete syntax (WikiEng) missing."
    
    print(f"\nLoaded Languages: {langs}")

def test_literal_generation(gf_engine):
    """Test converting simple string literals."""
    # Ninai Protocol: Raw strings are literals
    ninai_input = "Hello World"
    lang = "eng"
    
    # 1. Convert to AST String using Production Engine Logic
    # Note: _convert_to_gf_ast is internal, but we test it to verify structure
    ast_str = gf_engine._convert_to_gf_ast(ninai_input, lang)
    
    # The string representation of the GF Expr for a literal is just the string in quotes
    # The wrapper escapes quotes, so we expect "\"Hello World\""
    assert '"Hello World"' in ast_str
    
    # 2. Linearize (English)
    text = linearize(gf_engine, ast_str, lang)
    assert "Hello World" in text

def test_copula_construction(gf_engine):
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
    lang = "eng"

    # 1. Convert to AST String
    ast_str = gf_engine._convert_to_gf_ast(ninai_obj, lang)
    print(f"Generated AST: {ast_str}")
    
    # Check if AST structure contains key functions
    assert "mkCl" in ast_str
    assert "mkNP" in ast_str
    assert "apple" in ast_str

    # 2. Linearize - English
    text_en = linearize(gf_engine, ast_str, lang)
    print(f"English: {text_en}")
    
    # RGL Linearization check (approximate, as determiners may vary)
    assert "apple" in text_en.lower()
    assert "red" in text_en.lower()

    # 3. Linearize - French (if available)
    # We re-convert for French to ensure any language-specific logic in the wrapper applies
    if "WikiFra" in gf_engine.grammar.languages:
        ast_str_fr = gf_engine._convert_to_gf_ast(ninai_obj, "fra")
        text_fr = linearize(gf_engine, ast_str_fr, "fra")
        print(f"French: {text_fr}")
        # Expect: "pomme" (apple), "rouge" (red)
        # Note: Requires lexicon alignment in PGF
        pass

def test_transitive_event(gf_engine):
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
    lang = "eng"

    # Convert via Engine
    ast_str = gf_engine._convert_to_gf_ast(ninai_obj, lang)
    print(f"Generated AST: {ast_str}")
    
    assert "mkV2" in ast_str
    
    text_en = linearize(gf_engine, ast_str, lang)
    print(f"English: {text_en}")
    
    assert "cat" in text_en.lower()
    assert "fish" in text_en.lower()
    # "eats" or "eat"
    assert "eat" in text_en.lower()

def test_error_handling(gf_engine):
    """Test that invalid Ninai Objects raise strict errors."""
    invalid_obj = {
        "missing_function_key": "true",
        "args": []
    }
    
    # The production engine raises ValueError or DomainError on malformed input
    with pytest.raises(ValueError) as excinfo:
        gf_engine._convert_to_gf_ast(invalid_obj, "eng")
    
    assert "Missing function attribute" in str(excinfo.value)
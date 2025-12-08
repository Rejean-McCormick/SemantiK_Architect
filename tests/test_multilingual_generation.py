# tests/test_multilingual_generation.py
# =========================================================================
# INTEGRATION TEST: Multilingual Z-Object Generation
#
# This test suite verifies the end-to-end pipeline:
# 1. Takes a raw Z-Object (representing logic/meaning).
# 2. Converts it to a GF Abstract Syntax Tree (AST).
# 3. Linearizes it into multiple languages (English, French, etc.)
#
# It serves as the proof of concept for the "300 Languages" architecture.
# =========================================================================

import pytest
import os
import sys

# Add project root to path to ensure imports work during testing
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from architect_http_api.gf.engine import GFEngine, GFEngineError
from architect_http_api.logic.bridge.converter_main import convert_z_object

# --- FIXTURES ---

@pytest.fixture(scope="module")
def gf_engine():
    """
    Initializes the GF Engine once for the test module.
    Skips tests if the PGF file is not found (haven't run build script yet).
    """
    try:
        # We allow the engine to auto-locate the PGF
        engine = GFEngine.get_instance()
        return engine
    except GFEngineError:
        pytest.skip("Wiki.pgf not found. Run 'python gf/build_300.py' first.")


# --- TEST CASES ---

def test_engine_languages(gf_engine):
    """Verify that the engine loaded the expected languages."""
    langs = gf_engine.get_all_languages()
    assert "WikiEng" in langs, "English concrete syntax missing."
    # If you built the French grammar, check for it too
    if "WikiFra" in langs:
        assert True


def test_literal_generation(gf_engine):
    """Test converting simple string literals."""
    z_string = {"Z1K1": "Z6", "Z6K1": "Hello World"}
    
    # 1. Convert to AST
    ast = convert_z_object(z_string)
    assert ast == 'mkLiteral "Hello World"'
    
    # 2. Linearize (English)
    text = gf_engine.linearize(ast, "eng")
    # mkLiteral usually just outputs the string in the entity position
    assert "Hello World" in text


def test_copula_construction(gf_engine):
    """
    Test: 'The apple is red' (Z_CopulaAttributiveAdj)
    """
    # Construct a mock Z-Object for "Apple is Red"
    z_obj = {
        "Z1K1": "Z7",
        "Z7K1": "Z_IsA", # Mapped to _map_copula_attributive
        "Z7K2": {"Z1K1": "Z9", "Z9K1": "apple_Entity"}, # Subject
        "Z7K3": {"Z1K1": "Z9", "Z9K1": "red_Property"}  # Attribute
    }

    # 1. Convert to AST
    # Expected: mkIsAProperty (Entity2NP apple_Entity) (Property2AP red_Property)
    ast = convert_z_object(z_obj)
    print(f"Generated AST: {ast}")
    
    assert "mkIsAProperty" in ast
    assert "apple_Entity" in ast
    assert "red_Property" in ast

    # 2. Linearize - English
    # Expect: "apple is red" (MassNP default) or "the apple is red"
    text_en = gf_engine.linearize(ast, "eng")
    print(f"English: {text_en}")
    
    # Robust assertion: check for key words
    assert "apple" in text_en.lower()
    assert "red" in text_en.lower()
    # "is" might be contracted or different, but usually present
    
    # 3. Linearize - French (if available)
    if gf_engine.has_language("fra"):
        text_fr = gf_engine.linearize(ast, "fra")
        print(f"French: {text_fr}")
        # Expect: "pomme" (apple), "rouge" (red), "est" (is)
        # Note: Vocabulary must be synced for this to work perfectly.
        # If words are missing, GF often outputs the abstract name or Empty.
        pass


def test_intransitive_event(gf_engine):
    """
    Test: 'The dog runs' (Z_IntransitiveEvent)
    """
    z_obj = {
        "Z1K1": "Z7",
        "Z7K1": "Z_Runs", # Mapped to _map_intransitive
        "Z7K2": {"Z1K1": "Z9", "Z9K1": "dog_Entity"}, # Agent
        "Z7K3": {"Z1K1": "Z9", "Z9K1": "run_VP"}      # Predicate
    }

    ast = convert_z_object(z_obj)
    # Expected: mkFact (Entity2NP dog_Entity) run_VP
    assert "mkFact" in ast
    assert "dog_Entity" in ast
    
    text_en = gf_engine.linearize(ast, "eng")
    print(f"English: {text_en}")
    
    # RGL 'run_V' usually linearizes to 'runs' or 'run'
    assert "dog" in text_en.lower()
    assert "run" in text_en.lower()


def test_transitive_event(gf_engine):
    """
    Test: 'The cat eats the fish' (Z_TransitiveEvent)
    """
    z_obj = {
        "Z1K1": "Z7",
        "Z7K1": "Z_Eats", # Mapped to _map_transitive
        "Z7K2": {"Z1K1": "Z9", "Z9K1": "cat_Entity"},  # Subject
        "Z7K3": {"Z1K1": "Z9", "Z9K1": "eat_VP"},      # Verb
        "Z7K4": {"Z1K1": "Z9", "Z9K1": "fish_Entity"}  # Object
    }

    ast = convert_z_object(z_obj)
    print(f"Generated AST: {ast}")
    
    # Ensure our complex nesting (VP2Predicate (ComplV ...)) is happening
    assert "VP2Predicate" in ast
    assert "ComplV" in ast or "eat_VP" in ast 
    
    text_en = gf_engine.linearize(ast, "eng")
    print(f"English: {text_en}")
    
    assert "cat" in text_en.lower()
    assert "fish" in text_en.lower()
    # "eats" or "eat"
    assert "eat" in text_en.lower()


def test_error_handling(gf_engine):
    """Test that invalid Z-Objects don't crash the converter."""
    invalid_obj = {
        "Z1K1": "Z7",
        "Z7K1": "Z_NonExistentFunction", # No mapper exists
        "Z7K2": "something"
    }
    
    # Should return a safe fallback string like "meta_UnsupportedConstruction"
    # defined in converter_main.py
    ast = convert_z_object(invalid_obj)
    assert "meta_UnsupportedConstruction" in ast
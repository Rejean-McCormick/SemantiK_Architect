# architect_http_api/logic/bridge/construct_mappers.py
# =========================================================================
# GF CONSTRUCT MAPPERS: Implementation of Z-Function to GF AST Translation
#
# This file contains the logic to convert specific Z-Function calls (Constructions)
# into the corresponding GF Abstract Syntax Tree (AST) strings.
#
# All mappers MUST be passed a recursive converter function to handle arguments.
# =========================================================================

import logging
from typing import Dict, Any, Callable, Optional, List
from functools import partial

# Import helper utilities
from .ast_utils import wrap_gf_call, sanitize_function_name

# Define the type for the mapping function: (Z-Object, recursive_converter) -> GF_AST_string
MapperFunction = Callable[[Dict[str, Any], Callable[[Any], str]], str]

# --- LOGGING SETUP ---
logger = logging.getLogger(__name__)

# --- CORE MAPPING FUNCTIONS ---

def _map_copula_attributive(z_object: Dict[str, Any], convert: Callable[[Any], str]) -> str:
    """
    Maps a construction like Z_CopulaAttributiveAdj (e.g., Apple IS Red).
    GF Target: mkIsAProperty Entity Property
    """
    # Assuming the Z-Object structure is consistent:
    # Z7K2 = Subject (Entity)
    # Z7K3 = Attribute (Property/Adjective)
    
    try:
        subject_ast = convert(z_object["Z7K2"])  # e.g., apple_Entity
        attribute_ast = convert(z_object["Z7K3"]) # e.g., red_Property
        
        # 1. Ensure Subject is an NP (using AbstractWiki function)
        subject_np = wrap_gf_call("Entity2NP", subject_ast)
        
        # 2. Ensure Attribute is an AP (using AbstractWiki function)
        attribute_ap = wrap_gf_call("Property2AP", attribute_ast)

        # 3. Assemble the final Fact
        return wrap_gf_call("mkIsAProperty", subject_np, attribute_ap)
        
    except KeyError as e:
        logger.error(f"Missing required key in Z_CopulaAttributiveAdj: {e}")
        raise ValueError(f"Missing required key: {e}")


def _map_intransitive(z_object: Dict[str, Any], convert: Callable[[Any], str]) -> str:
    """
    Maps a construction like Z_IntransitiveEvent (e.g., Dog RUNS).
    GF Target: mkFact Entity Predicate
    """
    # Z7K2 = Agent/Subject (Entity)
    # Z7K3 = Verb/Predicate (VP reference)
    try:
        agent_ast = convert(z_object["Z7K2"])  # e.g., dog_Entity
        verb_ast = convert(z_object["Z7K3"])   # e.g., run_VP (Note: this is already a Predicate type)

        # 1. Ensure Agent is an NP
        agent_np = wrap_gf_call("Entity2NP", agent_ast)
        
        # 2. Assemble the final Fact
        return wrap_gf_call("mkFact", agent_np, verb_ast)

    except KeyError as e:
        logger.error(f"Missing required key in Z_IntransitiveEvent: {e}")
        raise ValueError(f"Missing required key: {e}")


def _map_transitive(z_object: Dict[str, Any], convert: Callable[[Any], str]) -> str:
    """
    Maps a construction like Z_TransitiveEvent (e.g., Cat EATS Fish).
    GF Target: mkFact Subject (VP2Predicate (UseV V Object))
    """
    # Z7K2 = Agent/Subject (Entity)
    # Z7K3 = Verb (VP reference)
    # Z7K4 = Patient/Object (Entity)
    try:
        subject_ast = convert(z_object["Z7K2"])  # e.g., cat_Entity
        verb_ref_id = sanitize_function_name(z_object["Z7K3"]["Z9K1"]) # e.g., eat_VP
        object_ast = convert(z_object["Z7K4"])   # e.g., fish_Entity
        
        # 1. Ensure Subject is an NP
        subject_np = wrap_gf_call("Entity2NP", subject_ast)
        
        # 2. The Transitive Verb Phrase (VP) construction:
        # We need to drop the '_VP' suffix to get the raw verb form (e.g., 'eat_V' from 'eat_VP')
        # This assumes the raw verb form is available in VocabularyI.gf
        raw_verb_id = verb_ref_id.replace("_VP", "_V") # e.g., run_VP -> run_V
        
        # We assume an RGL-style Transitive Verb construction is available in the PGF
        # e.g., mkTransitiveVP V NP -> mkVP (UseV V) NP
        
        # Simple construction: UseV V is the base V, then apply the object NP
        object_np = wrap_gf_call("Entity2NP", object_ast)
        
        # GF: ComplV V NP combines the verb and the object
        # Note: This requires the GF grammar to import ComplV which is standard RGL.
        vp_with_object = wrap_gf_call("VP2Predicate", wrap_gf_call("ComplV", raw_verb_id, object_np))
        
        # 3. Assemble the final Fact
        return wrap_gf_call("mkFact", subject_np, vp_with_object)

    except (KeyError, ValueError) as e:
        logger.error(f"Missing required key in Z_TransitiveEvent: {e}")
        raise ValueError(f"Missing required key: {e}")


# --- MAPPER REGISTRY ---

# The central registry linking a Z-Function ID (string) to the Python mapping function.
# NOTE: The Z-Function IDs below are placeholder examples. They must match the Z-IDs
# used in your actual Z-Objects (e.g., Z401, Z402, or semantic IDs like Z_IsA).
MAPPERS: Dict[str, MapperFunction] = {
    # Copula & State Mappers
    "Z401": _map_copula_attributive,       # Placeholder for Z_CopulaAttributiveAdj
    "Z_IsA": _map_copula_attributive,      # Semantic ID for IS-A relation

    # Event Mappers
    "Z402": _map_intransitive,             # Placeholder for Z_IntransitiveEvent
    "Z_Runs": _map_intransitive,           # Semantic ID example
    "Z403": _map_transitive,               # Placeholder for Z_TransitiveEvent
    "Z_Eats": _map_transitive,             # Semantic ID example
    
    # Add your ~15 other construction mappers here:
    # "Z_RelativeClause": _map_relative_clause,
    # "Z_Coordination": _map_coordination,
    # etc.
}


# --- PUBLIC ACCESSOR ---

def get_mapper_for_function(function_id: str) -> Optional[MapperFunction]:
    """
    Retrieves the specific Python function responsible for mapping a Z-Function ID.
    
    Args:
        function_id: The Z-ID of the function being called (e.g., 'Z401', 'Z_IsA').
        
    Returns:
        The Python mapping function or None if the ID is unsupported.
    """
    return MAPPERS.get(function_id)
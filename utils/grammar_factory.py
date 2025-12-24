import json
from pathlib import Path

# Load Topology Weights
ROOT_DIR = Path(__file__).parent.parent
CONFIG_PATH = ROOT_DIR / "data" / "config" / "topology_weights.json"

DEFAULT_WEIGHTS = {
    "SVO": {"nsubj": -10, "root": 0, "obj": 10},
    "SOV": {"nsubj": -10, "obj": -5, "root": 0},
    "VSO": {"root": -10, "nsubj": 0, "obj": 10},
    "VOS": {"root": -10, "obj": 5, "nsubj": 10},
    "OVS": {"obj": -10, "root": 0, "nsubj": 10},
    "OSV": {"obj": -10, "nsubj": -5, "root": 0}
}

# Simple registry for demonstration. In a real system, this comes from 'everything_matrix.json'
LANG_ORDERS = {
    "eng": "SVO", "fra": "SVO", "zul": "SVO", "spa": "SVO", "por": "SVO",
    "jpn": "SOV", "hin": "SOV", "kor": "SOV", "tur": "SOV", "que": "SOV",
    "gle": "VSO", "ara": "VSO" 
}

def load_weights():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return DEFAULT_WEIGHTS

def _build_linearization(components, weights):
    """
    Sorts components by topological weight and joins them with '++'.
    components: List of dicts {'code': str, 'role': str}
    weights: Dict of {role: int}
    """
    # Sort by the weight of the role (default to 0 if unknown)
    components.sort(key=lambda x: weights.get(x["role"], 0))
    # Join the GF code strings
    return " ++ ".join([item["code"] for item in components])

def generate_safe_mode_grammar(lang_code):
    """
    Generates a minimal Safe Mode grammar that implements the 
    AbstractWiki SEMANTIC interface defined in AbstractWiki.gf.
    
    NOW UPDATED: Uses Weighted Topology for correct word order (SVO/SOV).
    """
    weights_db = load_weights()
    
    # 1. Determine Language Order (Default to SVO)
    order = LANG_ORDERS.get(lang_code.lower(), "SVO")
    weights = weights_db.get(order, weights_db["SVO"])
    
    # 2. Construct Linearizations
    
    # mkBio: Name (nsubj) + "is a" (root) + Prof/Nat (obj)
    bio_comps = [
        {"code": "name",      "role": "nsubj"},
        {"code": "\"is a\"",  "role": "root"},
        {"code": "nat ++ prof", "role": "obj"} # Bundle nat+prof as Object
    ]
    bio_lin = _build_linearization(bio_comps, weights)

    # mkEvent: Subject (nsubj) + "participated in" (root) + Event (obj)
    event_comps = [
        {"code": "subject",              "role": "nsubj"},
        {"code": "\"participated in\"",  "role": "root"},
        {"code": "event",                "role": "obj"}
    ]
    event_lin = _build_linearization(event_comps, weights)
    
    # mkFact: Subj (nsubj) + Pred (root)
    # Note: Predicate usually contains the verb, so we treat it as root
    fact_comps = [
        {"code": "subj", "role": "nsubj"},
        {"code": "pred", "role": "root"}
    ]
    fact_lin = _build_linearization(fact_comps, weights)
    
    # mkIsAProperty: Subj (nsubj) + "is" (root) + Prop (obj)
    prop_comps = [
        {"code": "subj",     "role": "nsubj"},
        {"code": "\"is\"",   "role": "root"},
        {"code": "prop",     "role": "obj"}
    ]
    prop_lin = _build_linearization(prop_comps, weights)

    gf_code = f"""concrete Wiki{lang_code.title()} of AbstractWiki = open Prelude in {{
  lincat
    Entity = Str;
    Frame = Str;
    Property = Str;
    Fact = Str;
    Predicate = Str;
    Modifier = Str;
    Value = Str;

  lin
    -- Dynamic Topology for {lang_code} ({order})
    
    -- Core Semantics
    mkFact subj pred = {fact_lin};
    
    -- Hardcoded stub for 'is a property'
    mkIsAProperty subj prop = {prop_lin};

    -- Specialized Frames (Schema Alignment)
    -- Bio: Name -> Profession -> Nationality -> Fact
    mkBio name prof nat = {bio_lin};

    -- Event: Subject -> EventObject -> Fact
    mkEvent subject event = {event_lin};
    
    -- Modifiers
    FactWithMod fact mod = fact ++ mod;
    
    -- Lexical Stubs
    mkLiteral s = s;
    
    -- Type Converters
    Entity2NP e = e;
    Property2AP p = p;
    VP2Predicate p = p;

    -- Required Lexicon Stubs
    lex_animal_N = "animal";
    lex_walk_V = "walks";
    lex_blue_A = "blue";
}}
"""
    return gf_code
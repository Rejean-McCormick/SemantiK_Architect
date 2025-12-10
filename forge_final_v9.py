import json
import os

# --- Configuration ---
MAP_FILE = 'rgl_map.json'
PATHS_FILE = 'rgl_paths.json'
RGL_BASE = 'gf-rgl/src'  # Adjust if your RGL is located elsewhere relative to this script

ABSTRACT_WIKI = """
abstract Wiki = {
  flags startcat = Phr ;
  cat
    Phr ; NP ; CN ; Adv ;
  fun
    SimpNP : CN -> NP ;
    John : NP ;
    Here : Adv ;
    apple_N : CN ;
}
"""

def load_json(filename):
    if not os.path.exists(filename):
        print(f"Error: {filename} not found.")
        return {}
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_grammars():
    data_map = load_json(MAP_FILE)
    data_paths = load_json(PATHS_FILE)
    module_map = data_map.get('module_map', {})
    
    # We still skip the truly broken ones
    skip_list = set(data_map.get('skip_list', []))

    print("Generating Abstract Wiki.gf...")
    with open("Wiki.gf", "w", encoding="utf-8") as f:
        f.write(ABSTRACT_WIKI)

    stats = {"standard": 0, "fallback": 0, "skipped": 0}
    generated_langs = []
    
    for wiki_code, rgl_code in module_map.items():
        if wiki_code in skip_list:
            stats["skipped"] += 1
            continue

        # Check if we have a path for this language
        cat_key = f"Cat{rgl_code}"
        if cat_key not in data_paths:
            print(f"Warning: Module {cat_key} not found. Skipping {wiki_code}.")
            stats["skipped"] += 1
            continue

        # Determine the directory where this language lives
        # rgl_paths.json gives us "afrikaans/CatAfr.gf"
        rel_path = data_paths[cat_key] 
        folder_path = os.path.join(RGL_BASE, os.path.dirname(rel_path))
        
        # INTELLIGENT CHECK: Does GrammarX.gf exist?
        grammar_file = os.path.join(folder_path, f"Grammar{rgl_code}.gf")
        has_grammar_module = os.path.exists(grammar_file)

        wiki_mod = f"Wiki{wiki_code}"
        
        if has_grammar_module:
            # STRATEGY A: HIGH ROAD (Standard Syntax)
            # Use this for English, French, German, etc.
            imports = [f"Grammar{rgl_code}", f"Paradigms{rgl_code}"]
            content = f"""
concrete {wiki_mod} of Wiki = {", ".join(imports)} ** open Syntax{rgl_code}, (P = {imports[-1]}) in {{
  lin
    SimpNP cn = mkNP cn ;
    John = mkNP (P.mkPN "John") ; 
    Here = P.mkAdv "here" ;
    apple_N = mkCN (P.mkN "apple") ;
}}
"""
            stats["standard"] += 1
            print(f"✔ {wiki_code}: Using Standard Syntax (Grammar{rgl_code} found).")

        else:
            # STRATEGY B: FALLBACK (Direct Noun/Cat)
            # Use this for Functor languages (Dan, Afr, Cat) where GrammarX.gf is missing
            imports = [f"Cat{rgl_code}", f"Noun{rgl_code}", f"Paradigms{rgl_code}"]
            content = f"""
concrete {wiki_mod} of Wiki = {", ".join(imports[:-1])} ** open {imports[1]}, (P = {imports[-1]}) in {{
  lin
    -- Fallback to low-level Noun constructors
    SimpNP cn = MassNP cn ;
    John = UsePN (P.mkPN "John") ; 
    Here = P.mkAdv "here" ;
    apple_N = UseN (P.mkN "apple") ;
}}
"""
            stats["fallback"] += 1
            print(f"⚠ {wiki_code}: Using Direct Constructors (Grammar{rgl_code} missing).")

        with open(f"{wiki_mod}.gf", "w", encoding="utf-8") as f:
            f.write(content.strip())
        
        generated_langs.append(wiki_code)

    print(f"\n--- Generation Complete ---")
    print(f"Standard Syntax: {stats['standard']}")
    print(f"Direct Fallback: {stats['fallback']}")
    print(f"Skipped:         {stats['skipped']}")

if __name__ == "__main__":
    generate_grammars()
import json
import os
import subprocess
import sys

# Load Config
CONFIG_PATH = 'config/rgl_matrix_config.json'

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

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"❌ Config file not found at {CONFIG_PATH}")
        return None
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def build():
    config = load_config()
    if not config: return

    # Paths
    rgl_base = config.get("rgl_base_path", "gf-rgl/src")
    strategy_file = config["strategy_json"]
    inventory_file = config["inventory_file"]
    
    # Validation
    if not os.path.exists(strategy_file):
        print("❌ Error: Strategy map not found. Run tools/rgl_matrix_auditor.py first.")
        return
    if not os.path.exists(inventory_file):
        print("❌ Error: Inventory file not found. Run tools/rgl_matrix_scanner.py first.")
        return

    # Load Data
    with open(strategy_file, 'r') as f:
        strategy_map = json.load(f)
    
    with open(inventory_file, 'r') as f:
        inventory_data = json.load(f)
        family_folders = inventory_data.get("families", [])

    print(f"🔨 Starting Build for {len(strategy_map)} languages...")

    # --- STEP 1: GENERATE ABSTRACT ---
    with open("Wiki.gf", "w", encoding="utf-8") as f:
        f.write(ABSTRACT_WIKI)
    print("   Generated Wiki.gf")

    # --- STEP 2: GENERATE CONCRETES ---
    generated_files = []
    
    for wiki_code, data in strategy_map.items():
        rgl_code = data["rgl_code"]
        mode = data["strategy"]
        
        wiki_mod = f"Wiki{wiki_code}"
        
        if mode == "HIGH_ROAD":
            # STRATEGY A: Standard API (Grammar + Syntax)
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
        elif mode == "SAFE_MODE":
            # STRATEGY B: Low-Level (Cat + Noun + Paradigms)
            imports = [f"Cat{rgl_code}", f"Noun{rgl_code}", f"Paradigms{rgl_code}"]
            content = f"""
concrete {wiki_mod} of Wiki = {", ".join(imports[:-1])} ** open {imports[1]}, (P = {imports[-1]}) in {{
  lin
    SimpNP cn = MassNP cn ;
    John = UsePN (P.mkPN "John") ; 
    Here = P.mkAdv "here" ;
    apple_N = UseN (P.mkN "apple") ;
}}
"""
        
        # Write File
        with open(f"{wiki_mod}.gf", "w", encoding="utf-8") as f:
            f.write(content.strip())
        
        generated_files.append(f"{wiki_mod}.gf")
        # print(f"   Generated {wiki_mod}.gf ({mode})")

    print(f"✅ Generated {len(generated_files)} concrete grammars.")

    # --- STEP 3: PREPARE COMPILATION PATHS ---
    # Base Includes
    include_paths = {
        rgl_base,
        os.path.join(rgl_base, 'api'),
        os.path.join(rgl_base, 'abstract'),
        os.path.join(rgl_base, 'common'),
        os.path.join(rgl_base, 'prelude')
    }

    # Add Language Paths (from strategy)
    for data in strategy_map.values():
        path_root = data.get("path_root") # e.g., "gf-rgl/src/catalan"
        if path_root:
            include_paths.add(path_root)

    # Add Family Paths (Detected by Scanner)
    # This fixes the "Functor" issue for Romance, Germanic, etc.
    for family in family_folders:
        include_paths.add(os.path.join(rgl_base, family))

    path_arg = ":".join(include_paths)

    # --- STEP 4: COMPILE ---
    print("\n🚀 Compiling Wiki.pgf...")
    
    # Command: gf -make -path [paths] Wiki.gf WikiEng.gf ...
    cmd = ["gf", "-make", "-path", path_arg, "Wiki.gf"] + generated_files
    
    try:
        # Run GF
        subprocess.run(cmd, check=True)
        print("\n🏆 SUCCESS: Wiki.pgf created successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\n💥 FAILURE: Compilation failed with error code {e.returncode}.")
        sys.exit(e.returncode)

if __name__ == "__main__":
    build()
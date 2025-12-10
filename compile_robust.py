import json
import os
import subprocess
import glob

# --- Configuration ---
PATHS_FILE = 'rgl_paths.json'
RGL_BASE = 'gf-rgl/src'
LOG_DIR = 'build_logs'

# THE FIX: Explicitly include shared family folders
FAMILY_FOLDERS = [
    'romance',      # Required by: Cat, Fre, Ita, Por, Ron, Spa
    'scandinavian', # Required by: Dan, Nor, Swe
    'germanic',     # Required by: Afr, Dut, Ger, Eng
    'uralic',       # Required by: Est, Fin
    'slavic',       # Required by: Bul, Pol, Rus
    'baltic',       # Required by: Lav, Lit
    'hindustani',   # Required by: Hin, Urd
    'arabic',       # Shared definitions
    'turkic'        # For Tur
]

def setup_paths():
    if not os.path.exists(PATHS_FILE):
        print("Error: rgl_paths.json not found.")
        return None

    with open(PATHS_FILE, 'r') as f:
        path_data = json.load(f)

    # 1. Base paths
    include_paths = {
        RGL_BASE, 
        os.path.join(RGL_BASE, 'api'),
        os.path.join(RGL_BASE, 'abstract'),
        os.path.join(RGL_BASE, 'common'),
        os.path.join(RGL_BASE, 'prelude')
    }

    # 2. Add Family paths (Critical Fix)
    for family in FAMILY_FOLDERS:
        full_path = os.path.join(RGL_BASE, family)
        if os.path.exists(full_path):
            include_paths.add(full_path)

    # 3. Add specific language folders
    for filename in path_data.values():
        folder_name = os.path.dirname(filename)
        full_path = os.path.join(RGL_BASE, folder_name)
        include_paths.add(full_path)

    return ":".join(include_paths)

def compile_robustly():
    path_arg = setup_paths()
    if not path_arg:
        return

    os.makedirs(LOG_DIR, exist_ok=True)
    all_files = glob.glob("Wiki*.gf")
    concrete_files = [f for f in all_files if f != "Wiki.gf"]
    
    successful_files = []
    
    print(f"--- Phase 1: Individual Compilation Check ({len(concrete_files)} languages) ---")

    # 1. Compile Abstract
    try:
        subprocess.run(
            ["gf", "-make", "-path", path_arg, "Wiki.gf"], 
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )
        print("✔ Abstract Wiki.gf compiled successfully.")
    except subprocess.CalledProcessError:
        print("CRITICAL: Abstract Wiki.gf failed. Aborting.")
        return

    # 2. Test each concrete syntax
    for gf_file in concrete_files:
        lang_code = gf_file.replace("Wiki", "").replace(".gf", "")
        
        try:
            # Individual dry-run
            subprocess.run(
                ["gf", "-make", "-path", path_arg, gf_file],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            print(f"✔ {lang_code}")
            successful_files.append(gf_file)
            
        except subprocess.CalledProcessError as e:
            print(f"✘ {lang_code} (FAILED - see logs)")
            log_path = os.path.join(LOG_DIR, f"error_{lang_code}.txt")
            with open(log_path, "w", encoding="utf-8") as log:
                log.write(f"Command: gf -make -path ... {gf_file}\n\n")
                log.write(e.stderr.decode())

    # 3. Final Build
    if not successful_files:
        print("\nNo languages compiled successfully.")
        return

    print(f"\n--- Phase 2: Building Final PGF with {len(successful_files)} languages ---")
    final_cmd = ["gf", "-make", "-path", path_arg, "Wiki.gf"] + successful_files
    
    try:
        subprocess.run(final_cmd, check=True)
        print(f"\nSUCCESS: Wiki.pgf created with {len(successful_files)} languages.")
    except subprocess.CalledProcessError:
        print("\nFAILURE during final linking.")

if __name__ == "__main__":
    compile_robustly()
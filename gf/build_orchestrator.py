import os
import json
import subprocess
import sys
import shutil
import glob
from typing import List, Dict, Tuple, Optional

# v2.0 Integration: Graceful AI Fallback
try:
    from ai_services.architect import architect
except (ImportError, ModuleNotFoundError):
    architect = None

# ===========================================================================
# CONFIGURATION
# ===========================================================================

GF_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(GF_DIR)
MATRIX_PATH = os.path.join(PROJECT_ROOT, "data", "indices", "everything_matrix.json")
GENERATED_SRC_DIR = os.path.join(PROJECT_ROOT, "gf", "generated", "src")
BUILD_LOGS_DIR = os.path.join(GF_DIR, "build_logs")
PGF_OUTPUT_FILE = os.path.join(GF_DIR, "AbstractWiki.pgf")
ABSTRACT_NAME = "AbstractWiki"

CODE_TO_NAME_FALLBACK = {
    "zul": "Zulu", "yor": "Yoruba", "ibo": "Igbo", "hau": "Hausa", 
    "wol": "Wolof", "kin": "Kinyarwanda"
}

def log(level: str, msg: str):
    colors = {
        "INFO": "\033[94m", "SUCCESS": "\033[92m", 
        "WARN": "\033[93m", "ERROR": "\033[91m", 
        "DEBUG": "\033[90m", "RESET": "\033[0m",
        "RAW": "" 
    }
    c = colors.get(level, colors["RESET"])
    if level == "RAW":
        print(msg)
    else:
        print(f"{c}[{level}] {msg}{colors['RESET']}")

# ===========================================================================
# MATRIX LOADER
# ===========================================================================

def load_build_targets() -> Dict[str, Dict]:
    log("INFO", f"Loading Matrix from: {MATRIX_PATH}")
    if not os.path.exists(MATRIX_PATH):
        log("ERROR", f"Critical: Matrix not found at {MATRIX_PATH}")
        sys.exit(1)
    with open(MATRIX_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    raw_languages = data.get("languages", {})
    targets = {}
    for code, entry in raw_languages.items():
        if entry.get("status", {}).get("build_strategy") != "BROKEN":
            targets[code] = entry
    log("INFO", f"Matrix Loaded: {len(targets)} active targets found.")
    return targets

def get_gf_suffix(iso_code: str, detected_suffix: str = None) -> str:
    if detected_suffix: return detected_suffix
    return iso_code.capitalize()

# ===========================================================================
# GENERATORS
# ===========================================================================

def generate_abstract():
    filename = f"{ABSTRACT_NAME}.gf"
    path = os.path.join(GF_DIR, filename)
    log("INFO", f"Generating Abstract Grammar: {path}")
    content = f"""abstract {ABSTRACT_NAME} = {{
  cat Entity; Property; Fact; Predicate; Modifier; Value;
  fun
    mkFact : Entity -> Predicate -> Fact;
    mkIsAProperty : Entity -> Property -> Fact;
    FactWithMod : Fact -> Modifier -> Fact;
    mkLiteral : Value -> Entity;
    Entity2NP : Entity -> Entity; Property2AP : Property -> Property; VP2Predicate : Predicate -> Predicate;
}}\n"""
    with open(path, 'w', encoding='utf-8') as f: f.write(content)
    return filename

def generate_interface():
    filename = "WikiI.gf"
    path = os.path.join(GF_DIR, filename)
    log("INFO", f"Generating Interface Grammar: {path}")
    content = f"""incomplete concrete WikiI of {ABSTRACT_NAME} = open Syntax in {{
  lincat Entity = NP; Property = AP; Fact = S; Predicate = VP; Modifier = Adv; Value = {{s : Str}};
  lin
    mkFact s p = mkS (mkCl s p);
    mkIsAProperty s p = mkS (mkCl s (mkVP p));
    FactWithMod f m = mkS m f;
    Entity2NP x = x; Property2AP x = x; VP2Predicate x = x;
    mkLiteral v = mkNP (mkN v.s); 
}}\n"""
    with open(path, 'w', encoding='utf-8') as f: f.write(content)
    return filename

def generate_rgl_connector(iso_code, suffix):
    filename = f"Wiki{suffix}.gf"
    path = os.path.join(GF_DIR, filename)
    content = f"""concrete Wiki{suffix} of {ABSTRACT_NAME} = WikiI ** open Syntax{suffix}, Paradigms{suffix} in {{}};\n"""
    with open(path, 'w', encoding='utf-8') as f: f.write(content)

# ===========================================================================
# PATH RESOLUTION
# ===========================================================================

def resolve_language_path(iso_code: str, lang_entry: Dict, rgl_src_base: str) -> Tuple[Optional[str], Optional[List[str]]]:
    contrib_base = os.path.join(GF_DIR, "contrib")
    paths = [GF_DIR, "."] 
    if rgl_src_base:
        paths.extend([rgl_src_base, os.path.join(rgl_src_base, "api"), os.path.join(rgl_src_base, "prelude"), os.path.join(rgl_src_base, "abstract"), os.path.join(rgl_src_base, "common")])

    # 1. Contrib
    default_suffix = iso_code.capitalize()
    target_file = f"Wiki{default_suffix}.gf"
    contrib_path = os.path.join(contrib_base, iso_code, target_file)
    if os.path.exists(contrib_path):
        paths.append(os.path.dirname(contrib_path))
        return contrib_path, paths

    # 2. Generated
    folder = iso_code.lower() 
    factory_path = os.path.join(GENERATED_SRC_DIR, folder, target_file)
    if os.path.exists(factory_path):
        paths.append(os.path.dirname(factory_path))
        return factory_path, paths
        
    # 3. RGL (Dynamic Discovery)
    if rgl_src_base:
        rgl_folder_name = lang_entry.get("meta", {}).get("folder")
        if rgl_folder_name:
            candidate_path = os.path.join(rgl_src_base, rgl_folder_name)
            if os.path.exists(candidate_path):
                detected_suffix = default_suffix
                patterns = [os.path.join(candidate_path, "Grammar*.gf"), os.path.join(candidate_path, "Lang*.gf")]
                found_file = None
                for p in patterns:
                    matches = glob.glob(p)
                    if matches:
                        found_file = matches[0]
                        break
                
                if found_file:
                    detected_suffix = os.path.basename(found_file).replace("Grammar", "").replace("Lang", "").replace(".gf", "")
                else:
                    log("WARN", f"[{iso_code}] Folder found ({rgl_folder_name}) but no Grammar/Lang file.")

                connector_file = f"Wiki{detected_suffix}.gf"
                generated_connector_path = os.path.join(GF_DIR, connector_file)
                if not os.path.exists(generated_connector_path):
                    generate_rgl_connector(iso_code, detected_suffix)
                
                paths.append(candidate_path)
                return generated_connector_path, paths
    return None, None

def get_rgl_base() -> Optional[str]:
    rgl_base = os.environ.get("GF_LIB_PATH")
    if rgl_base and os.path.exists(rgl_base): return os.path.join(rgl_base, "src") if os.path.exists(os.path.join(rgl_base, "src")) else rgl_base
    internal_path = os.path.join(PROJECT_ROOT, "gf-rgl")
    if os.path.exists(internal_path): return os.path.join(internal_path, "src") if os.path.exists(os.path.join(internal_path, "src")) else internal_path
    sibling_path = os.path.join(os.path.dirname(PROJECT_ROOT), "gf-rgl")
    if os.path.exists(sibling_path): return os.path.join(sibling_path, "src") if os.path.exists(os.path.join(sibling_path, "src")) else sibling_path
    log("WARN", "No RGL Base found.")
    return None

# ===========================================================================
# AI STUBS
# ===========================================================================
def attempt_ai_generation(iso_code, lang_meta):
    if not architect: return False
    try:
        lang_name = lang_meta.get("name", CODE_TO_NAME_FALLBACK.get(iso_code, iso_code))
        log("INFO", f"🏗️ Architect: Designing grammar for {lang_name} ({iso_code})...")
        code = architect.generate_grammar(iso_code, lang_name)
        if not code: return False
        suffix = get_gf_suffix(iso_code)
        folder = os.path.join(GENERATED_SRC_DIR, iso_code.lower())
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, f"Wiki{suffix}.gf"), "w", encoding="utf-8") as f: f.write(code)
        return True
    except: return False

def attempt_ai_repair(iso_code, filepath, error_log):
    if not architect: return False
    try:
        log("WARN", f"🚑 Surgeon: Repairing {iso_code}...")
        with open(filepath, "r") as f: broken = f.read()
        fixed = architect.repair_grammar(broken, error_log)
        if not fixed: return False
        shutil.copy(filepath, filepath + ".bak")
        with open(filepath, "w") as f: f.write(fixed)
        return True
    except: return False

# ===========================================================================
# MAIN ORCHESTRATOR
# ===========================================================================

def main():
    log("INFO", "🚀 Abstract Wiki Architect v2.0: Orchestrator Online")
    if os.path.exists(BUILD_LOGS_DIR): shutil.rmtree(BUILD_LOGS_DIR)
    os.makedirs(BUILD_LOGS_DIR)
    targets = load_build_targets()
    generate_abstract()
    generate_interface()
    rgl_base = get_rgl_base()
    
    if os.path.exists("AbstractWiki.gfo"): os.remove("AbstractWiki.gfo")
    try:
        subprocess.run(["gf", "-batch", "-c", "AbstractWiki.gf"], check=True, cwd=GF_DIR)
        log("SUCCESS", "Abstract Syntax Verified.")
    except: log("ERROR", "Fatal: Abstract failed."); sys.exit(1)

    valid_files = []
    all_paths = []
    
    log("INFO", "---------------------------------------------------")
    log("INFO", "Starting Language Build Loop")
    log("INFO", "---------------------------------------------------")

    for iso, meta in targets.items():
        try:
            file_path, paths = resolve_language_path(iso, meta, rgl_base)
            if not file_path:
                if attempt_ai_generation(iso, meta): file_path, paths = resolve_language_path(iso, meta, rgl_base)
            if not file_path: continue
            
            deduped_paths = list(dict.fromkeys([GF_DIR] + paths))
            path_arg = os.pathsep.join(deduped_paths)
            cmd = ["gf", "-batch", "-c", "-path", path_arg, file_path]
            result = subprocess.run(cmd, cwd=GF_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode == 0:
                log("SUCCESS", f"✅ {iso}: Verified")
                valid_files.append(file_path)
                all_paths.extend(deduped_paths)
            else:
                log("ERROR", f"❌ {iso}: Compilation Failed.")
                
                # --- AUTO-HEAL: Delete Corrupted Generated Files ---
                abs_file = os.path.abspath(file_path)
                abs_gen = os.path.abspath(GENERATED_SRC_DIR)
                
                if abs_file.startswith(abs_gen):
                    log("WARN", f"🧹 Detected broken file in Generated Source: {os.path.basename(file_path)}")
                    log("WARN", "   -> Auto-deleting to force fresh RGL fallback...")
                    try:
                        os.remove(file_path)
                        
                        # Re-Resolve: Should now find RGL or create fresh empty connector
                        new_file, new_paths = resolve_language_path(iso, meta, rgl_base)
                        
                        if new_file:
                            log("INFO", f"   -> Retrying with fresh target...")
                            d_paths = list(dict.fromkeys([GF_DIR] + new_paths))
                            p_arg = os.pathsep.join(d_paths)
                            c = ["gf", "-batch", "-c", "-path", p_arg, new_file]
                            
                            retry = subprocess.run(c, cwd=GF_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                            if retry.returncode == 0:
                                log("SUCCESS", f"✅ {iso}: Auto-Healed & Verified")
                                valid_files.append(new_file)
                                all_paths.extend(d_paths)
                                continue # Skip remaining error handling
                            else:
                                log("ERROR", f"❌ {iso}: Heal failed. RGL issue persists.")
                    except Exception as e:
                        log("ERROR", f"   -> Deletion failed: {e}")
                # ---------------------------------------------------

                if attempt_ai_repair(iso, file_path, result.stderr):
                    if subprocess.run(cmd, cwd=GF_DIR).returncode == 0:
                        log("SUCCESS", f"✅ {iso}: Repaired")
                        valid_files.append(file_path); all_paths.extend(deduped_paths)
                else:
                    log("ERROR", f"💀 {iso}: Skipping.")
                    with open(os.path.join(BUILD_LOGS_DIR, f"{iso}_error.log"), "w") as f: f.write(result.stderr)
        except Exception as e:
            log("ERROR", f"Exception {iso}: {e}")

    if not valid_files: log("ERROR", "No languages linked."); sys.exit(1)
    
    final_paths = list(dict.fromkeys(all_paths))
    path_arg = os.pathsep.join(final_paths)
    try:
        log("INFO", f"\n🔗 Linking {len(valid_files)} languages into PGF binary...")
        subprocess.run(["gf", "-batch", "-make", "-path", path_arg, "AbstractWiki.gf"] + valid_files, check=True, cwd=GF_DIR)
        pgf = os.path.join(GF_DIR, f"{ABSTRACT_NAME}.pgf")
        if os.path.exists(pgf): shutil.move(pgf, PGF_OUTPUT_FILE)
        log("SUCCESS", f"📦 Binary created: {PGF_OUTPUT_FILE}")
    except: log("ERROR", "Linking Failed."); sys.exit(1)

if __name__ == "__main__":
    main()
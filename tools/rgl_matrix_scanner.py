import os
import json
import glob

# Load Config
CONFIG_PATH = 'config/rgl_matrix_config.json'

def load_config():
    if not os.path.exists(CONFIG_PATH):
        # Fallback defaults if config missing
        return {"rgl_base_path": "gf-rgl/src", "inventory_file": "data/indices/rgl_matrix_inventory.json"}
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def scan_rgl():
    config = load_config()
    base_path = config.get("rgl_base_path", "gf-rgl/src")
    output_file = config.get("inventory_file", "data/indices/rgl_matrix_inventory.json")
    
    print(f"🔍 Scanning {base_path} for GF modules...")
    
    inventory = {}
    family_folders = set()

    # Walk through every folder in RGL
    for root, dirs, files in os.walk(base_path):
        folder_name = os.path.basename(root)
        
        # Skip ignored folders
        if folder_name in config.get("ignored_folders", []):
            continue

        # Look for GF files
        for file in files:
            if not file.endswith(".gf"): continue
            
            # Save normalized path
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, start='.')
            norm_path = rel_path.replace("\\", "/")
            
            # HEURISTIC 1: Detect Standard Language Modules
            # Pattern: [Type][Code].gf (e.g., CatEng.gf, GrammarChi.gf)
            name_part = file.replace(".gf", "")
            
            module_type = None
            lang_code = None

            if name_part.startswith("Grammar"):
                module_type = "Grammar"
                lang_code = name_part.replace("Grammar", "")
            elif name_part.startswith("Cat"):
                module_type = "Cat"
                lang_code = name_part.replace("Cat", "")
            elif name_part.startswith("Noun"):
                module_type = "Noun"
                lang_code = name_part.replace("Noun", "")
            elif name_part.startswith("Paradigms"):
                module_type = "Paradigms"
                lang_code = name_part.replace("Paradigms", "")
            
            if module_type and len(lang_code) == 3:
                # Add to inventory
                if lang_code not in inventory:
                    inventory[lang_code] = {"path": root, "modules": {}}
                
                inventory[lang_code]["modules"][module_type] = norm_path
            
            # HEURISTIC 2: Detect Family Definitions
            # e.g., romance/GrammarRomance.gf
            if "Grammar" in name_part and len(lang_code) > 3:
                 family_folders.add(folder_name)

    # Save Data
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    final_data = {
        "languages": inventory,
        "families": list(family_folders)
    }

    with open(output_file, 'w') as f:
        json.dump(final_data, f, indent=2)
    
    print(f"✅ Inventory saved to {output_file}")
    print(f"   Languages found: {len(inventory)}")
    print(f"   Families detected: {len(family_folders)}")

if __name__ == "__main__":
    scan_rgl()
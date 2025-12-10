import json
import csv
import os

# Load Config
CONFIG_PATH = 'config/rgl_matrix_config.json'

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"❌ Config file not found at {CONFIG_PATH}")
        return None
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def audit():
    config = load_config()
    if not config: return

    # Input Files
    inventory_file = config["inventory_file"]
    map_file = config["map_file"] # rgl_map.json
    
    # Output Files
    csv_output = config["audit_csv"]
    json_output = config["strategy_json"]

    if not os.path.exists(inventory_file):
        print(f"❌ Error: Inventory file not found at {inventory_file}")
        print("   Run tools/rgl_matrix_scanner.py first.")
        return

    with open(inventory_file, 'r') as f:
        scan_data = json.load(f)
        inventory = scan_data.get("languages", {})
    
    if not os.path.exists(map_file):
        print(f"❌ Error: Map file not found at {map_file}")
        return

    with open(map_file, 'r') as f:
        rgl_map = json.load(f).get('module_map', {})

    matrix_rows = []
    strategy_map = {}

    print("📊 Auditing languages against Inventory...")

    for wiki_code, rgl_code in rgl_map.items():
        # Initialize Status
        status = {
            "Wiki": wiki_code, "RGL": rgl_code,
            "Cat": "MISSING", "Noun": "MISSING", "Grammar": "MISSING",
            "Strategy": "SKIP"
        }

        # Check against Inventory
        if rgl_code in inventory:
            modules = inventory[rgl_code]["modules"]
            
            if "Cat" in modules: status["Cat"] = "FOUND"
            if "Noun" in modules: status["Noun"] = "FOUND"
            if "Grammar" in modules: status["Grammar"] = "FOUND"

            # --- DECISION ENGINE ---
            # RULE 1: HIGH_ROAD (Standard)
            # Requires physical Grammar file + Cat + Noun
            if status["Cat"] == "FOUND" and status["Noun"] == "FOUND" and status["Grammar"] == "FOUND":
                status["Strategy"] = "HIGH_ROAD"
            
            # RULE 2: SAFE_MODE (Functor or Partial)
            # Requires at least Cat + Noun (we bypass Grammar/Syntax)
            elif status["Cat"] == "FOUND" and status["Noun"] == "FOUND":
                status["Strategy"] = "SAFE_MODE"
            
            # RULE 3: BROKEN
            else:
                status["Strategy"] = "BROKEN"
        
        else:
            status["Strategy"] = "NOT_INSTALLED"

        # Add to CSV list
        matrix_rows.append(status)
        
        # Add to JSON Map (Only actionable strategies)
        if status["Strategy"] in ["HIGH_ROAD", "SAFE_MODE"]:
            strategy_map[wiki_code] = {
                "rgl_code": rgl_code,
                "strategy": status["Strategy"],
                "modules": inventory[rgl_code]["modules"],
                "path_root": inventory[rgl_code]["path"]
            }

    # Write CSV Report
    os.makedirs(os.path.dirname(csv_output), exist_ok=True)
    with open(csv_output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["Wiki", "RGL", "Cat", "Noun", "Grammar", "Strategy"])
        writer.writeheader()
        writer.writerows(matrix_rows)

    # Write Executable Strategy Map
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(strategy_map, f, indent=2)

    print(f"✅ Audit Complete.")
    print(f"   Human Report: {csv_output}")
    print(f"   Builder Map:  {json_output}")

if __name__ == "__main__":
    audit()
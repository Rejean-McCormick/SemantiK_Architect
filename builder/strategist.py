# builder\strategist.py
import os
import json
import sys
from . import config

# -----------------------------------------------------------------------------
# SENIOR DEV UPGRADE: Strategy Hierarchy
# -----------------------------------------------------------------------------
# Defines the quality rank. Higher is better.
STRATEGY_RANK = {
    "GOLD": 4,
    "SILVER": 3,
    "BRONZE": 2,
    "IRON": 1,
    "SKIP": 0
}

def load_json(path, default_type=dict):
    """
    Robust JSON loader. Returns default_type() if file missing/broken.
    """
    if not os.path.exists(path):
        return default_type()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"⚠️  Warning: Corrupt JSON file at {path}")
        return default_type()

def get_build_context(rgl_code):
    """
    Defines ALL dynamic variables available to your strategies.json templates.
    Add new logic here, and it becomes instantly available in the JSON.
    """
    # 1. Determine SimpNP logic based on config
    if config.AMBIGUITY_STRATEGY == "indef":
        simp_np_val = "mkNP a_Det cn"
    else:
        simp_np_val = "mkNP cn"

    # 2. Return the Context Dictionary
    return {
        "code": rgl_code,
        "simp_np": simp_np_val,
        # Future-proofing: Add more vars here if needed
    }

def generate_blueprint(rgl_code, modules, strategies):
    """
    Evaluates a language against the list of strategies using generic templating.
    """
    available_modules = set(modules.keys())
    context = get_build_context(rgl_code)

    for strat in strategies:
        required = set(strat.get("requirements", []))
        
        # Check if requirements are a subset of available modules
        if required.issubset(available_modules):
            
            # --- MATCH FOUND ---
            blueprint = {
                "status": strat["name"],
                "imports": [],
                "lincats": {},
                "rules": {}
            }

            try:
                # 1. Expand Imports
                blueprint["imports"] = [
                    imp.format(**context) for imp in strat.get("imports", [])
                ]

                # 2. Expand Lincats (Qualified Names)
                base = strat.get("lincat_base", "").format(**context)
                blueprint["lincats"] = {
                    "Phr": f"{base}.Phr",
                    "NP":  f"{base}.NP",
                    "CN":  f"{base}.CN",
                    "Adv": f"{base}.Adv"
                }

                # 3. Expand Rules
                for key, template in strat.get("rules", {}).items():
                    blueprint["rules"][key] = template.format(**context)

                return blueprint

            except KeyError as e:
                print(f"❌ Template Error in Strategy '{strat['name']}': Missing variable {e}")
                continue

    return {"status": "SKIP", "imports": [], "lincats": {}, "rules": {}}

def detect_drift(rgl_code, new_status, old_plan):
    """
    Checks if the quality of a language has degraded compared to the previous build.
    """
    if not old_plan:
        return None

    prev_entry = old_plan.get(rgl_code)
    if not prev_entry:
        return None  # New language, no drift possible

    prev_status = prev_entry.get("status", "SKIP")
    
    new_rank = STRATEGY_RANK.get(new_status, 0)
    prev_rank = STRATEGY_RANK.get(prev_status, 0)

    if new_rank < prev_rank:
        return f"🔻 REGRESSION: {prev_status} -> {new_status}"
    elif new_rank > prev_rank:
        return f"🚀 UPGRADE: {prev_status} -> {new_status}"
    
    return None

def generate_plan(fail_on_regression=False):
    print("🧠 Strategist: Calculating optimal build paths (Template-Driven)...")
    
    # Paths
    plan_path = os.path.join("builder", "build_plan.json")

    # Load inputs
    inventory_data = load_json(config.RGL_INVENTORY_FILE, dict)
    inventory = inventory_data.get("languages", {})
    strategies = load_json(config.STRATEGIES_FILE, list)
    
    # Load PREVIOUS plan for Drift Detection
    old_plan = load_json(plan_path, dict)
    
    if not inventory:
        print(f"❌ Inventory missing or empty: {config.RGL_INVENTORY_FILE}")
        return False
    if not strategies:
        print(f"❌ Strategies missing or empty: {config.STRATEGIES_FILE}")
        return False

    build_plan = {}
    stats = {s["name"]: 0 for s in strategies}
    stats["SKIP"] = 0
    
    regressions = []
    upgrades = []

    print(f"   Analyzing {len(inventory)} languages...")

    for rgl_code, data in inventory.items():
        modules = data.get("modules", {})
        
        # Calculate NEW Plan
        blueprint = generate_blueprint(rgl_code, modules, strategies)
        
        # Check for Drift
        drift_msg = detect_drift(rgl_code, blueprint["status"], old_plan)
        if drift_msg:
            if "REGRESSION" in drift_msg:
                regressions.append(f"{rgl_code}: {drift_msg}")
            else:
                upgrades.append(f"{rgl_code}: {drift_msg}")

        if blueprint["status"] != "SKIP":
            build_plan[rgl_code] = blueprint
        
        # Safe stat counting
        st = blueprint.get("status", "SKIP")
        stats[st] = stats.get(st, 0) + 1

    # --- REPORTING ---
    if upgrades:
        print(f"\n✨ {len(upgrades)} IMPROVEMENTS DETECTED:")
        for msg in upgrades[:5]: print(f"   {msg}")
        if len(upgrades) > 5: print(f"   ...and {len(upgrades)-5} others.")

    if regressions:
        print(f"\n⚠️  {len(regressions)} REGRESSIONS DETECTED:")
        for msg in regressions: print(f"   {msg}")
        
        if fail_on_regression:
            print("\n❌ ABORTING BUILD DUE TO QUALITY REGRESSION.")
            print("   (Fix the broken grammar files or update strategies.json)")
            sys.exit(1)

    # Save Plan
    try:
        with open(plan_path, 'w', encoding='utf-8') as f:
            json.dump(build_plan, f, indent=2)
        
        print(f"\n📋 Plan saved to {plan_path}")
        print(f"📊 Stats: {json.dumps(stats)}")
        return True
    except IOError as e:
        print(f"❌ Error writing build plan: {e}")
        return False
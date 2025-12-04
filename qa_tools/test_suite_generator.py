import json
import csv
import os
import sys

# Add project root to path to find data
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_grammar_config():
    """Loads the master grammar matrix."""
    config_path = os.path.join('data', 'romance_grammar_matrix.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find {config_path}")
        sys.exit(1)

def generate_csv_templates():
    """
    Generates CSV testing templates for each supported language.
    """
    config = load_grammar_config()
    languages = config['languages'].keys()
    
    output_dir = os.path.join('qa_tools', 'generated_datasets')
    os.makedirs(output_dir, exist_ok=True)
    
    # Standard Lemmas to test across all languages
    # These are English concepts. The human/AI task is to:
    # 1. Translate Lemma to Target Language (Masculine Singular Base)
    # 2. Generate the full sentence based on Gender/Rules
    base_test_cases = [
        # (Concept Name, Concept Gender, Profession Concept, Nationality Concept)
        ("Roberto", "Male", "Actor", "Italian"),
        ("Maria", "Female", "Actor", "Italian"),
        ("Enrico", "Male", "Scientist", "Italian"), # Trap: S+Consonant checks
        ("Sofia", "Female", "Scientist", "Italian"),
        ("Pablo", "Male", "Painter", "Spanish"),
        ("Frida", "Female", "Painter", "Spanish"),
        ("Jean", "Male", "Writer", "French"),
        ("Simone", "Female", "Writer", "French"),
        ("Dante", "Male", "Poet", "Italian"),       # Trap: Irregular (Poeta)
        ("Alda", "Female", "Poet", "Italian"),      # Trap: Irregular (Poetessa)
        ("Sigmund", "Male", "Psychologist", "Austrian"), # Trap: ps- start
        ("Marie", "Female", "Physicist", "Polish")
    ]
    
    print(f"🏭 QA Factory started. Generating templates for: {', '.join(languages)}")
    
    for lang in languages:
        lang_name = config['languages'][lang]['name']
        filename = os.path.join(output_dir, f"test_suite_{lang}.csv")
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Header Columns
            writer.writerow([
                'Test_ID',
                'Name', 
                'Gender (Male/Female)', 
                f'Profession_Lemma_in_{lang_name}', 
                f'Nationality_Lemma_in_{lang_name}', 
                'EXPECTED_FULL_SENTENCE'
            ])
            
            # Write rows
            for i, case in enumerate(base_test_cases, 1):
                # We pre-fill the name and gender, leaving lemmas and output blank/hinted
                # User/AI must translate 'Actor' -> 'Attore' (IT) or 'Acteur' (FR)
                test_id = f"{lang.upper()}_{i:03d}"
                name, gender, prof_concept, nat_concept = case
                
                writer.writerow([
                    test_id,
                    name,
                    gender,
                    f"[{prof_concept}]",  # Placeholder hint
                    f"[{nat_concept}]",   # Placeholder hint
                    ""                    # Empty for Ground Truth
                ])
                
        print(f"   ✅ Created {filename}")

if __name__ == "__main__":
    # Ensure we are running from project root context if possible, or handle paths relative to script
    # Changing working directory to project root for simplicity
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    generate_csv_templates()
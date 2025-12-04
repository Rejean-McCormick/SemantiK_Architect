"""
SHARED ROMANCE ENGINE (Prototype)
---------------------------------
A single Python function designed to render biographical sentences 
for any Romance language defined in the Grammar Matrix.

This function is "Data-Driven": it contains no hardcoded rules for Italian 
or Spanish. It only contains logic to READ rules from a configuration object.
"""

def render_romance_bio(name, gender, prof_lemma, nat_lemma, lang_config):
    """
    Universal Renderer for Romance Languages.
    
    Args:
        name (str): Person's name (e.g., "Marie Curie")
        gender (str): 'Male' or 'Female' (Case insensitive)
        prof_lemma (str): Profession in base form (e.g., "Attore")
        nat_lemma (str): Nationality in base form (e.g., "Italiano")
        lang_config (dict): The specific JSON chunk for one language 
                            (e.g., matrix['languages']['it'])
                            
    Returns:
        str: The fully inflected sentence.
    """
    
    # 1. Normalize Inputs
    gender = gender.lower().strip()
    prof_lemma = prof_lemma.lower().strip()
    nat_lemma = nat_lemma.lower().strip()
    
    # Extract Rules from Config
    morph_rules = lang_config['morphology']
    article_rules = lang_config['articles']
    phonetics = lang_config.get('phonetics', {})
    structure = lang_config['structure']

    # =================================================================
    # 2. MORPHOLOGY ENGINE (Inflect Nouns/Adjectives)
    # =================================================================
    
    def inflect(word, target_gender, is_noun=False):
        if target_gender == 'male':
            return word # Assume base form is Male Singular
            
        # A. Check Irregulars (Dictionary Lookup)
        # We assume the config keys are lowercase
        irregulars = morph_rules.get('irregulars', {})
        if word in irregulars:
            return irregulars[word]
            
        # B. Apply Suffix Rules
        # We iterate through the defined suffixes in the JSON.
        # Order matters! The JSON list should be ordered by specific->general.
        suffixes = morph_rules.get('suffixes', [])
        
        for rule in suffixes:
            ending = rule['ends_with']
            replacement = rule['replace_with']
            
            if word.endswith(ending):
                # Cut the ending and add the replacement
                stem = word[:-len(ending)]
                return stem + replacement
        
        # C. Naive Fallback (if no rule matched)
        # If it ends in 'o', make it 'a'. Otherwise, leave it.
        if word.endswith('o'):
            return word[:-1] + 'a'
            
        return word

    # Apply Inflection
    final_prof = inflect(prof_lemma, gender, is_noun=True)
    # Note: Nationalities act like adjectives, usually sharing similar rules
    final_nat = inflect(nat_lemma, gender, is_noun=False)

    # =================================================================
    # 3. PHONETIC ARTICLE SELECTOR
    # =================================================================
    
    def get_indefinite_article(next_word, target_gender):
        # 1. Get the gender definitions
        rules = article_rules['m'] if target_gender == 'male' else article_rules['f']
        default_art = rules['default']
        
        # 2. Check Phonetic Triggers
        # Triggers define when to deviate from default (e.g. Italian 'uno', French 'l'')
        
        # CHECK: Vowel Start (Elision)
        # e.g., Italian 'un' amico (M) vs un'amica (F)
        if next_word[0] in "aeiouàèìòù":
            if 'vowel' in rules:
                return rules['vowel']
        
        # CHECK: Impure S / Complex Clusters (Italian Specific)
        # Config provides list: ["s_consonant", "z", "gn", ...]
        impure_triggers = phonetics.get('impure_triggers', [])
        if impure_triggers:
            is_s_cons = (next_word.startswith('s') and len(next_word) > 1 
                         and next_word[1] not in "aeiouàèìòù")
            
            # Helper to check starts_with against a list
            starts_match = any(next_word.startswith(t) for t in impure_triggers if t != 's_consonant')
            
            if is_s_cons or starts_match:
                if 's_impure' in rules:
                    return rules['s_impure']

        # CHECK: Stressed 'A' (Spanish Specific)
        # e.g., un águila (F)
        stressed_a_words = phonetics.get('stressed_a_words', [])
        if next_word in stressed_a_words:
            if 'stressed_a' in rules:
                return rules['stressed_a']
                
        return default_art

    article = get_indefinite_article(final_prof, gender)

    # =================================================================
    # 4. SENTENCE ASSEMBLER
    # =================================================================
    
    # Handle Elision Spacing
    # If article is "un'" or "l'", we want ZERO space. Otherwise ONE space.
    sep = "" if article.endswith("'") else " "
    
    # We use a simple replacement on the template string provided in JSON
    # Template: "{name} è {article}{sep}{profession} {nationality}."
    
    sentence = structure.replace("{name}", name)
    sentence = sentence.replace("{article}", article)
    sentence = sentence.replace("{sep}", sep) # The JSON specifically separates article/sep
    sentence = sentence.replace("{profession}", final_prof)
    sentence = sentence.replace("{nationality}", final_nat)
    
    # Final cleanup (Capitalize first letter if name is missing context, though name is usually prop)
    return sentence

# ------------------------------------------------------------------
# DEBUGGING / DEMO (Runs if executed directly)
# ------------------------------------------------------------------
if __name__ == "__main__":
    # Example: Manually mocking the Italian Config to test the engine
    mock_it_config = {
        "articles": {
            "m": {"default": "un", "s_impure": "uno", "vowel": "un"},
            "f": {"default": "una", "vowel": "un'"}
        },
        "morphology": {
            "suffixes": [
                {"ends_with": "tore", "replace_with": "trice"}
            ],
            "irregulars": {}
        },
        "phonetics": {
            "impure_triggers": ["z", "gn"]
        },
        "structure": "{name} è {article}{sep}{profession} {nationality}."
    }
    
    print("Testing Engine with Mock Data...")
    print(render_romance_bio("Roberto", "Male", "Attore", "Italiano", mock_it_config))
    print(render_romance_bio("Sophia", "Female", "Attore", "Italiano", mock_it_config))
"""
ROMANCE LANGUAGE ENGINE
-----------------------
A data-driven renderer for Romance languages (IT, ES, FR, PT, RO, CA, etc.).

This engine handles:
1. Gender Inflection (Suffix replacement and Irregulars)
2. Phonetic Article Selection (Elision, Italian 's-impure', Spanish 'stressed-a')
3. Sentence Construction (Template filling)
"""

def render_bio(name, gender, prof_lemma, nat_lemma, config):
    """
    Main Entry Point.
    
    Args:
        name (str): The subject's name.
        gender (str): 'Male' or 'Female'.
        prof_lemma (str): The profession in base form (usually Masc Singular).
        nat_lemma (str): The nationality in base form (usually Masc Singular).
        config (dict): The JSON configuration card for the specific language.
    
    Returns:
        str: The fully inflected sentence.
    """
    
    # 1. Normalize Inputs
    gender = gender.lower().strip()
    prof_lemma = prof_lemma.lower().strip()
    nat_lemma = nat_lemma.lower().strip()
    
    # 2. Extract Rules from Config
    # We use .get() to prevent crashes if a config is incomplete
    morph_rules = config.get('morphology', {})
    article_rules = config.get('articles', {})
    phonetics = config.get('phonetics', {})
    structure = config.get('structure', "{name} {profession} {nationality}.")

    # =================================================================
    # HELPER: Morphology Engine (Inflect Nouns/Adjectives)
    # =================================================================
    def inflect(word, target_gender):
        if target_gender == 'male':
            return word # Assume input is already base form (Masc SG)
            
        # A. Check Irregulars (Dictionary Lookup)
        irregulars = morph_rules.get('irregulars', {})
        if word in irregulars:
            return irregulars[word]
            
        # B. Apply Suffix Rules
        # The config provides a list of rules: {"ends_with": "tore", "replace_with": "trice"}
        # We must sort by length descending to ensure "-tore" matches before "-e"
        suffixes = morph_rules.get('suffixes', [])
        # Sort logic: longest 'ends_with' string comes first
        sorted_suffixes = sorted(suffixes, key=lambda x: len(x['ends_with']), reverse=True)
        
        for rule in sorted_suffixes:
            ending = rule['ends_with']
            replacement = rule['replace_with']
            
            if word.endswith(ending):
                # Cut the ending and append the replacement
                stem = word[:-len(ending)]
                return stem + replacement
        
        # C. Generic Fallback
        # If no rule matched, check if it's a standard -o -> -a shift 
        # (Common in IT/ES/PT, but we implement it safely)
        if word.endswith('o'):
            return word[:-1] + 'a'
            
        return word

    # Apply Inflection
    final_prof = inflect(prof_lemma, gender)
    final_nat = inflect(nat_lemma, gender)

    # =================================================================
    # HELPER: Phonetic Article Selector
    # =================================================================
    def get_article(next_word, target_gender):
        # 1. Select the gender bucket (m/f)
        gender_key = 'm' if target_gender == 'male' else 'f'
        if gender_key not in article_rules:
            return ""
            
        rules = article_rules[gender_key]
        default_art = rules.get('default', '')
        
        # 2. Analyze the 'Next Word' for Phonetic Triggers
        # Triggers are defined in config['phonetics']
        
        # --- Check: Vowel Start (Elision) ---
        # e.g., Italian l'amico, French l'homme
        if next_word[0] in "aeiouàèìòù":
            if 'vowel' in rules:
                return rules['vowel']
        
        # --- Check: Impure Triggers (Italian Specific) ---
        # Config provides list: ["s_consonant", "z", "ps", ...]
        impure_triggers = phonetics.get('impure_triggers', [])
        if impure_triggers:
            is_s_cons = (next_word.startswith('s') and len(next_word) > 1 
                         and next_word[1] not in "aeiouàèìòù")
            
            # Check other starts (z, gn, ps, etc.)
            other_match = any(next_word.startswith(t) for t in impure_triggers if t != 's_consonant')
            
            if (is_s_cons and 's_consonant' in impure_triggers) or other_match:
                if 's_impure' in rules:
                    return rules['s_impure']

        # --- Check: Stressed 'A' (Spanish Specific) ---
        # e.g., un águila (F) uses masculine article to avoid cacophony
        stressed_a_words = phonetics.get('stressed_a_words', [])
        if next_word in stressed_a_words:
            if 'stressed_a' in rules:
                return rules['stressed_a']
                
        return default_art

    article = get_article(final_prof, gender)

    # =================================================================
    # 3. SENTENCE ASSEMBLER
    # =================================================================
    
    # Logic: Handle Spacing for Apostrophes
    # If article is "un'" or "l'", we want ZERO space. Otherwise ONE space.
    sep = "" if article.endswith("'") else " "
    
    # Dynamic Replacement into the JSON template
    # Template Example: "{name} è {article}{sep}{profession} {nationality}."
    
    sentence = structure.replace("{name}", name)
    sentence = sentence.replace("{article}", article)
    sentence = sentence.replace("{sep}", sep) 
    sentence = sentence.replace("{profession}", final_prof)
    sentence = sentence.replace("{nationality}", final_nat)
    
    # Sanity cleanup (remove double spaces if article was empty)
    sentence = sentence.replace("  ", " ").strip()
    
    return sentence
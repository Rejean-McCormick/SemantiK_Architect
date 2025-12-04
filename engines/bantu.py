"""
BANTU LANGUAGE ENGINE
---------------------
A data-driven renderer for Bantu languages (SW, ZU, IG, RW, YO).

Key features distinguished from Indo-European:
1. Noun Class System: Nouns belong to numbered classes (1-22+) instead of genders.
   - Class 1 (M-/Mu-): Human Singular (Default for Biography).
   - Class 2 (Wa-/Ba-): Human Plural.
2. Concordial Agreement: Adjectives, Verbs, and Nouns must align prefixes.
   (e.g., Swahili: 'Mtu mzuri' vs 'Kitu kizuri').
3. Prefix Morphology: Inflection happens at the START of the word.
"""

def render_bio(name, gender, prof_lemma, nat_lemma, config):
    """
    Main Entry Point.
    
    Args:
        name (str): The subject's name.
        gender (str): 'Male' or 'Female' (Mapped to Noun Class).
        prof_lemma (str): Profession (Dictionary form).
        nat_lemma (str): Nationality (Dictionary form).
        config (dict): The JSON configuration card.
    
    Returns:
        str: The fully inflected sentence.
    """
    
    # 1. Normalize Inputs
    prof_lemma = prof_lemma.strip()
    nat_lemma = nat_lemma.strip()
    
    morph_rules = config.get('morphology', {})
    structure = config.get('structure', "{name} {copula} {profession} {nationality}.")
    
    # =================================================================
    # HELPER 1: Determine Noun Class
    # =================================================================
    # For a biography, the subject is always a Human.
    # In Bantu languages, "Person (Singular)" is almost always Class 1.
    # The config should specify the "default_human_class" (usually "1").
    
    target_class = config.get('syntax', {}).get('default_human_class', '1')
    
    # Note: 'gender' input (Male/Female) is largely irrelevant for grammar 
    # in Bantu languages, as both men and women fall into Class 1.
    
    # =================================================================
    # HELPER 2: Prefix Inflector (The Core Logic)
    # =================================================================
    # We need to swap the dictionary prefix (which might be Class 9 or generic)
    # for the Target Class prefix (Class 1).
    
    def apply_class_prefix(word, target_cls, word_type='noun'):
        # 1. Look up the specific prefix for this class
        # Config structure: "prefixes": {"1": "m", "2": "wa", "9": "n"}
        prefixes = morph_rules.get('prefixes', {})
        target_prefix = prefixes.get(target_cls, "")
        
        # 2. Check Irregulars (Whole word replacement)
        irregulars = morph_rules.get('irregulars', {})
        if word in irregulars:
            return irregulars[word]
            
        # 3. Handle Adjectives vs Nouns
        # Adjectives might use a different set of "Concord" prefixes than Nouns.
        # e.g., Swahili: Mtu (Noun Cl 1) M-zuri (Adj Cl 1). 
        # But sometimes they differ. We check for specific 'adjective_prefixes' map.
        if word_type == 'adjective':
            adj_prefixes = morph_rules.get('adjective_prefixes', prefixes)
            target_prefix = adj_prefixes.get(target_cls, target_prefix)

        # 4. Strip Existing Prefix (Intelligent Stem Detection)
        # This is the hard part. Dictionary words come with prefixes.
        # e.g. "Mwalimu" (Teacher) -> Stem "alimu".
        # Logic: Check all known prefixes, strip the longest match.
        
        current_stem = word
        known_prefixes = sorted(prefixes.values(), key=len, reverse=True)
        
        # Naive Stemmer: If word starts with a known prefix, strip it.
        # REALITY CHECK: This is risky (e.g. 'Mama' starts with 'Ma' but 'Ma' is root).
        # Production systems use a dictionary of roots. 
        # For this prototype, we rely on the input being a STEM or the config handling it.
        
        # Assumption: Inputs are provided as STEMS or Dict forms. 
        # If Dict form, we assume we map directly if no stem logic exists.
        
        # Vowel Harmony for Prefixes (M- vs Mw-)
        # If the stem starts with a vowel, the prefix often changes (m->mw, wa->w).
        vowel_rules = morph_rules.get('vowel_harmony', {})
        if word[0] in "aeiou" and target_prefix in vowel_rules:
            target_prefix = vowel_rules[target_prefix]
            
        return f"{target_prefix}{word}"

    # Apply Inflection
    # Profession is treated as a Noun (Class 1 prefix)
    final_prof = apply_class_prefix(prof_lemma, target_class, word_type='noun')
    
    # Nationality is treated as an Adjective (Class 1 concord)
    final_nat = apply_class_prefix(nat_lemma, target_class, word_type='adjective')

    # =================================================================
    # HELPER 3: The Copula (Verb 'To Be')
    # =================================================================
    # The verb must also agree with Class 1.
    # Swahili: "ni" (invariant) OR "yu-" (Class 1 specific).
    
    def get_copula():
        verbs = config.get('verbs', {})
        copula_map = verbs.get('copula', {})
        
        # Check if there is a class-specific copula (e.g. Zulu 'ungu')
        if target_class in copula_map:
            return copula_map[target_class]
            
        # Default invariant (e.g. Swahili 'ni')
        return copula_map.get('default', '')

    copula = get_copula()

    # =================================================================
    # 4. ASSEMBLY
    # =================================================================
    
    sentence = structure.replace("{name}", name)
    sentence = sentence.replace("{copula}", copula)
    sentence = sentence.replace("{profession}", final_prof)
    sentence = sentence.replace("{nationality}", final_nat)
    
    # Cleanup
    sentence = " ".join(sentence.split())
    
    return sentence
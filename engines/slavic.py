"""
SLAVIC LANGUAGE ENGINE
----------------------
A data-driven renderer for Slavic languages (RU, PL, CS, UK, SR, HR, BG).

Key features distinguished from Romance/Germanic:
1. Rich Case System: Nouns/Adjectives must be declined (usually Instrumental for predicates).
2. Gendered Verbs: Past tense verbs agree with the subject's gender (e.g., byl/byla).
3. Morphology: Complex suffix stacking and vowel removal (fleeting vowels).
"""

def render_bio(name, gender, prof_lemma, nat_lemma, config):
    """
    Main Entry Point.
    
    Args:
        name (str): The subject's name.
        gender (str): 'Male' or 'Female'.
        prof_lemma (str): Profession in Nominative Singular (Dictionary form).
        nat_lemma (str): Nationality in Nominative Singular.
        config (dict): The JSON configuration card.
    
    Returns:
        str: The fully inflected sentence.
    """
    
    # 1. Normalize Inputs
    gender = gender.lower().strip()
    prof_lemma = prof_lemma.strip()
    nat_lemma = nat_lemma.strip()
    
    morph_rules = config.get('morphology', {})
    structure = config.get('structure', "{name} {verb} {nationality} {profession}.")
    
    # =================================================================
    # HELPER 1: Gender Derivation (Feminization)
    # =================================================================
    # First, we must convert the base lemma (usually Male Nominative)
    # to the Subject's gender (Female Nominative) before we apply cases.
    
    def get_gendered_nominative(word, target_gender, is_adjective=False):
        if target_gender == 'male':
            return word
            
        # Check Irregulars
        irregulars = morph_rules.get('irregulars', {})
        if word in irregulars:
            return irregulars[word]
            
        # Apply Feminizing Suffixes to Nominative
        # e.g., Russian: -tel -> -telnitsa, Polish: -arz -> -arka
        suffix_key = 'adjective_suffixes' if is_adjective else 'noun_suffixes'
        rules = morph_rules.get('gender_inflection', {}).get(suffix_key, [])
        
        # Sort by length to match specific endings first
        rules = sorted(rules, key=lambda x: len(x['ends_with']), reverse=True)
        
        for rule in rules:
            if word.endswith(rule['ends_with']):
                stem = word[:-len(rule['ends_with'])]
                return stem + rule['replace_with']
                
        # Fallback (Naive appending 'a' is common in Slavic but dangerous without rules)
        # We rely on the config being robust.
        return word

    # Get the Nominative forms for the Subject's gender
    prof_nom = get_gendered_nominative(prof_lemma, gender, is_adjective=False)
    nat_nom = get_gendered_nominative(nat_lemma, gender, is_adjective=True)

    # =================================================================
    # HELPER 2: Case Declension (The Slavic Hard Part)
    # =================================================================
    # "X was Y". In Russian/Polish, Y must be INSTRUMENTAL case.
    # In Bulgarian/Serbian, Y might be NOMINATIVE.
    # The config['syntax']['predicative_case'] tells us which case to use.
    
    target_case = config.get('syntax', {}).get('predicative_case', 'nominative')
    
    def declinate(word, case, grammatical_gender):
        if case == 'nominative':
            return word
            
        # Look up declension rules for this specific case + gender combination
        # e.g., config['morphology']['cases']['instrumental']['f']
        declension_rules = morph_rules.get('cases', {}).get(case, {}).get(grammatical_gender, [])
        
        # Sort rules
        declension_rules = sorted(declension_rules, key=lambda x: len(x['ends_with']), reverse=True)
        
        for rule in declension_rules:
            if word.endswith(rule['ends_with']):
                stem = word[:-len(rule['ends_with'])]
                return stem + rule['replace_with']
        
        return word

    # Determine Grammatical Gender of the word (for declension logic)
    # Usually maps to Natural Gender for people, but we need simple logic keys ('m', 'f')
    gram_gender = 'f' if gender == 'female' else 'm'

    final_prof = declinate(prof_nom, target_case, gram_gender)
    final_nat = declinate(nat_nom, target_case, gram_gender)

    # =================================================================
    # HELPER 3: Verb Agreement
    # =================================================================
    # Slavic past tense verbs change based on gender (byl / byla / bylo)
    
    def get_verb():
        verbs = config.get('verbs', {})
        # Check if we need "was" (past) or "is" (present)
        # For biography, we usually default to Past, but let's look for a 'copula' key
        copula = verbs.get('copula', {})
        
        # If the language drops the copula in present tense (Russian "She scientist"), 
        # the config might return empty string.
        
        if gender in copula:
            return copula[gender]
        return copula.get('default', '')

    verb = get_verb()

    # =================================================================
    # 4. ASSEMBLY
    # =================================================================
    
    sentence = structure.replace("{name}", name)
    sentence = sentence.replace("{verb}", verb)
    sentence = sentence.replace("{nationality}", final_nat)
    sentence = sentence.replace("{profession}", final_prof)
    
    # Cleanup extra spaces (e.g. if verb is empty in Russian Present Tense)
    sentence = " ".join(sentence.split())
    
    return sentence
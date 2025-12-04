"""
INDO-ARYAN LANGUAGE ENGINE
--------------------------
A data-driven renderer for Indo-Aryan languages (HI, BN, UR, PA, MR).

Key features distinguished from Indo-European:
1. SOV Word Order: Subject - Predicate - Verb (Copula comes last).
2. Gender Agreement: Strong in Hindi/Urdu (Adjectives change), 
   weak/absent in Bengali (Adjectives invariant).
3. Zero Copula: Bengali/Marathi often drop "is" in present tense equations.
4. Honorifics: Verbs/Copulas often change based on respect level (assumed High/Formal for biographies).
"""

def render_bio(name, gender, prof_lemma, nat_lemma, config):
    """
    Main Entry Point.
    
    Args:
        name (str): The subject's name.
        gender (str): 'Male' or 'Female'.
        prof_lemma (str): Profession (Masculine Singular Base).
        nat_lemma (str): Nationality (Masculine Singular Base).
        config (dict): The JSON configuration card.
    
    Returns:
        str: The fully inflected sentence.
    """
    
    # 1. Normalize Inputs
    gender = gender.lower().strip()
    prof_lemma = prof_lemma.strip()
    nat_lemma = nat_lemma.strip()
    
    morph_rules = config.get('morphology', {})
    structure = config.get('structure', "{name} {nationality} {profession} {copula}.")
    
    # =================================================================
    # HELPER 1: Gender Inflection (Nouns & Adjectives)
    # =================================================================
    # Hindi: 'aa' endings usually become 'ii' for feminine (Larka -> Larki).
    # Bengali: Specific suffixes like '-a' or '-i' (Chhatro -> Chhatri).
    
    def inflect_gender(word, target_gender, part_of_speech='noun'):
        if target_gender == 'male':
            return word
            
        # Check if this language/POS inflects for gender at all
        # (e.g. Bengali adjectives usually don't)
        inflects = config.get('syntax', {}).get(f'{part_of_speech}_gender_agreement', True)
        if not inflects:
            return word

        # Check Irregulars
        irregulars = morph_rules.get('irregulars', {})
        if word in irregulars:
            return irregulars[word]
            
        # Apply Suffix Rules
        # config['morphology']['suffixes']
        suffixes = morph_rules.get('suffixes', [])
        # Sort by length descending
        sorted_suffixes = sorted(suffixes, key=lambda x: len(x.get('ends_with', '')), reverse=True)
        
        for rule in sorted_suffixes:
            ending = rule.get('ends_with', '')
            replacement = rule.get('replace_with', '')
            
            if word.endswith(ending):
                return word[:-len(ending)] + replacement
                
        # Generic Fallback (Hindi/Urdu style)
        # If word ends in 'aa', change to 'ii'
        if config.get('code') in ['hi', 'ur'] and word.endswith('aa'):
            return word[:-2] + 'ii'
            
        return word

    # Apply inflection
    # Nationality is treated as an adjective
    final_nat = inflect_gender(nat_lemma, gender, part_of_speech='adjective')
    # Profession is treated as a noun
    final_prof = inflect_gender(prof_lemma, gender, part_of_speech='noun')

    # =================================================================
    # HELPER 2: The Copula (The 'Is' Verb)
    # =================================================================
    # Handles "Zero Copula" logic (Bengali) vs Explicit Copula (Hindi).
    # Also handles Honorifics if defined (Biographies usually use Formal).
    
    def get_copula():
        verbs = config.get('verbs', {})
        copula_defs = verbs.get('copula', {})
        
        # 1. Check for Zero Copula rule
        # e.g. Bengali: "She [is] writer" -> "She writer" (Copula dropped)
        if copula_defs.get('zero_copula_in_present', False):
            return ""
            
        # 2. Check for Honorific/Formal form (Default for Bio)
        # Hindi: 'hai' (casual) vs 'hain' (formal/plural)
        # We assume 'formal' is the target for Wikipedia
        if 'formal' in copula_defs:
            return copula_defs['formal']
            
        # 3. Fallback to Gendered Copula (Marathi/some dialects)
        if gender in copula_defs:
            return copula_defs[gender]
            
        return copula_defs.get('default', "")

    copula = get_copula()

    # =================================================================
    # HELPER 3: Postpositions / Particles (Optional)
    # =================================================================
    # While "X is Y" is simple, some languages might require an ergative 
    # marker or specific topic marker on the Subject (like Japanese 'wa', but for IA).
    # Usually Nominative is unmarked in IA, so we leave Name as is.
    
    # =================================================================
    # 4. ASSEMBLY
    # =================================================================
    
    # Standard SOV Template: "{name} {nationality} {profession} {copula}."
    
    sentence = structure.replace("{name}", name)
    sentence = sentence.replace("{nationality}", final_nat)
    sentence = sentence.replace("{profession}", final_prof)
    sentence = sentence.replace("{copula}", copula)
    
    # Clean up double spaces (vital for Zero Copula languages)
    sentence = " ".join(sentence.split())
    
    # Ensure final punctuation (some scripts might use Danda '।')
    punctuation = config.get('syntax', {}).get('punctuation', '.')
    if not sentence.endswith(punctuation):
        sentence += punctuation
        
    return sentence
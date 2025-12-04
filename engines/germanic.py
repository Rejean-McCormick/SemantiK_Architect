"""
GERMANIC LANGUAGE ENGINE
------------------------
A data-driven renderer for Germanic languages (EN, DE, NL, SV, DA, NO).

Key features distinguished from Romance:
1. Adjective Declension: Complex rules for adjectives based on gender/article (e.g., German 'ein guter Mann' vs 'der gute Mann').
2. Gender Systems: Handles 3-gender (Der/Die/Das) and 2-gender (En/Ett) systems.
3. Compound Nouns: Support for joining nouns (optional).
4. Phonetic Articles: Specific handling for English 'a/an'.
"""

def render_bio(name, gender, prof_lemma, nat_lemma, config):
    """
    Main Entry Point.
    
    Args:
        name (str): The subject's name.
        gender (str): 'Male' or 'Female'.
        prof_lemma (str): The profession (e.g., "Lehrer" / "Teacher").
        nat_lemma (str): The nationality adjective (e.g., "Deutsch" / "German").
        config (dict): The JSON configuration card.
    
    Returns:
        str: The fully inflected sentence.
    """
    
    # 1. Normalize Inputs
    gender = gender.lower().strip()
    prof_lemma = prof_lemma.strip() # Don't lowercase German nouns!
    nat_lemma = nat_lemma.strip()   # Don't lowercase German adjectives (if nominalized)!
    
    # German Noun Capitalization Check
    # If the language requires capitalized nouns (DE), we ensure the lemma matches.
    # Otherwise, we might lowercase it depending on the language style.
    if config.get('casing', {}).get('capitalize_nouns', False):
        prof_lemma = prof_lemma.capitalize()
    else:
        prof_lemma = prof_lemma  # Keep original casing or lower() if strictly EN/NL
    
    morph_rules = config.get('morphology', {})
    article_rules = config.get('articles', {})
    adj_rules = config.get('adjectives', {})
    phonetics = config.get('phonetics', {})
    structure = config.get('structure', "{name} {is_verb} {article} {nationality} {profession}.")

    # =================================================================
    # HELPER 1: Profession Morphology (Feminization)
    # =================================================================
    def inflect_profession_gender(word, target_gender):
        if target_gender == 'male':
            return word
            
        # Check Irregulars
        irregulars = morph_rules.get('irregulars', {})
        # Check case-insensitive key match
        for k, v in irregulars.items():
            if k.lower() == word.lower():
                return v
        
        # Apply Suffixes (e.g., DE: -in, NL: -es)
        suffixes = morph_rules.get('gender_suffixes', [])
        sorted_suffixes = sorted(suffixes, key=lambda x: len(x['ends_with']), reverse=True)
        
        for rule in sorted_suffixes:
            if word.endswith(rule['ends_with']):
                return word[:-len(rule['ends_with'])] + rule['replace_with']
        
        # Generic Appending (Common in German: Lehrer -> Lehrerin)
        generic_suffix = morph_rules.get('generic_feminine_suffix', "")
        if generic_suffix:
            return word + generic_suffix
            
        return word

    final_prof = inflect_profession_gender(prof_lemma, gender)

    # =================================================================
    # HELPER 2: Determine Grammatical Gender of the *Word*
    # =================================================================
    # In Germanic languages, the article depends on the gender of the NOUN,
    # not necessarily the gender of the PERSON (though they often align).
    
    def get_word_gender(word, natural_gender):
        # 1. Config can explicitly map suffixes to grammatical genders
        # e.g., words ending in '-in' are Feminine in German.
        # e.g., words ending in '-chen' are Neuter in German.
        gram_gender_map = morph_rules.get('grammatical_gender_map', {})
        
        for suffix, g_gender in gram_gender_map.items():
            if word.endswith(suffix):
                return g_gender
        
        # 2. Fallback: For professions, Grammatical Gender usually == Natural Gender
        # (Actor -> Male/Masculine, Actress -> Female/Feminine)
        if natural_gender == 'male':
            return 'm'
        elif natural_gender == 'female':
            return 'f'
        return 'n' # Default/Neuter

    word_gender = get_word_gender(final_prof, gender)

    # =================================================================
    # HELPER 3: Adjective Declension (The Hard Part)
    # =================================================================
    # Germanic adjectives change based on:
    # 1. Context (Indefinite article used here)
    # 2. Gender of the noun
    
    def inflect_adjective(adj, noun_gender):
        # If language has no adjective inflection (English), return raw
        if not adj_rules.get('inflects', False):
            return adj
            
        # Get rules for "Indefinite" context (Mixed declension)
        # e.g., German: Ein (M) -> guter (M-Ending)
        endings = adj_rules.get('indefinite_endings', {})
        suffix = endings.get(noun_gender, "")
        
        return adj + suffix

    final_nat = inflect_adjective(nat_lemma, word_gender)

    # =================================================================
    # HELPER 4: Article Selection (Phonetic & Grammatical)
    # =================================================================
    def get_article(next_word, noun_gender):
        # 1. English Special Case (A vs An)
        if config.get('code') == 'en':
            vowels = "aeiou"
            # Very naive heuristic, production needs a phonetic dictionary
            if next_word[0].lower() in vowels:
                return "an"
            return "a"
            
        # 2. Standard Gender Lookup (DE/NL/SV)
        articles_map = article_rules.get('indefinite', {})
        return articles_map.get(noun_gender, "")

    # In "X is a Y Z", the article precedes the Adjective (Nationality)
    # So we check the Nationality for phonetic triggers (like English 'an American')
    target_for_article = final_nat if final_nat else final_prof
    article = get_article(target_for_article, word_gender)

    # =================================================================
    # 5. ASSEMBLY
    # =================================================================
    
    sentence = structure.replace("{name}", name)
    sentence = sentence.replace("{is_verb}", config.get('verbs', {}).get('is', 'is'))
    sentence = sentence.replace("{article}", article)
    sentence = sentence.replace("{nationality}", final_nat)
    sentence = sentence.replace("{profession}", final_prof)
    
    # Cleanup extra spaces (if article is empty)
    sentence = " ".join(sentence.split())
    
    return sentence
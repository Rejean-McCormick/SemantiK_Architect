"""
IRANIC LANGUAGE ENGINE
----------------------
A data-driven renderer for Iranic languages (FA, PS, KU, TG).

Key features distinguished from Indo-European:
1. The Ezafe (Izafe): A linker suffix connecting Noun + Adjective.
   (e.g., Persian: 'Ketab-e khoob' = Book [link] good).
2. Gender Split: 
   - Persian/Tajik: Gender Neutral (No inflection).
   - Pashto/Kurdish: Gendered (Nouns/Adjectives change).
3. Indefiniteness: Often a suffix '-i' (Ya-ye Vahdat) attached to the noun group.
4. SOV Order: Copula comes last.
"""

def render_bio(name, gender, prof_lemma, nat_lemma, config):
    """
    Main Entry Point.
    
    Args:
        name (str): The subject's name.
        gender (str): 'Male' or 'Female'.
        prof_lemma (str): Profession (Base form).
        nat_lemma (str): Nationality (Base form).
        config (dict): The JSON configuration card.
    
    Returns:
        str: The fully inflected sentence.
    """
    
    # 1. Normalize Inputs
    gender = gender.lower().strip()
    prof_lemma = prof_lemma.strip()
    nat_lemma = nat_lemma.strip()
    
    morph_rules = config.get('morphology', {})
    phonetics = config.get('phonetics', {})
    structure = config.get('structure', "{name} {profession} {nationality} {copula}.")
    
    # =================================================================
    # HELPER 1: Gender Inflection (Pashto/Kurdish only)
    # =================================================================
    # Persian (fa) ignores this. Pashto (ps) uses it heavily.
    
    def inflect_gender(word, target_gender):
        # Check if language has gender (defined in JSON)
        if not config.get('syntax', {}).get('has_gender', False):
            return word
            
        if target_gender == 'male':
            return word
            
        # Apply Suffixes (e.g. Pashto -a for feminine)
        suffixes = morph_rules.get('gender_suffixes', [])
        for rule in suffixes:
            if word.endswith(rule['ends_with']):
                stem = word[:-len(rule['ends_with'])]
                return stem + rule['replace_with']
                
        # Generic Fallback
        default = morph_rules.get('default_fem_suffix', "")
        if default:
            return word + default
            
        return word

    final_prof = inflect_gender(prof_lemma, gender)
    final_nat = inflect_gender(nat_lemma, gender)

    # =================================================================
    # HELPER 2: The Ezafe (Ezofe) Constructor
    # =================================================================
    # Connects Profession (Head) to Nationality (Modifier).
    # Logic: If word ends in Vowel -> -ye. If Consonant -> -e.
    # Note: In Persian script, short 'e' is often unwritten (Zero Width Non-Joiner),
    # but for transliteration or precise rendering, we calculate it.
    
    def apply_ezafe(head_noun):
        # Check if Ezafe is used in this language
        if not config.get('syntax', {}).get('uses_ezafe', False):
            return head_noun
            
        # Get vowels list
        vowels = phonetics.get('vowels', "aeiou")
        last_char = head_noun[-1].lower()
        
        # Determine suffix
        if last_char in vowels or last_char in ['h', 'eh']: # 'Silent h' counts as vowel in Persian
            suffix = morph_rules.get('ezafe_vowel', "ye") # e.g. "Daneshmand-e"
        else:
            suffix = morph_rules.get('ezafe_consonant', "e")
            
        # Check if we need a connector (like ZWNJ or hyphen)
        connector = config.get('syntax', {}).get('ezafe_connector', "-")
        
        return f"{head_noun}{connector}{suffix}"

    # Apply Ezafe to the profession because it is followed by Nationality
    # "Scientist [of] Polish"
    prof_with_ezafe = apply_ezafe(final_prof)

    # =================================================================
    # HELPER 3: Indefiniteness (Ya-ye Vahdat)
    # =================================================================
    # Persian often adds '-i' to indicate "A/An". 
    # It usually attaches to the end of the noun phrase or the head noun depending on style.
    # For "A Polish Scientist": "Daneshmand-e Lahestani-i" OR "Yek Daneshmand-e..."
    
    def apply_indefinite(noun_phrase):
        strategy = config.get('syntax', {}).get('indefinite_strategy', 'none')
        
        if strategy == 'suffix':
            # Add suffix to the end of the phrase
            suffix = morph_rules.get('indefinite_suffix', "i")
            return f"{noun_phrase}{suffix}"
            
        elif strategy == 'prefix':
            # Add separate word (e.g. "Yek")
            particle = config.get('articles', {}).get('indefinite', "")
            return f"{particle} {noun_phrase}"
            
        return noun_phrase

    # =================================================================
    # HELPER 4: The Copula
    # =================================================================
    # Persian: 'ast' (is)
    
    def get_copula():
        verbs = config.get('verbs', {})
        return verbs.get('copula', {}).get('default', "")

    copula = get_copula()

    # =================================================================
    # 5. ASSEMBLY
    # =================================================================
    
    # We construct the Noun Phrase first to handle Ezafe logic correctly
    # Standard: Profession + Ezafe + Nationality
    noun_phrase = f"{prof_with_ezafe} {final_nat}"
    
    # Apply Indefiniteness to the whole group if needed (e.g. Persian suffix style)
    # Note: If suffix style is used, it usually attaches to the adjective in modern Persian
    # "Daneshmand-e Lahestani-i"
    noun_phrase_final = apply_indefinite(noun_phrase)
    
    # Fill Template
    sentence = structure.replace("{name}", name)
    sentence = sentence.replace("{predicate}", noun_phrase_final)
    # Fallback if structure uses individual tags
    sentence = sentence.replace("{profession}", prof_with_ezafe)
    sentence = sentence.replace("{nationality}", final_nat)
    sentence = sentence.replace("{copula}", copula)
    
    # Cleanup
    sentence = " ".join(sentence.split())
    
    return sentence
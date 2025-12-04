"""
CELTIC LANGUAGE ENGINE
----------------------
A data-driven renderer for Celtic languages (CY, GA, GD, KW, BR).

Key features distinguished from Indo-European:
1. VSO Word Order: Verb - Subject - Object/Predicate.
   (e.g., Welsh: "Mae Marie yn wyddonydd" -> "Is Marie a scientist").
2. Initial Consonant Mutation: The first letter of a word changes based on context.
   (Soft, Nasal, Aspirate/Spirant, Eclipsis, Lenition).
3. Predicative Particles: Linking words (yn, ina) often trigger mutations.
4. Adjective Mutation: Adjectives modifying Feminine Singular nouns often undergo Soft Mutation.
"""

def render_bio(name, gender, prof_lemma, nat_lemma, config):
    """
    Main Entry Point.
    
    Args:
        name (str): The subject's name.
        gender (str): 'Male' or 'Female'.
        prof_lemma (str): Profession (Radical/Base form).
        nat_lemma (str): Nationality (Radical/Base form).
        config (dict): The JSON configuration card.
    
    Returns:
        str: The fully inflected sentence.
    """
    
    # 1. Normalize Inputs
    gender = gender.lower().strip()
    prof_lemma = prof_lemma.strip()
    nat_lemma = nat_lemma.strip()
    
    morph_rules = config.get('morphology', {})
    mutation_rules = config.get('mutations', {})
    structure = config.get('structure', "{copula} {name} {particle} {profession} {nationality}.")
    
    # =================================================================
    # HELPER 1: Mutation Engine (The Core Logic)
    # =================================================================
    # Applies changes like p->b, t->d, c->g based on the mutation type.
    
    def mutate(word, mutation_type):
        if not mutation_type or mutation_type == 'radical':
            return word
            
        # Get specific rules for this mutation type (e.g., 'soft', 'nasal')
        # config['mutations']['rules']['soft'] -> {"p": "b", "c": "g", ...}
        rules = mutation_rules.get('rules', {}).get(mutation_type, {})
        
        # Check simple replacement (First letter)
        first_char = word[0].lower()
        
        # Handle multi-char processing if needed (e.g. "Gw" -> "W" in Welsh soft)
        # We sort keys by length descending to match "Gw" before "G"
        sorted_triggers = sorted(rules.keys(), key=len, reverse=True)
        
        for trigger in sorted_triggers:
            if word.lower().startswith(trigger):
                # Match case of original word (Title or Lower)
                is_upper = word[0].isupper()
                
                # Perform substitution
                replacement = rules[trigger]
                
                # "Empty" replacement means deletion (e.g. G -> nothing)
                if replacement == "":
                    remainder = word[len(trigger):]
                    return remainder.capitalize() if is_upper else remainder
                
                stem = word[len(trigger):]
                new_start = replacement.capitalize() if is_upper else replacement
                return new_start + stem
                
        return word

    # =================================================================
    # HELPER 2: Gender Inflection (Suffixes)
    # =================================================================
    # Some Celtic nouns change form for gender (e.g. -es suffix in Welsh)
    
    def inflect_form(word, target_gender):
        if target_gender == 'male':
            return word
            
        suffixes = morph_rules.get('gender_suffixes', [])
        for rule in suffixes:
            if word.endswith(rule['ends_with']):
                stem = word[:-len(rule['ends_with'])]
                return stem + rule['replace_with']
        
        # Generic fallback suffix (e.g., Welsh -es)
        default_suffix = morph_rules.get('default_fem_suffix', "")
        return word + default_suffix

    # Apply Form Inflection (Base form before mutation)
    prof_form = inflect_form(prof_lemma, gender)
    nat_form = inflect_form(nat_lemma, gender)

    # =================================================================
    # HELPER 3: Predicative Particle Logic
    # =================================================================
    # In Welsh, 'yn' triggers Soft Mutation on the following word (Predicate).
    # In Irish, 'ina' triggers Eclipsis/Lenition depending on dialect/grammar.
    
    def get_particle_and_mutate_next(next_word):
        syntax = config.get('syntax', {})
        particle = syntax.get('predicative_particle', '')
        
        # Check if particle causes mutation
        # config['syntax']['particle_mutation'] -> "soft"
        mutation_type = syntax.get('particle_mutation', None)
        
        mutated_word = mutate(next_word, mutation_type)
        
        return particle, mutated_word

    # Get particle and mutate the Profession
    # e.g. Welsh: 'yn' + 'athro' -> 'yn athro' (vowel, no change) or 'pobydd' -> 'yn bobydd'
    particle, final_prof = get_particle_and_mutate_next(prof_form)

    # =================================================================
    # HELPER 4: Adjective Mutation (Noun-Adjective Agreement)
    # =================================================================
    # If the Noun (Profession) is Feminine Singular, the Adjective (Nationality)
    # usually undergoes Soft Mutation.
    
    def process_adjective(adj, noun_gender):
        syntax = config.get('syntax', {})
        
        # Check if language requires mutation for Fem SG adjectives
        # config['syntax']['fem_adj_mutation'] -> "soft"
        if noun_gender == 'female':
            mut_type = syntax.get('fem_adj_mutation', None)
            return mutate(adj, mut_type)
            
        return adj

    final_nat = process_adjective(nat_form, gender)

    # =================================================================
    # HELPER 5: The Copula (Verb 'To Be')
    # =================================================================
    # Welsh: 'Mae' (Present), 'Oedd' (Past).
    # Irish: 'Is' (Present), 'Ba' (Past).
    
    def get_copula():
        verbs = config.get('verbs', {})
        copula_map = verbs.get('copula', {})
        
        # Default to present tense for Bio
        return copula_map.get('present', copula_map.get('default', ''))

    copula = get_copula()

    # =================================================================
    # 6. ASSEMBLY
    # =================================================================
    
    sentence = structure.replace("{name}", name)
    sentence = sentence.replace("{copula}", copula)
    sentence = sentence.replace("{particle}", particle)
    sentence = sentence.replace("{profession}", final_prof)
    sentence = sentence.replace("{nationality}", final_nat)
    
    # Clean up double spaces
    sentence = " ".join(sentence.split())
    
    return sentence
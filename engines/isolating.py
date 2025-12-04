"""
ISOLATING LANGUAGE ENGINE
-------------------------
A data-driven renderer for Isolating/Analytic languages (ZH, VI, TH).

Key features distinguished from Inflectional languages:
1. No Morphology: Words do not change form (no plurals, no gender suffixes).
2. Classifiers: Nouns require specific counter words (e.g., 'yi ge ren').
3. Particles: Tense/Aspect is handled by separate particles (e.g., 'le', 'da').
4. Strict Word Order: SVO is rigid.
"""

def render_bio(name, gender, prof_lemma, nat_lemma, config):
    """
    Main Entry Point.
    
    Args:
        name (str): The subject's name.
        gender (str): 'Male' or 'Female' (Used for pronoun selection, not inflection).
        prof_lemma (str): Profession (Invariant root).
        nat_lemma (str): Nationality (Invariant root).
        config (dict): The JSON configuration card.
    
    Returns:
        str: The constructed sentence.
    """
    
    # 1. Normalize Inputs
    # Isolating languages don't usually have "lemmas" vs "inflected forms",
    # but we strip whitespace just in case.
    prof = prof_lemma.strip()
    nat = nat_lemma.strip()
    
    structure = config.get('structure', "{name} {copula} {nationality} {profession}.")
    
    # =================================================================
    # HELPER 1: The Copula (Verb 'To Be')
    # =================================================================
    # Chinese: 'shì' (是)
    # Vietnamese: 'là'
    # Thai: 'pen' (เป็น)
    
    def get_copula():
        verbs = config.get('verbs', {})
        # Isolating languages usually have a single invariant copula
        return verbs.get('copula', {}).get('default', "")

    copula = get_copula()

    # =================================================================
    # HELPER 2: Classifiers (The Hard Part)
    # =================================================================
    # In "X is a Y", isolating languages often require "X is [ONE] [CLASSIFIER] Y".
    # e.g. "He is a teacher" -> "Ta shi yi **ge** laoshi" (He is one unit teacher).
    
    def apply_classifier(noun_phrase):
        # Check if the config requires a classifier for indefinite predicative nouns
        syntax = config.get('syntax', {})
        if not syntax.get('requires_classifier_in_predicate', False):
            return noun_phrase
            
        # Get the default classifier for people
        # config['classifiers']['person'] -> "gè" (Chinese) / "người" (Vietnamese)
        classifiers = config.get('classifiers', {})
        person_classifier = classifiers.get('person', '')
        
        # Get the word for "One" or "A"
        # config['articles']['indefinite'] -> "yī" (Chinese) / "một" (Vietnamese)
        article = config.get('articles', {}).get('indefinite', '')
        
        if article and person_classifier:
            # Result: "yi ge" + " " + "laoshi"
            return f"{article} {person_classifier} {noun_phrase}"
            
        return noun_phrase

    # =================================================================
    # HELPER 3: Noun Phrase Construction
    # =================================================================
    # We combine Nationality + Profession.
    # Chinese: [Nationality] [Profession] (Meiguo ren)
    # Vietnamese: [Profession] [Nationality] (Nguoi My)
    
    def build_noun_phrase():
        order = config.get('syntax', {}).get('adjective_order', 'pre') # 'pre' or 'post'
        
        if order == 'pre':
            # Adjective before Noun (Chinese/English style)
            # "Meiguo" + " " + "Kexuejia"
            return f"{nat} {prof}"
        else:
            # Noun before Adjective (Vietnamese/Thai style)
            # "Nha khoa hoc" + " " + "My"
            return f"{prof} {nat}"

    # Build the core Noun Phrase (e.g. "American Scientist")
    np = build_noun_phrase()
    
    # Apply the Classifier/Article wrapper to the whole NP
    # "yī gè [American Scientist]"
    final_predicate = apply_classifier(np)

    # =================================================================
    # 4. ASSEMBLY
    # =================================================================
    
    # Template: "{name} {copula} {predicate}."
    # We override the default structure if the config provides one that uses {predicate}
    # instead of separate {profession} {nationality} tags, because word order was handled above.
    
    if "{predicate}" in structure:
        sentence = structure.replace("{name}", name)
        sentence = sentence.replace("{copula}", copula)
        sentence = sentence.replace("{predicate}", final_predicate)
    else:
        # Fallback for simple templates
        sentence = structure.replace("{name}", name)
        sentence = sentence.replace("{copula}", copula)
        sentence = sentence.replace("{profession}", prof) # Raw
        sentence = sentence.replace("{nationality}", nat) # Raw
    
    # Cleanup
    sentence = " ".join(sentence.split())
    
    return sentence
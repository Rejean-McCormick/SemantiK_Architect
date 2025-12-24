-- Tier 1 Concrete Grammar (French)
-- Implements AbstractWiki v2.1 using the GF Resource Grammar Library
concrete WikiFra of AbstractWiki = open SyntaxFre, ParadigmsFre, SymbolicFre, Prelude in {

  lincat
    Entity = NP;      -- Noun Phrase
    Property = AP;    -- Adjectival Phrase
    Fact = S;         -- Sentence
    Predicate = VP;   -- Verb Phrase
    Modifier = Adv;   -- Adverb ("rapidement") - Must be Adv, not AdV
    Value = Str;      -- Raw String

  lin
    -- Core Semantics
    mkFact subj pred = mkS (mkCl subj pred);
    mkIsAProperty subj prop = mkS (mkCl subj (mkVP prop));

    -- Specialized Frames
    -- Bio: "Subject is Nationality and Profession"
    -- RGL automatically handles gender agreement (accord) here!
    mkBio name prof nat = mkS (mkCl name (mkVP (mkAP and_Conj nat prof)));

    -- Event: "participer à" (participate in)
    -- FIX: Inlined definitions to prevent 'variable #0 out of scope' error
    mkEvent subj obj = 
      mkS (mkCl subj (mkVP (mkV2 (mkV "participer") (mkPrep "à")) obj));

    -- Modifiers
    FactWithMod fact mod = mkS mod fact;

    -- === THE FIX: Use Symbolic for Raw Strings ===
    -- 'symb' treats the string as a fixed symbol, bypassing morphology rules
    mkLiteral s = symb s;
    mkStrProperty s = mkAP (mkA s);

    -- Type Converters (Identity)
    Entity2NP e = e;
    Property2AP p = p;
    VP2Predicate p = p;

    -- Lexicon
    lex_animal_N = mkNP the_Det (mkN "animal");
    lex_walk_V   = mkVP (mkV "marcher");
    lex_blue_A   = mkAP (mkA "bleu");
}
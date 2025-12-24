-- Tier 1 Concrete Grammar (English)
-- FIXED: Added 'StructuralEng' to imports so in_Prep and and_Conj are defined
concrete WikiEng of AbstractWiki = open SyntaxEng, ParadigmsEng, SymbolicEng, StructuralEng, Prelude in {

  lincat
    Entity = NP;
    Property = AP;
    Fact = S;
    Predicate = VP;
    Modifier = Adv;   -- Must be 'Adv' to work with mkS
    Value = SS;       -- Changed from Str to SS (String Structure) for better RGL compatibility

  lin
    -- Core Semantics
    mkFact subj pred = mkS (mkCl subj pred);
    mkIsAProperty subj prop = mkS (mkCl subj (mkVP prop));

    -- Bio: "Subject is Nationality and Profession"
    -- StructuralEng provides 'and_Conj'
    mkBio name prof nat = mkS (mkCl name (mkVP (mkAP and_Conj nat prof)));

    -- Event: "Subject participated in Object"
    -- StructuralEng provides 'in_Prep', fixing the scope error
    mkEvent subj obj = 
      mkS (mkCl subj (mkVP (mkV2 (mkV "participate") in_Prep) obj));

    -- Modifiers
    FactWithMod fact mod = mkS mod fact;

    -- String Bridges (Using Symbolic to avoid gluing crash)
    -- FIXED: accessing the .s field because Value is a record
    mkLiteral s = symb s.s;
    mkStrProperty s = mkAP (mkA s.s);

    -- Identity Converters
    Entity2NP e = e;
    Property2AP p = p;
    VP2Predicate p = p;

    -- Lexicon
    lex_animal_N = mkNP the_Det (mkN "animal");
    lex_walk_V   = mkVP (mkV "walk");
    lex_blue_A   = mkAP (mkA "blue");
}
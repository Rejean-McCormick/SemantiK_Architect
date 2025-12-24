concrete WikiQue of AbstractWiki = open Prelude in {
  lincat
    Entity = Str;
    Property = Str;
    Fact = Str;
    Predicate = Str;
    Modifier = Str;
    Value = Str;

  lin
    -- Semantic Constructor Implementation
    mkFact subj pred = subj ++ pred;
    
    -- Hardcoded stub for 'is a property'
    mkIsAProperty subj prop = subj ++ "is" ++ prop;
    
    FactWithMod fact mod = fact ++ mod;
    
    -- Lexical Stubs
    mkLiteral s = s;
    
    -- Type Converters
    Entity2NP e = e;
    Property2AP p = p;
    VP2Predicate p = p;

    -- Required Lexicon Stubs
    lex_animal_N = "animal";
    lex_walk_V = "walks";
    lex_blue_A = "blue";
}

abstract AbstractWiki = {
  cat Entity; Property; Fact; Predicate; Modifier; Value;
  fun
    -- Core Semantics
    mkFact : Entity -> Predicate -> Fact;
    mkIsAProperty : Entity -> Property -> Fact;

    -- Specialized Frames
    mkBio : Entity -> Property -> Property -> Fact;
    mkEvent : Entity -> Entity -> Fact;

    -- Modifiers
    FactWithMod : Fact -> Modifier -> Fact;

    -- === THE FIX: String Converters ===
    -- Bridge: String -> Entity (For Names)
    mkLiteral : Value -> Entity;
    
    -- Bridge: String -> Property (For Profession/Nationality)
    mkStrProperty : Value -> Property;  -- <--- ADD THIS LINE
    
    -- Type Casts
    Entity2NP : Entity -> Entity; 
    Property2AP : Property -> Property; 
    VP2Predicate : Predicate -> Predicate;

    -- Lexicon Stubs
    lex_animal_N : Entity; 
    lex_walk_V : Predicate; 
    lex_blue_A : Property;
}
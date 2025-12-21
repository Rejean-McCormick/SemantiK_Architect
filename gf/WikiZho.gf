concrete WikiZho of AbstractWiki = WikiI ** open SyntaxZho, ParadigmsZho in {
  lin
    lex_animal_N = mkNP (mkN "animal"); -- Placeholder
    lex_walk_V = mkVP (mkV "walk");     -- Placeholder
    lex_blue_A = mkAP (mkA "blue");     -- Placeholder
    mkLiteral v = mkNP (mkN v.s);       -- Simple string wrapper
};

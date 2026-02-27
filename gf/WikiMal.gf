concrete WikiMal of SemantikArchitect = open SyntaxMal, ParadigmsMal in {
  lincat
    Fact = S ;
    Entity = NP ;
    Predicate = VP ;
  lin
    mkFact s p = mkS (mkCl s p) ;
}
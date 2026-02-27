concrete WikiGus of SemantikArchitect = open SyntaxGus, ParadigmsGus in {
  lincat
    Fact = S ;
    Entity = NP ;
    Predicate = VP ;
  lin
    mkFact s p = mkS (mkCl s p) ;
}
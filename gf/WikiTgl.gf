concrete WikiTgl of SemantikArchitect = open SyntaxTgl, ParadigmsTgl in {
  lincat
    Fact = S ;
    Entity = NP ;
    Predicate = VP ;
  lin
    mkFact s p = mkS (mkCl s p) ;
}
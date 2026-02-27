concrete WikiCym of SemantikArchitect = open SyntaxCym, ParadigmsCym in {
  lincat
    Fact = S ;
    Entity = NP ;
    Predicate = VP ;
  lin
    mkFact s p = mkS (mkCl s p) ;
}
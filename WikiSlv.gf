concrete WikiSlv of Wiki = GrammarSlv, ParadigmsSlv ** open SyntaxSlv, (P = ParadigmsSlv) in {
  lin
    SimpNP cn = mkNP cn ;
    John = mkNP (P.mkPN "John") ; 
    Here = P.mkAdv "here" ;
    apple_N = mkCN (P.mkN "apple") ;
}
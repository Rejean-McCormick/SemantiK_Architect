concrete WikiLit of Wiki = GrammarLit, ParadigmsLit ** open SyntaxLit, (P = ParadigmsLit) in {
  lin
    SimpNP cn = mkNP cn ;
    John = mkNP (P.mkPN "John") ; 
    Here = P.mkAdv "here" ;
    apple_N = mkCN (P.mkN "apple") ;
}
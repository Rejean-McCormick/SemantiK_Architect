concrete WikiSwa of Wiki = GrammarSwa, ParadigmsSwa ** open SyntaxSwa, (P = ParadigmsSwa) in {
  lin
    SimpNP cn = mkNP cn ;
    John = mkNP (P.mkPN "John") ; 
    Here = P.mkAdv "here" ;
    apple_N = mkCN (P.mkN "apple") ;
}
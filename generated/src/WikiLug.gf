concrete WikiLug of AbstractWiki = open Syntax, Paradigms in {
  lincat
    S = Str;
    NP = Str;
    VP = Str;
    Cl = Str;
  lin
    -- Generated via Weighted Topology Factory (SVO)
    mkCl subj verb obj = nsubj ++ root ++ obj;
    mkS clause = clause;
    
    -- Lexical Stubs (Data injected at runtime)
    mkNP s = s;
    mkVP s = s;
}

concrete WikiFre of SemantikArchitect =
  WikiI with (Syntax = SyntaxFre), (Symbolic = SymbolicFre) **
  open Prelude, SyntaxFre, ParadigmsFre, SymbolicFre in {
    flags coding = utf8 ;

    lin
      mkBioProf e p   = ss (e.s ++ "est" ++ p.s) ;
      mkBioNat  e n   = ss (e.s ++ "est" ++ n.s) ;
      mkBioFull e p n = ss (e.s ++ "est" ++ n.s ++ p.s) ;
      mkEvent e ev    = ss (e.s ++ "participe à" ++ ev.s) ;
  };
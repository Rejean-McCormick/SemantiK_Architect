concrete WikiEng of SemantikArchitect =
  WikiI with (Syntax = SyntaxEng), (Symbolic = SymbolicEng) **
  open Prelude, SyntaxEng, ParadigmsEng, SymbolicEng in {
    flags coding = utf8 ;

    lin
      mkBioProf e p =
        ss (e.s ++ " is a " ++ p.s) ;

      mkBioNat e n =
        ss (e.s ++ " is " ++ n.s) ;

      mkBioFull e p n =
        ss (e.s ++ " is a " ++ n.s ++ " " ++ p.s) ;

      mkEvent e ev =
        ss (e.s ++ " participated in " ++ ev.s) ;
  };
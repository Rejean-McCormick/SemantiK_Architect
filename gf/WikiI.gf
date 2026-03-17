incomplete concrete WikiI of SemantikArchitect = open Prelude in {

  lincat
    Statement   = SS ;
    Entity      = SS ;
    Profession  = SS ;
    Nationality = SS ;
    EventObj    = SS ;

  lin
    mkEntityStr s = s ;
    strProf s     = s ;
    strNat s      = s ;
    strEvent s    = s ;

  -- Language-specific surface realization must NOT live here.
  -- Each concrete language module (e.g. WikiEng, WikiFre) must define:
  --   mkBioProf
  --   mkBioNat
  --   mkBioFull
  --   mkEvent
}
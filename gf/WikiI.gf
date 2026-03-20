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

  -- Shared concrete contract:
  -- - WikiI remains language-neutral.
  -- - WikiI owns only shared lincats and language-neutral lexical/string helpers.
  -- - WikiI must NOT own English or French sentence realization.
  --
  -- Concrete language modules such as WikiEng and WikiFre must define:
  --   mkBioProf
  --   mkBioNat
  --   mkBioFull
  --   mkEvent
  --
  -- This prevents hidden EN/FR surface behavior from leaking through shared GF.
}
-- gf/WikiI.gf
-- =========================================================================
-- FUNCTOR IMPLEMENTATION: Defines the concrete realization logic for
-- all languages (I) by leveraging the GF Resource Grammar Library (RGL).
-- This avoids writing 300 separate language files.
--
-- Note: RGL names its concrete syntaxes using 3-letter ISO 639-3 codes
-- (e.g., 'eng', 'fra', 'deu').

-- 1. PARAMETER BLOCK: Define the set of languages this grammar supports.
-- =========================================================================
-- The compiler will iterate over this list and generate a concrete instance
-- for each language, using the RGL rules for that language.

param Language = 
  -- Define your list of target languages here using RGL names (ISO 639-3 codes)
  -- This list must contain all 300+ language codes you intend to support.
  i : [eng, fra, deu, spa, ita, swe, por, rus, zho, jpn] ; 
  -- NOTE: For a real 300-language grammar, you would include every RGL language code.

-- 2. INSTANCE DEFINITION: The Core Concrete Syntax
-- =========================================================================
-- This block implements the abstract functions from AbstractWiki by calling
-- RGL functions. The 'i' refers to the current language in the 'Language' parameter.

instance WikiI of AbstractWiki **= open RGL.Paradigms i, RGL.Syntax i in** {

  -- 3. MAPPING SECTION: Map Abstract Categories to RGL Concrete Categories
  -- =========================================================================
  -- (Generally handled automatically by importing RGL.Syntax)
  -- The categories in AbstractWiki (Entity, Property, Fact) are defined
  -- to map to their RGL counterparts (NP, AP, S).

  lincat 
    Entity = NP ;
    Property = AP ;
    Fact = S ;
    Predicate = VP ;
    Modifier = Adv ;
    Value = Str ; -- Literals are treated as simple strings initially

  -- 4. MAPPING SECTION: Map Abstract Functions to RGL Concrete Functions
  -- =========================================================================

  lin 
    -- Structural Functions (Fact Construction)
    -------------------------------------------
    -- Combines a Subject (NP) and a Predicate (VP) into a Statement (S).
    mkFact entity_np predicate_vp = 
      -- Use the RGL function 'PredVP' (or similar, depending on RGL version)
      -- This handles tense, agreement, and word order for the language 'i'.
      PredVP entity_np predicate_vp ;

    -- Linking an entity and a property via a copula (is/are)
    mkIsAProperty entity_np property_ap = 
      -- Uses RGL's 'PredAP' construction (Copula + Adjective Predicate)
      PredAP entity_np property_ap ;

    -- Conversion of Entity to NP (e.g., 'dog' -> 'the dog' or 'dogs')
    Entity2NP entity = 
      -- Use 'MassNP' to generate a simple, default NP (e.g., singular, indefinite, or mass)
      MassNP entity ;

    -- Conversion of Property to AP (e.g., 'red' -> 'red')
    Property2AP property = 
      -- Simple mapping to the RGL Adjective Phrase type
      property ;
      
    -- Conversion of an RGL Verb Phrase to your internal Predicate type
    VP2Predicate vp = 
      vp ; -- Simple type alignment

    -- Adding an Adverbial Modifier to a Fact
    FactWithMod fact modifier = 
      -- Use RGL function 'AdvS' to attach an adverbial phrase to a sentence
      AdvS fact modifier ;

    -- Handling simple literals (Raw string/number data)
    mkLiteral value_str = 
      -- Use RGL function 'UseN' with 'mkN' to wrap a string into a Noun (as an Entity)
      mkNP (mkN value_str) ;


    -- Lexicon Abstract Functions (Vocabulary Interface)
    -----------------------------------------------------
    -- These map to specific RGL dictionary entries. 
    -- The actual words (e.g., 'pomme', 'hund', 'león') will come from the 
    -- *generated* VocabularyI.gf files, which syncs from your DB/RGL.
    
    -- We assume the lexicon syncer fills in the RGL dictionary entries (e.g., 'apple_N')
    -- Here we map your abstract Entity to the RGL Noun (N) type.
    apple_Entity = apple_N ;
    dog_Entity   = dog_N ;
    city_Entity  = city_N ;

    -- Mapping Properties to RGL Adjectives (A)
    red_Property   = red_A ;
    big_Property   = big_A ;
    famous_Property= famous_A ;
    
    -- Mapping Verb Phrases to RGL Verb (V) or VP types.
    -- Assuming a simple usage form (V used as VP) for common RGL verbs.
    run_VP  = UseV run_V ;
    eat_VP  = UseV eat_V ;
    know_VP = UseV know_V ;

    -- Mapping Modifiers to RGL Adverbs (Adv)
    quickly_Mod = quickly_Adv ;
    slowly_Mod  = slowly_Adv ;
    today_Mod   = today_Adv ;
}
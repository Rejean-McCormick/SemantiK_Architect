-- gf/Vocabulary.gf
-- =========================================================================
-- ABSTRACT VOCABULARY: The Extensible Lexicon
--
-- This file extends the core 'AbstractWiki' grammar. It defines the specific
-- vocabulary items (Functions) that are available to be used in sentences.
--
-- ARCHITECTURE NOTE:
-- This file is intended to be managed by the 'scripts/lexicon/sync_rgl.py'
-- script. It maps the Semantic Categories defined in AbstractWiki (Entity,
-- Property, Predicate) to specific lexical identifiers.
-- =========================================================================

abstract Vocabulary = AbstractWiki ** {

  -- 1. ENTITIES (Nouns)
  -- =======================================================================
  -- Maps to RGL 'N' (Noun) types in the concrete implementation.
  -- These represent physical objects, abstract concepts, or beings.
  
  fun
    -- Common Animals
    animal_Entity  : Entity ;
    cat_Entity     : Entity ;
    horse_Entity   : Entity ;
    bird_Entity    : Entity ;
    fish_Entity    : Entity ;
    
    -- Common Objects/Concepts
    book_Entity    : Entity ;
    house_Entity   : Entity ;
    car_Entity     : Entity ;
    tree_Entity    : Entity ;
    flower_Entity  : Entity ;
    water_Entity   : Entity ;
    sun_Entity     : Entity ;
    moon_Entity    : Entity ;
    
    -- People/Roles
    person_Entity  : Entity ;
    man_Entity     : Entity ;
    woman_Entity   : Entity ;
    child_Entity   : Entity ;
    doctor_Entity  : Entity ;
    teacher_Entity : Entity ;


  -- 2. PROPERTIES (Adjectives)
  -- =======================================================================
  -- Maps to RGL 'A' (Adjective) types.
  -- These represent attributes assigned to Entities.

  fun
    -- Colors
    blue_Property   : Property ;
    green_Property  : Property ;
    yellow_Property : Property ;
    black_Property  : Property ;
    white_Property  : Property ;

    -- Qualities
    good_Property   : Property ;
    bad_Property    : Property ;
    old_Property    : Property ;
    new_Property    : Property ;
    long_Property   : Property ;
    short_Property  : Property ;
    cold_Property   : Property ;
    warm_Property   : Property ;


  -- 3. PREDICATES (Verbs)
  -- =======================================================================
  -- Maps to RGL 'V' (Verb) types, wrapped in VPs.
  -- These represent actions or states.

  fun
    -- Movement/Action
    walk_VP   : Predicate ;  -- To walk
    sleep_VP  : Predicate ;  -- To sleep
    swim_VP   : Predicate ;  -- To swim
    jump_VP   : Predicate ;  -- To jump
    fly_VP    : Predicate ;  -- To fly
    
    -- Transitive Actions (Requiring an object)
    -- Note: In AbstractWiki, we might handle transitivity via specific
    -- functions like 'mkAction : Entity -> Predicate -> Entity -> Fact'.
    -- For now, we define the base VP.
    see_VP    : Predicate ;  -- To see (someone/something)
    love_VP   : Predicate ;  -- To love
    read_VP   : Predicate ;  -- To read
    buy_VP    : Predicate ;  -- To buy

    -- Cognitive/State
    think_VP  : Predicate ;  -- To think
    live_VP   : Predicate ;  -- To live (exist/reside)


  -- 4. MODIFIERS (Adverbs)
  -- =======================================================================
  -- Maps to RGL 'Adv' (Adverb) types.
  
  fun
    here_Mod      : Modifier ;
    there_Mod     : Modifier ;
    always_Mod    : Modifier ;
    never_Mod     : Modifier ;
    tomorrow_Mod  : Modifier ;
    yesterday_Mod : Modifier ;

}
-- gf/VocabularyI.gf
-- =========================================================================
-- VOCABULARY FUNCTOR: The Bridge between Abstract Vocabulary and RGL Dicts
--
-- This file implements the 'Vocabulary' abstract syntax.
-- It extends 'WikiI' (so it knows that Entity = NP, etc.).
--
-- METHOD:
-- It assumes a Dictionary module 'D' is available (injected at build time).
-- It wraps raw dictionary words (N, V, A) into your semantic types (NP, VP, AP).
-- =========================================================================

instance VocabularyI of Vocabulary = WikiI ** open Syntax, Paradigms, (D=Dict) in {

  -- 1. ENTITIES (Nouns -> NPs)
  -- =======================================================================
  -- We use 'mkNP' to turn a raw Noun (N) into a Noun Phrase (NP).
  -- Depending on the language, this might default to Indefinite ("a cat") 
  -- or Mass ("water"). Specific determiners can be added in logic if needed.

  lin
    -- Animals
    animal_Entity  = mkNP D.animal_N ;
    cat_Entity     = mkNP D.cat_N ;
    horse_Entity   = mkNP D.horse_N ;
    bird_Entity    = mkNP D.bird_N ;
    fish_Entity    = mkNP D.fish_N ;
    
    -- Objects
    book_Entity    = mkNP D.book_N ;
    house_Entity   = mkNP D.house_N ;
    car_Entity     = mkNP D.car_N ;
    tree_Entity    = mkNP D.tree_N ;
    flower_Entity  = mkNP D.flower_N ;
    water_Entity   = mkNP D.water_N ; -- Mass noun logic handled by RGL
    sun_Entity     = mkNP D.sun_N ;
    moon_Entity    = mkNP D.moon_N ;
    
    -- People
    person_Entity  = mkNP D.person_N ;
    man_Entity     = mkNP D.man_N ;
    woman_Entity   = mkNP D.woman_N ;
    child_Entity   = mkNP D.child_N ;
    doctor_Entity  = mkNP D.doctor_N ;
    teacher_Entity = mkNP D.teacher_N ;


  -- 2. PROPERTIES (Adjectives -> APs)
  -- =======================================================================
  -- We use 'mkAP' to turn a raw Adjective (A) into an Adjective Phrase (AP).

  lin
    -- Colors
    blue_Property   = mkAP D.blue_A ;
    green_Property  = mkAP D.green_A ;
    yellow_Property = mkAP D.yellow_A ;
    black_Property  = mkAP D.black_A ;
    white_Property  = mkAP D.white_A ;

    -- Qualities
    good_Property   = mkAP D.good_A ;
    bad_Property    = mkAP D.bad_A ;
    old_Property    = mkAP D.old_A ;
    new_Property    = mkAP D.new_A ;
    long_Property   = mkAP D.long_A ;
    short_Property  = mkAP D.short_A ;
    cold_Property   = mkAP D.cold_A ;
    warm_Property   = mkAP D.warm_A ;


  -- 3. PREDICATES (Verbs -> VPs)
  -- =======================================================================
  -- We use 'mkVP' to turn a raw Verb (V) into a Verb Phrase (VP).
  -- This prepares the verb to receive a subject and tense later.

  lin
    -- Movement/Action (Intransitive)
    walk_VP   = mkVP D.walk_V ;
    sleep_VP  = mkVP D.sleep_V ;
    swim_VP   = mkVP D.swim_V ;
    jump_VP   = mkVP D.jump_V ;
    fly_VP    = mkVP D.fly_V ;
    
    -- Transitive Actions
    -- Note: Since 'see_VP' is defined as just a Predicate (VP) in Abstract,
    -- we map it to the generic verb. If we need objects, the Abstract syntax
    -- should use 'mkFact (Subject) (mkVP see_V Object)'.
    -- Here we just expose the verb as a VP.
    see_VP    = mkVP D.see_V ;
    love_VP   = mkVP D.love_V ;
    read_VP   = mkVP D.read_V ;
    buy_VP    = mkVP D.buy_V ;

    -- Cognitive
    think_VP  = mkVP D.think_V ;
    live_VP   = mkVP D.live_V ;


  -- 4. MODIFIERS (Adverbs -> Advs)
  -- =======================================================================
  -- Direct mapping as RGL Adverbs are already the correct category.

  lin
    here_Mod      = D.here_Adv ;
    there_Mod     = D.there_Adv ;
    always_Mod    = D.always_Adv ;
    never_Mod     = D.never_Adv ;
    
    -- Note: Some RGL Dicts might lack time adverbs, but assuming standard coverage:
    tomorrow_Mod  = D.tomorrow_Adv ; 
    yesterday_Mod = D.yesterday_Adv ;

}
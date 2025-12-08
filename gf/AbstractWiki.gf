-- gf/AbstractWiki.gf
-- =========================================================================
-- ABSTRACT SYNTAX: The core, language-independent interface for your
-- Abstract Wiki data (Z-Objects).
--
-- This file defines the Categories (Cat) and Functions (Fun) that represent
-- the conceptual structures your system needs to express.
--
-- Note: This is written to leverage the RGL (Resource Grammar Library)
-- types, enabling the subsequent 'WikiI.gf' functor to generate 300+
-- concrete syntaxes automatically.

abstract AbstractWiki = {

  -- 1. Import RGL Common Categories
  -- =======================================================================
  -- This brings in basic linguistic categories (N, V, A, NP, VP, S)
  -- that AbstractWiki will use as a foundation.
  open Common

  -- 2. Domain-Specific Categories (Your Z-Objects / Semantic Types)
  -- =======================================================================
  -- These categories represent the specific data structures you want to linearize.
  cat
    -- Core Z-Concepts
    Entity;     -- A specific object, idea, or person (maps to RGL.NP or RGL.N)
    Property;   -- An attribute or quality (maps to RGL.A or RGL.AP)
    Fact;       -- A complete statement or proposition (maps to RGL.S)

    -- Contextual Types
    Value;      -- Literal data, e.g., a number, date, or ungrammatical text
    Predicate;  -- The verb or core relation in a sentence (maps to RGL.VP)
    Modifier;   -- Adverbs, PPs, or other sentence modifiers (maps to RGL.Adv)


  -- 3. Core Structural Functions
  -- =======================================================================
  -- These functions build the structure of a sentence (Fact) from its components.
  fun
    -- Construction of a basic Fact: Subject-Predicate-Object
    mkFact : Entity -> Predicate -> Fact;
    -- E.g., mkFact (dog_Entity) (run_Predicate) => "The dog runs."

    -- Conversion of Entity to NP (A complete phrase that can be a subject/object)
    Entity2NP : Entity -> NP;
    -- E.g., Entity2NP dog_Entity => "The dog" or "dogs"

    -- Linking an entity and a property via a copula (is/are)
    mkIsAProperty : Entity -> Property -> Fact;
    -- E.g., mkIsAProperty (apple_Entity) (red_Property) => "The apple is red."

    -- Simple conversion of Property to an Adjective Phrase
    Property2AP : Property -> AP;
    -- E.g., Property2AP red_Property => "red"

    -- Conversion of an RGL Verb Phrase to your internal Predicate type
    VP2Predicate : VP -> Predicate;

    -- Adding an Adverbial Modifier to a Fact
    FactWithMod : Fact -> Modifier -> Fact;
    -- E.g., FactWithMod (The dog runs) (quickly) => "The dog runs quickly."

    -- Handling simple literals
    mkLiteral : Value -> Entity;
    -- E.g., mkLiteral (Value "42") => "42" (used as an Entity/NP)


  -- 4. Lexicon Abstract Functions (Vocabulary Interface)
  -- =======================================================================
  -- These are placeholders for the words you want to manage. These are the
  -- functions that the 'scripts/lexicon/sync_rgl.py' will iterate over.
  -- They are defined here to link your domain to RGL types (N, A, V, etc.)
  
  -- Nouns (Entities)
  apple_Entity : Entity;
  dog_Entity   : Entity;
  city_Entity  : Entity;

  -- Adjectives (Properties)
  red_Property   : Property;
  big_Property   : Property;
  famous_Property: Property;
  
  -- Verbs (Predicates, often converted from VP)
  run_VP  : VP;
  eat_VP  : VP;
  know_VP : VP;

  -- Adverbs (Modifiers)
  quickly_Mod : Modifier;
  slowly_Mod  : Modifier;
  today_Mod   : Modifier;

}
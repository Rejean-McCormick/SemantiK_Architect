# Global System Architecture: Abstract Wiki Architect

This document describes the industrial-scale architecture designed to support Natural Language Generation (NLG) for hundreds of languages using a **Language Family + Data-Driven** approach.

Instead of “one renderer per language”, we use:

* A **Router**
* A small set of **Family Engines**
* **Data-only language cards and lexica**
* A shared **Constructions + Semantics + Discourse** layer
* A full **QA and lexicon coverage pipeline**

---

## 1. High-Level Design

The classical “N+1 problem” for NLG is:

> To add a language, you write a new renderer – and copy/paste most of the logic.

This system replaces that with a **Router–Engine–Data–Semantics** pattern.

### High-Level Flow

1. **Input: Abstract Data + Target Language Code**

   * Abstract semantic frame(s) (e.g. `BioFrame` for biographies).
   * Target language (e.g. `tr` for Turkish, `sw` for Swahili).

2. **Router: Identify Language Family & Profile**

   * Example mappings:

     * `it` → Romance engine
     * `ru` → Slavic engine
     * `sw` → Bantu engine
     * `zh` → Isolating engine
     * `tr` → Agglutinative engine

   * Based on `language_profiles/profiles.json`.

3. **Dispatcher: Load Config + Lexicon + Constructions**

   * Loads the **family morphology matrix** (e.g. `data/morphology_configs/agglutinative_matrix.json`).
   * Loads the **language card** (e.g. `data/agglutinative/tr.json`).
   * Loads the **lexicon** (e.g. `data/lexicon/tr_lexicon.json`).
   * Selects appropriate **constructions** for the semantic frame (e.g. simple equative, relative clause).

4. **Execution: Engine + Constructions**

   * The **family engine** applies language-family logic (e.g. vowel harmony, case, noun-class agreement).
   * The **constructions layer** chooses a clause pattern, fills roles, and calls the engine’s morphology API.

5. **Output: Surface Sentence(s)**

   * Returns one or more **well-formed sentences** in the target language.
   * For biographies, this can be a short multi-sentence lead, not just a single sentence.

---

## 2. Component Breakdown

### A. Master Router (`router.py`)

Entry point for rendering.

Responsibilities:

* Map `lang_code` → **language profile**:

  * family (Romance, Slavic, Bantu, …),
  * engine module (e.g. `engines.romance`),
  * morphology config path,
  * lexicon configuration,
  * word order & other macro-parameters.
* Provide a stable high-level API, e.g.:

  * `render_bio(name, gender, profession_lemma, nationality_lemma, lang_code)`
  * `render_from_semantics(frame, lang_code, discourse_state=None)`

Examples of language → family mapping:

* `it` → `engines.romance`
* `es` → `engines.romance`
* `pt` → `engines.romance`
* `fr` → `engines.romance`
* `ro` → `engines.romance`
* `de` → `engines.germanic`
* `en` → `engines.germanic`
* `nl` → `engines.germanic`
* `ru` → `engines.slavic`
* `pl` → `engines.slavic`
* `tr` → `engines.agglutinative`
* `hu` → `engines.agglutinative`
* `sw` → `engines.bantu`
* `zh` → `engines.isolating`
* `ja` → `engines.japonic`
* `ko` → `engines.koreanic`
* … and so on.

### B. Logic Engines (`engines/*.py`)

We group languages into ~15 structural families. Each **engine** encodes how that family does morphology and basic syntax.

| Engine / Family | Typical Type    | Logic Focus                                                                |
| --------------- | --------------- | -------------------------------------------------------------------------- |
| Romance         | Inflectional    | Gender (M/F), number, article elision, suffix replacement, clitic pronouns |
| Germanic        | Inflectional    | Compounds, adjective declension (strong/weak), mixed 3-gender systems      |
| Slavic          | Synthetic       | Case systems (6–7+ cases), aspect, gendered past, agreement                |
| Agglutinative   | Agglutinative   | Vowel harmony, suffix chains, possessive morphology                        |
| Semitic         | Root–Pattern    | Consonantal roots, patterns, definiteness prefixes, nominal sentences      |
| Bantu           | Noun Class      | Noun classes, concordial agreement, subject/object concord                 |
| Isolating       | Analytic        | Classifiers, particles, strict word order, almost no inflection            |
| Indo-Aryan      | SOV / Split-Erg | Case, postpositions, gender/number agreement, various honorific systems    |
| Dravidian       | Agglutinative   | Rational/irrational “gender”, pronominal suffixes, sandhi                  |
| Austronesian    | Voice System    | Focus/voice markers, personal articles, reduplication                      |
| Japonic         | Topic–Comment   | Particles (wa/ga), honorifics, no grammatical gender                       |
| Koreanic        | Agglutinative   | Verb endings for speech level, particle-based case                         |
| Polysynthetic   | Holophrastic    | Word-sentences, noun incorporation, ergativity                             |
| …               | …               | Additional families / hybrid patterns as needed                            |

Each engine exposes a **Morphology + Syntax API** that the constructions layer uses:

* `realize_lexeme(lemma, pos, features)`
* `realize_noun(lemma, features)`
* `realize_adjective(lemma, features)`
* `realize_verb(lemma, features)`
* `join_tokens(tokens)` (handles spacing, clitics, zero morphemes, etc.)

The engines do **not** hard-code specific lexemes; they read their behavior from **family matrices** + **language cards** + **lexicon**.

### C. The Data Layer (Language Cards & Matrices)

All language-specific rules live in JSON, not in Python.

#### Family Matrices (`data/morphology_configs/*.json`)

Each family has a matrix that defines:

* core inflection paradigms,
* agreement rules (subject–verb, noun–adjective, noun–determiner, noun-class concord),
* phonology triggers (vowel harmony groups, elision, s-impure, sandhi),
* default clause templates for simple constructions.

Examples:

* `data/morphology_configs/romance_grammar_matrix.json`
* `data/morphology_configs/slavic_matrix.json`
* `data/morphology_configs/agglutinative_matrix.json`
* `data/morphology_configs/bantu_matrix.json`
* etc.

#### Language Cards (`data/<family>/<lang>.json`)

A language card specializes the family matrix.

Agglutinative example (Turkish-like):

```json
{
  "phonetics": {
    "harmony_groups": {
      "back": ["a", "ı", "o", "u"],
      "front": ["e", "i", "ö", "ü"]
    }
  },
  "morphology": {
    "suffixes": {
      "plural": { "back": "lar", "front": "ler" },
      "possessive_3sg": { "back": "ı", "front": "i" }
    }
  },
  "syntax": {
    "canonical_order": ["topic", "subject", "object", "verb"]
  }
}
```

The engine merges:

> **Family matrix ⊕ Language card ⊕ Language profile**

into a single configuration object.

### D. Constructions Layer (`constructions/*.py`)

The constructions layer is **language-agnostic** code that knows about **sentence patterns**, not letters or suffixes.

Examples of constructions:

* `copula_equative_simple.py` – “X is a Y”
* `copula_locative.py` – “X is in Y”
* `copula_existential.py` – “There is a Y (in X)”
* `possession_have.py` – “X has Y”
* `transitive_event.py`, `intransitive_event.py`
* `relative_clause_subject_gap.py`, `relative_clause_object_gap.py`
* `topic_comment_copular.py`, `topic_comment_eventive.py`
* `comparative_superlative.py`
* `apposition_np.py`

Each construction:

1. Receives a **language-independent clause spec** (`ClauseInput`).
2. Calls the engine’s Morphology API for all words.
3. Respects the language profile’s word order and function words.
4. Produces a `ClauseOutput` with tokens and final string.

This means the same construction code is reused for Romance, Slavic, Bantu, etc.; only the engine + data differ.

### E. Lexicon Subsystem (`lexicon/*`, `data/lexicon/*.json`)

The lexicon is a separate subsystem, not hidden inside engines.

Components:

* `data/lexicon/<lang>_lexicon.json`

  * Lemmas, POS, gender, class, QID/lexeme links.
* `lexicon/types.py`, `lexicon/loader.py`, `lexicon/index.py`

  * Load lexica, validate schema, build indices (lemma → Lexeme, QID → Lexeme).
* `lexicon/wikidata_bridge.py`, `lexicon/aw_lexeme_bridge.py`

  * Bridges from Wikidata lexeme dumps or Abstract Wikipedia lexeme objects to internal lexicon format.
* `utils/build_lexicon_from_wikidata.py`, `utils/dump_lexicon_stats.py`

  * Utilities to build/update lexica and inspect coverage.

This allows:

* broad coverage via Wikidata,
* language-neutral semantics that point to lexemes, not raw strings,
* QA for lexical coverage across test suites.

### F. Semantics & Discourse (`semantics/*`, `discourse/*`)

To move beyond single sentences, we have a thin semantic and discourse layer.

* `semantics/types.py`

  * Defines frame types like `BioFrame` (person, profession, nationality, birth, death, achievements).
* `semantics/normalization.py`, `semantics/aw_bridge.py`

  * Convert AW-style structures into internal frames.
* `discourse/state.py`

  * Tracks mentioned entities, salience, and current topic.
* `discourse/info_structure.py`

  * Assigns topic vs focus labels.
* `discourse/referring_expression.py`

  * Chooses full NP / short NP / pronoun / zero subject.
* `discourse/planner.py`

  * Given several frames (birth, profession, award, etc.), decide the sentence order and structure.

This layer lets the system handle:

* multi-sentence leads,
* anaphora,
* topic–comment patterns in languages like Japanese,
* more natural discourse structure.

---

## 3. Data Flow & Interfaces

### Standard Input: Abstract Semantics + Language Code

The system expects **abstract** input, not raw strings.

For biographies:

* `BioFrame` containing:

  * main entity (name, gender, QID),
  * profession lemmas,
  * nationality lemmas,
  * birth/death events (with years, locations),
  * extra attributes.

Minimal “flat” entry via the simple API:

* Name: “Marie Curie”
* Gender: `female`
* Profession lemma: `physicist`
* Nationality lemma: `polish`
* Language: `it`

Or via richer semantic frames for more complex texts.

### Standard Output: Surface Text

The engines + constructions return a surface string (or list of sentences).

#### Example: Italian Biography Sentence

Input abstractly:

* `main_entity`: “Marie Curie”, female
* `profession_lemma`: `fisico` (physicist)
* `nationality_lemma`: `polish`
* `lang_code`: `it`

Processing sketch:

1. **Semantics → Frame**

   * Build a `BioFrame`:

     * main person: Marie Curie (female, QID=Q7186),
     * profession: `physicist`,
     * nationality: `polish`.

2. **Router → Romance Engine**

   * Language `it` → Romance engine
   * Load `romance_grammar_matrix.json` + `data/romance/it.json`
   * Load `data/lexicon/it_lexicon.json` entry for “fisico”.

3. **Constructions**

   * Select `copula_equative_simple` for first sentence.
   * Fill roles: subject = “Marie Curie”, predicate = “Polish physicist”.

4. **Morphology**

   * Profession lemma: `fisico` (masculine lemma).
   * Gender = female → morphological rules:

     * `fisico` → `fisica`.
   * Nationality lemma: `polacco` → feminine form `polacca`.
   * Article rules:

     * feminine singular, initial consonant → `una`.

5. **Surface Assembly**

   * Order tokens: `[Marie Curie] [è] [una] [fisica] [polacca].`
   * Join tokens into `"Marie Curie è una fisica polacca."`

Output:

> `"Marie Curie è una fisica polacca."`

The same input frame can be routed to Slavic, Bantu, Japonic, etc., with completely different morphosyntax but reusing the same constructions and semantics code.

---

## 4. Scalability Strategy

To reach (or approach) 300 languages:

1. **Do not write 300 renderers.**

   * Implement ~15 **family engines** that capture major typological patterns.
   * Each engine is parameterized by family matrices + language cards.

2. **Crowdsource / community-maintain the data.**

   * Language-specific behavior is in JSON (cards + lexicon).
   * Contributors who speak Catalan, Swahili, etc., do **not** need to know Python to improve coverage.
   * Example:

     * A Catalan contributor copies `data/romance/es.json` to `data/romance/ca.json`,
     * Updates suffixes and article rules (`-dad` → `-tat`, `y` → `i`),
     * The Romance engine immediately supports Catalan.

3. **Integrate with Wikidata / lexemes for breadth.**

   * Use `lexicon/wikidata_bridge.py` and associated utils to populate large lexica.
   * Align lexemes with QIDs so Abstract Wikipedia’s semantic structures can refer to them directly.

4. **Back it with QA.**

   * CSV test suites per language (`qa/generated_datasets/test_suite_<lang>.csv`).
   * Automated runners (`qa/test_runner.py`, `qa_tools/universal_test_runner.py`) to keep regressions in check.
   * Lexicon coverage reports to detect missing vocabulary.

The combination of **family engines + data cards + lexicon + QA** allows incremental scaling to many languages without losing control over quality.

---

## 5. Development Roadmap (Conceptual)

* **Phase 1: Core families & biographies (Beta)**

  * Romance, Germanic, Agglutinative fully wired.
  * Multi-language biography first-sentences with discourse-aware pronouns.
  * Robust per-language test suites, lexicon coverage reports.

* **Phase 2: Complex morphologies (Alpha)**

  * Slavic (case-rich, aspect), Semitic (root–pattern, nominal sentences), Bantu (noun classes, concord).
  * Extend family matrices and language cards.
  * Expand constructions to cover more frame types (relative clauses, possessives, locative/existential, etc.).

* **Phase 3: Long tail & tooling**

  * Add “catch-all” / hybrid engines for isolate or fringe typologies.
  * Build UI tools for non-coders:

    * guided editors for language cards,
    * simple lexicon editors,
    * test suite creators.
  * Tight integration with Abstract Wikipedia / Wikifunctions:

    * Functions that take Z-objects and language codes,
    * Cards / lexica maintained as Z-data.

This architecture is designed to be **incrementally extensible**: every new language, test suite, and lexicon improvement benefits from the same shared logic and QA infrastructure.

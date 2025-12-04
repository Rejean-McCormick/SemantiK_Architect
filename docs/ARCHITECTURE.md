# Abstract Wiki Architect: System Architecture

This repository implements a **data-driven, family-based architecture** for Abstract Wikipedia renderers. Instead of writing bespoke code for every language, we factor out shared logic at three levels:

* **Language-family engines** (Python),
* **Morphology “matrices” and language cards** (JSON),
* **Language-agnostic constructions + semantics/discourse + lexicon**.

The result is an industrial-scale stack that can cover hundreds of languages with ~15 engines and many configuration files instead of 300+ separate renderers. 

---

## 1. End-to-end flow: from abstract frame to surface sentence

At a high level, rendering proceeds as:

1. **Abstract semantics in, per-sentence:**

   * The system receives one or more **semantic frames** (e.g. `BioFrame` for biographies) plus optional **discourse state** describing which entities are already given / topical.
   * Core modules: `semantics/` (frame types, AW/Ninai bridge, normalization), `discourse/state.py`. 

2. **Discourse & information structure:**

   * `discourse/info_structure.py` assigns topic/focus labels to arguments.
   * `discourse/referring_expression.py` decides whether to realize an entity as:

     * full NP (“Marie Curie”),
     * reduced NP (“Curie”),
     * pronoun / zero subject (for pro-drop languages).
   * `discourse/planner.py` can sequence multiple frames into a coherent multi-sentence plan (e.g. birth → occupation → awards). 

3. **Routing to the right engine:**

   * `router.py` plus `language_profiles/profiles.json` map an ISO language code to:

     * a **family engine** in `engines/*.py`,
     * the relevant **morphology config** in `data/morphology_configs/*.json`,
     * the **lexicon** files in `data/lexicon/*.json`,
     * language-level flags (word order, copula defaults, article usage, etc.). 

   Example mappings:

   * `it` → Romance engine + romance matrix + `data/romance/it.json` + `data/lexicon/it_lexicon.json`
   * `ru` → Slavic engine + slavic matrix + `data/slavic/ru.json` + `data/lexicon/ru_lexicon.json`

4. **Family engine orchestration:**

   Each family has its own engine module, e.g.:

   * `engines/romance.py` (gender, articles, suffix alternations),
   * `engines/slavic.py` (cases, gendered past, agreement),
   * `engines/agglutinative.py` (vowel harmony, suffix chains),
   * `engines/semitic.py` (root–pattern, definiteness),
   * … and so on for Bantu, Austronesian, Japonic, etc. 

   The engine:

   * Reads the **family matrix** (see §2),
   * Loads the per-language card (phonotactics, templates, irregulars),
   * Wraps all of that behind a uniform **Morphology API** that the constructions layer can call:

     * `realize_lexeme(lemma, pos, features)`,
     * `join_tokens(tokens)`,
     * plus optional helpers (`realize_np`, `realize_verb`, `realize_causative`, …).

5. **Constructions layer (clause templates):**

   * `constructions/*.py` implement **language-agnostic sentence patterns**, e.g.:

     * `copula_equative_simple.py` (“X is a Y”),
     * `copula_locative.py` (“X is in Y”),
     * `transitive_event.py`, `intransitive_event.py`,
     * `relative_clause_subject_gap.py`, `relative_clause_object_gap.py`,
     * `topic_comment_copular.py`, `topic_comment_eventive.py`,
     * `apposition_np.py`, `comparative_superlative.py`, etc. 

   Each construction:

   * Takes a **language-independent `ClauseInput`** (roles + features) from `constructions/base.py`,
   * Consults `lang_profile` for word order and little words (particles, complementizers),
   * Delegates all inflection to the Morphology API,
   * Returns a `ClauseOutput` with tokens + final text string.

   Engines select which construction to use for a given frame type and pass in the right roles and features.

6. **Lexicon lookup:**

   * `lexicon/index.py`, `lexicon/loader.py`, `lexicon/types.py` and `data/lexicon/*.json` form the **lexicon subsystem**:

     * lemma → POS → features (gender, animacy, class),
     * mappings to Wikidata IDs (`qid`, `lexeme_id`),
     * domain-specific sub-lexica (e.g. science, people) when needed. 

   * `lexicon/wikidata_bridge.py` and utilities in `utils/` support building and refreshing these lexica from Wikidata / lexeme dumps, and `qa_tools/lexicon_coverage_report.py` measures coverage against test suites. 

7. **Surface assembly and post-processing:**

   * Engines or constructions call `morph.join_tokens` to handle spacing, clitics, and script-specific rules.
   * Final sentences are returned either singly (for one frame) or as a list for multi-sentence discourse.

---

## 2. Grammar Matrices and Language Cards

Morphology and low-level syntax are defined in **data, not code**.

### 2.1 Family-level matrices

Under `data/morphology_configs/` you find:

* `romance_grammar_matrix.json`
* `germanic_matrix.json`
* `slavic_matrix.json`
* `agglutinative_matrix.json`
* … (one JSON “matrix” per language family). 

Each matrix encodes:

* **Nominal morphology:** gender systems, plural formation, case endings, noun-class prefixes.
* **Verbal morphology:** tense/aspect/person endings, copula paradigms, participles.
* **Agreement:** which features must agree (subject–verb, noun–adjective, noun–determiner).
* **Phonology hooks:** vowel harmony groups, elision rules, sandhi, “fleeting vowels”, etc.
* **Default clause templates:** simple patterns like
  `{name} {verb} {nationality} {profession}.`

These matrices are shared by all languages in the family.

### 2.2 Per-language cards

For each concrete language there is a **language card** in `data/<family>/<lang>.json`, e.g.:

* `data/romance/it.json`
* `data/romance/es.json`
* `data/slavic/ru.json`
* `data/agglutinative/tr.json`
* etc. 

Language cards specify:

* Actual lexeme forms for articles, common function words, and irregular patterns,
* Overrides or additions to the family matrix (e.g. special feminine formations),
* Language-specific structure strings or template variants when needed.

Engines merge:

> family matrix ⊕ language card ⊕ language profile

into a single configuration object and then expose it via the Morphology API.

---

## 3. Semantics and discourse components

While engines and constructions focus on **morphosyntax**, the project also includes a thin semantic/discourse layer, primarily for multi-sentence outputs like biographies:

* `semantics/types.py` defines frame types (e.g. “person”, “birth”, “occupation”) and roles.
* `semantics/aw_bridge.py` and `semantics/normalization.py` map Abstract Wikipedia / Wikifunctions inputs into those internal frames.
* `discourse/state.py` tracks which entities are “given”, their last mention, and salience scores.
* `discourse/referring_expression.py` chooses pronouns vs names vs NPs based on this state.
* `discourse/info_structure.py` attaches topic/focus labels that constructions can consult.
* `discourse/planner.py` can order frames into a coherent, minimal biography or description. 

This makes it possible to go beyond isolated sentences and approach **document-level NLG** in a controlled way.

---

## 4. Lexicon architecture (high-level)

The lexicon layer is intentionally separate from morphology and engines:

* JSON lexica live in `data/lexicon/*.json`.
* Code lives in `lexicon/*.py` and is responsible for:

  * loading and validating lexica (`lexicon/loader.py`, `lexicon/schema.py`),
  * building fast indices (`lexicon/index.py`, `lexicon/cache.py`),
  * mapping from abstract frames to concrete lemmas (`lexicon/config.py`, `lexicon/types.py`),
  * connecting to Wikidata / Lexemes (`lexicon/wikidata_bridge.py`, `lexicon/aw_lexeme_bridge.py`). 

Supporting docs:

* `docs/LEXICON_ARCHITECTURE.md`
* `docs/LEXICON_SCHEMA.md`
* `docs/LEXICON_WORKFLOW.md` 

These documents describe the JSON schema, the build pipeline from Wikidata, and the QA checks around coverage.

---

## 5. QA and test infrastructure

Two layers of testing are provided:

1. **Engine- and construction-level tests**

   * `qa/test_runner.py` runs the core biography renderer over CSV suites and reports pass/fail rates.
   * `qa_tools/test_suite_generator.py` and `qa_tools/universal_test_runner.py` support large, LLM-assisted test generation and regression suites.
   * `data/ambiguity_corpus.json` and `qa_tools/prompts/*` are used to stress-test reference resolution, ambiguity, and tricky morphology. 

2. **Lexicon-specific tests**

   * `qa/test_lexicon_loader.py`, `qa/test_lexicon_index.py`, `qa/test_lexicon_wikidata_bridge.py` ensure that lexica load, index, and align with Wikidata as expected.
   * `qa_tools/lexicon_smoke_tests.py`, `qa_tools/lexicon_coverage_report.py`, and `qa_tools/generate_lexicon_regression_tests.py` provide coverage and regression checks for vocab. 

---

## 6. Adding a new language (overview)

A separate document `docs/ADDING_A_LANGUAGE.md` gives a detailed cookbook. At a high level, integrating a new language requires:

1. **Lexicon:**

   * Create `data/lexicon/<lang>_lexicon.json` following `data/lexicon_schema.json`.
   * Optionally use `utils/build_lexicon_from_wikidata.py` and `utils/refresh_lexicon_index.py`. 

2. **Morphology config:**

   * Add or extend the relevant **family matrix** in `data/morphology_configs/`.
   * Create a per-language card in `data/<family>/<lang>.json`.

3. **Language profile and routing:**

   * Add an entry for `<lang>` in `language_profiles/profiles.json` (family, engine, paths, word order, flags).
   * Ensure `router.py` can call the correct engine for `<lang>`.

4. **Tests and docs:**

   * Generate and fill `qa/generated_datasets/test_suite_<lang>.csv`.
   * Run `python qa/test_runner.py` and the lexicon QA tools.
   * Document any language-specific choices under `docs/` (lexicon + morphology notes). 

With these pieces in place, the new language plugs into the same Router–Engine–Constructions–Lexicon–QA pipeline as the existing ones, benefiting from shared abstractions while allowing clean language-specific extensions.

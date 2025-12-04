# Abstract Wiki Architect

An industrial-scale toolkit for **Abstract Wikipedia** and **Wikifunctions**.

Instead of writing one renderer per language (300 scripts for 300 languages), this project builds:

- ~15 shared **Logic Engines** (per language family, in Python),
- hundreds of **Configuration Cards** (per language, in JSON),
- a small library of **cross-linguistic constructions** (sentence patterns),
- a **lexicon subsystem** (with Wikidata bridges),
- and a **QA factory** for large test suites.

The goal is to offer a **professional, testable architecture** for rule-based NLG across many languages.

---

## Intuition: Consoles, Cartridges, and the Router

Think of each sentence as a game you want to play.

- Old way:
  - Build **one console per game** (one monolithic renderer per language).
- This project:
  - Build **~15 universal consoles** (family engines: Romance, Slavic, Agglutinative, Bantu, etc.).
  - Load **hundreds of cartridges** (per-language JSON Cards + lexica).
  - Use a **Router** to plug the right card into the right console.

Example (Romance family):

- The **Romance Engine** knows how to:
  - Feminize nouns/adjectives.
  - Apply plural rules.
  - Pick articles.
- The **Italian Card** (`data/morphology_configs/romance_grammar_matrix.json` + `data/romance/it.json`) tells it:
  - “`-o` → `-a` for feminine”.
  - “Use `uno` before /z/ or /sC/”.
- The **Spanish Card** tweaks only what differs:
  - Feminization also `-o` → `-a`,
  - but indefinite article is always `un`.

The **Router** sees `lang_code="it"`, picks `RomanceEngine`, loads the Italian Card and lexicon, and calls the right constructions to build the sentence.

---

## Core Concepts

### 1. Engines (Family-Level Logic)

One engine per **language family**, e.g.:

- `engines/romance.py`
- `engines/slavic.py`
- `engines/agglutinative.py`
- `engines/germanic.py`
- `engines/bantu.py`
- `engines/semitic.py`
- `engines/indo_aryan.py`
- `engines/iranic.py`
- `engines/austronesian.py`
- `engines/japonic.py`
- `engines/koreanic.py`
- `engines/polysynthetic.py`
- `engines/celtic.py`
- `engines/dravidian.py`
- …

Each engine knows *how* its family works:

- Gender & number paradigms.
- Case systems.
- Vowel harmony / suffix chaining.
- Noun class agreement, etc.

It does **not** hard-code per-language endings; it reads them from JSON configs and lexica.

### 2. Morphology Helpers

Under `morphology/`:

- `morphology/romance.py`
- `morphology/slavic.py`
- `morphology/agglutinative.py`
- `morphology/germanic.py`
- `morphology/bantu.py`
- `morphology/semitic.py`
- `morphology/isolating.py`
- `morphology/austronesian.py`
- `morphology/japonic.py`
- `morphology/koreanic.py`
- `morphology/polysynthetic.py`
- `morphology/celtic.py`
- `morphology/dravidian.py`
- …

These modules implement **family-specific morphology**, using:

- Grammars in `data/morphology_configs/` (e.g. `romance_grammar_matrix.json`, `slavic_matrix.json`, `agglutinative_matrix.json`),
- Per-language configs (e.g. `data/romance/it.json`, `data/slavic/ru.json`),
- Lemma features from the lexicon,
- Shared utilities in `morphology/base.py`.

### 3. Constructions (Sentence Patterns)

Under `constructions/` you get **cross-linguistic sentence patterns**, e.g.:

- `copula_equative_simple.py` — “X is a Y”
- `copula_equative_classification.py` — “X is a Polish physicist”
- `copula_attributive_np.py` / `copula_attributive_adj.py`
- `copula_existential.py` — “There is a Y in X”
- `copula_locative.py`
- `possession_have.py` — “X has Y”
- `intransitive_event.py`, `transitive_event.py`, `ditransitive_event.py`
- `passive_event.py`
- `relative_clause_subject_gap.py` — “the scientist who discovered Y”
- `coordination_clauses.py`
- `comparative_superlative.py`
- `causative_event.py`
- `topic_comment_copular.py`
- `apposition_np.py`
- …

Constructions are **family-agnostic**:

- They choose roles (SUBJ, PRED, LOC, OBJ, etc.).
- They call morphology + lexicon to realize NPs and verbs.
- They can consult discourse state (topic vs focus) when available.

### 4. Semantics Layer

Under `semantics/`:

- `semantics/types.py`
  - `Entity`, `Location`, `TimeSpan`, `Event`, `BioFrame`.
- `semantics/normalization.py`
  - Helpers to convert “loose” dicts (CSV rows, Z-objects) into semantic objects.
- `semantics/roles.py`
  - String constants / helpers for semantic roles (`ROLE_AGENT`, `ROLE_PATIENT`, etc.).
- `semantics/aw_bridge.py`
  - Mapping between Abstract Wikipedia-style data structures and internal semantic frames.

Example:

```python
from semantics.types import Entity, BioFrame

marie = Entity(
    id="Q7186",
    name="Marie Curie",
    gender="female",
    human=True,
)

frame = BioFrame(
    main_entity=marie,
    primary_profession_lemmas=["physicist"],
    nationality_lemmas=["polish"],
)
````

The router takes this **semantic frame** plus `lang_code="fr"` and chooses the right constructions and engine.

### 5. Discourse & Information Structure

Under `discourse/`:

* `discourse/state.py` — `DiscourseState` tracks:

  * which entities have been mentioned,
  * current topic,
  * simple salience scores.
* `discourse/info_structure.py`

  * decides topic vs focus labels on frames / arguments.
* `discourse/referring_expression.py`

  * decides whether to use full name vs short name vs pronoun vs zero subject.
* `discourse/planner.py`

  * orders frames (birth, death, achievements, etc.) into a short multi-sentence description.

This allows you to move from:

> “Marie Curie is a Polish physicist. Marie Curie discovered radium.”

to:

> “Marie Curie is a Polish physicist. **She** discovered radium.”

and, for topic-marking languages, to topic–comment variants.

### 6. Lexicon Subsystem (with Wikidata Bridges)

Under `lexicon/`:

* `lexicon/types.py` — `Lexeme`, `Form`, etc.
* `lexicon/loader.py` — read `data/lexicon/*.json`.
* `lexicon/index.py` — lemma/QID lookup, normalised `Lexeme` objects.
* `lexicon/normalization.py` — string/lemma normalization helpers.
* `lexicon/cache.py` — in-memory cache.
* `lexicon/config.py` — environment-based config.
* `lexicon/errors.py` — custom exceptions.
* `lexicon/schema.py` — schema helpers for lexicon JSON.
* `lexicon/wikidata_bridge.py` — convert Wikidata Lexeme records into `Lexeme`s.
* `lexicon/aw_lexeme_bridge.py` — bridge from Abstract Wikipedia lexeme-like Z-objects to `Lexeme`.

Data lives under `data/lexicon/`:

* `en_lexicon.json`, `fr_lexicon.json`, `it_lexicon.json`, `es_lexicon.json`, `pt_lexicon.json`, `ro_lexicon.json`, `ru_lexicon.json`, `tr_lexicon.json`, `sw_lexicon.json`, `ja_lexicon.json`, etc.
* Optional shards (e.g. `en_core.json`, `en_science.json`, `en_people.json`).
* `data/lexicon_schema.json` defines the JSON schema.

Each entry stores at least:

* `lemma`, `pos` (`NOUN`, `ADJ`, `VERB`, …),
* features like `gender`, `number`, `noun_class`,
* flags like `human`, `nationality`,
* mappings to related lemmas (`feminine_lemma`, `plural_lemma`, …),
* optional IDs (`wikidata_qid`, `wikidata_lexeme_id`),
* language-specific data used by morphology.

Helper scripts:

* `utils/build_lexicon_from_wikidata.py`

  * build/update `data/lexicon/<lang>_lexicon.json` from Wikidata dumps.
* `utils/dump_lexicon_stats.py`

  * print per-language counts by POS, flags, etc.
* `qa_tools/lexicon_coverage_report.py`

  * report which test-suite lemmas are missing from each lexicon.

### 7. Router

`router.py` is the main entrypoint used by tests and demos.

Two typical call shapes:

**a) High-level helper for bios**

```python
from router import render_bio

print(
    render_bio(
        name="Marie Curie",
        gender="female",
        profession_lemma="physicist",
        nationality_lemma="polish",
        lang_code="fr",
    )
)
# → "Marie Curie est une physicienne polonaise."
```

**b) Semantics-first entrypoint**

```python
from semantics.types import BioFrame, Entity
from router import render_from_semantics

frame = BioFrame(
    main_entity=Entity(name="Marie Curie", gender="female", human=True),
    primary_profession_lemmas=["physicist"],
    nationality_lemmas=["polish"],
)

print(render_from_semantics(frame, lang_code="it"))
# → "Marie Curie è una fisica polacca."
```

Internally the router:

1. Builds a `BioFrame` or other semantic frame (via `semantics.normalization` or manually).
2. Looks up the language profile (`language_profiles/profiles.json`).
3. Picks:

   * the correct family engine,
   * default constructions,
   * the right morphology + lexicon config.
4. Returns a surface string.

---

## Quick Start

### 1. Setup environment

From the project root:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

This installs (via `pyproject.toml`):

* `pytest`, `pandas` (for QA),
* `black`, `flake8`, `mypy` (for code quality).

### 2. Generate Test Suites

Use the **Test Factory** to create CSV templates:

```bash
python qa_tools/test_suite_generator.py
```

Outputs (example):

* `qa_tools/generated_datasets/test_suite_it.csv`
* `qa_tools/generated_datasets/test_suite_fr.csv`
* `qa_tools/generated_datasets/test_suite_tr.csv`
* …

Fill the `EXPECTED_OUTPUT` (or `EXPECTED_FULL_SENTENCE`) column with gold sentences (LLM or native speakers).

### 3. Run the Test Runner

From project root:

```bash
python qa/test_runner.py
```

This will:

* Scan `qa_tools/generated_datasets/` (or `qa/generated_datasets/`) for `test_suite_*.csv`.
* For each row with an expected sentence:

  * build a semantic frame,
  * call `router.render_bio(...)`,
  * compare ACTUAL vs EXPECTED.
* Print per-language and global pass/fail statistics and a small mismatch report.

### 4. Inspect Lexicon Coverage (optional)

```bash
python utils/dump_lexicon_stats.py
```

You’ll get, per language:

* total lemmas,
* counts by POS,
* counts by key flags (`human`, `nationality`, etc.).

For test-suite alignment:

```bash
python qa_tools/lexicon_coverage_report.py
```

This reports which lemmas in the CSVs are missing from each lexicon.

---

## Mapping to Wikifunctions

### Z-Object Compatibility

The repo includes a tiny **Z-Object mock**:

* `utils/wikifunctions_api_mock.py`

It provides:

* `Z6(text)` → wraps a string as a Z6 object,
* `Z9(zid)` → wraps a reference as Z9,
* `unwrap` / `unwrap_recursive` → convert nested Z-objects to plain Python.

You can simulate a Wikifunctions call:

```python
from utils.wikifunctions_api_mock import Z6, unwrap_recursive
from router import render_bio

z_args = {
    "name": Z6("Marie Curie"),
    "gender": Z6("female"),
    "profession_lemma": Z6("physicist"),
    "nationality_lemma": Z6("polish"),
    "lang_code": Z6("it"),
}

args = unwrap_recursive(z_args)
print(render_bio(**args))
# → "Marie Curie è una fisica polacca."
```

### JSON Cards for Wikifunctions

For language-specific JSON Cards on Wikifunctions:

* Use `utils/config_extractor.py`:

```bash
# Extract Italian Romance configuration payload for Wikifunctions
python utils/config_extractor.py it
```

Copy the printed JSON into the Wikifunctions function call argument.

You can keep the **Logic Engines** as Z-implementations and feed them the card as a single JSON argument.

---

## Adding a New Language (High-Level Recipe)

1. **Decide the family**

   * Choose or create a family engine (`engines/<family>.py`).
   * Ensure there is a matching morphology module in `morphology/`.

2. **Add Lexicon Entries**

   * Create or edit `data/lexicon/<lang>_lexicon.json`.
   * Include:

     * common professions (`physicist`, `writer`, …),
     * nationality adjectives,
     * key country/city names,
     * basic biography verbs.

3. **Add or Extend Morphology Config**

   * For Romance:

     * add the language entry to `data/morphology_configs/romance_grammar_matrix.json`,
     * and, if needed, a per-language file under `data/romance/`.
   * For other families:

     * add a similar JSON config under `data/morphology_configs/` (and `data/<family>/` if used).

4. **Create a Language Profile**

   * Add an entry in `language_profiles/profiles.json`:

     * `family`,
     * `default_constructions`,
     * flags (e.g. “postposed definite articles”, “topic_marker_language”).

5. **Generate & Fill Test Suite**

   * Run `qa_tools/test_suite_generator.py`.
   * Fill `EXPECTED_OUTPUT` for `test_suite_<lang>.csv`.

6. **Run the Tests**

   * `python qa/test_runner.py`
   * Iterate on configs/lexicon until the language passes most tests.

---

## Project Structure (Overview)

```text
abstract-wiki-architect/
│
├── router.py                        # Master: lang + semantics → surface
│
├── language_profiles/
│   ├── __init__.py
│   └── profiles.json                # Per-language family & defaults
│
├── constructions/                   # Cross-ling sentence patterns
│   ├── __init__.py
│   ├── copula_equative_simple.py
│   ├── copula_equative_classification.py
│   ├── copula_attributive_np.py
│   ├── copula_attributive_adj.py
│   ├── copula_locative.py
│   ├── copula_existential.py
│   ├── possession_have.py
│   ├── intransitive_event.py
│   ├── transitive_event.py
│   ├── passive_event.py
│   ├── ditransitive_event.py
│   ├── relative_clause_subject_gap.py
│   ├── coordination_clauses.py
│   ├── comparative_superlative.py
│   ├── causative_event.py
│   ├── topic_comment_copular.py
│   ├── apposition_np.py
│   └── base.py
│
├── morphology/                      # Family-level morphology
│   ├── __init__.py
│   ├── base.py
│   ├── romance.py
│   ├── slavic.py
│   ├── agglutinative.py
│   ├── germanic.py
│   ├── bantu.py
│   ├── semitic.py
│   ├── isolating.py
│   ├── austronesian.py
│   ├── japonic.py
│   ├── koreanic.py
│   ├── polysynthetic.py
│   ├── celtic.py
│   └── dravidian.py
│
├── engines/                         # Family engines (orchestrate morph + constructions)
│   ├── __init__.py
│   ├── romance.py
│   ├── slavic.py
│   ├── agglutinative.py
│   ├── germanic.py
│   ├── bantu.py
│   ├── semitic.py
│   ├── indo_aryan.py
│   ├── iranic.py
│   ├── austronesian.py
│   ├── japonic.py
│   ├── koreanic.py
│   ├── polysynthetic.py
│   └── celtic.py
│
├── semantics/                       # Meaning-level types
│   ├── __init__.py
│   ├── types.py
│   ├── normalization.py
│   ├── roles.py
│   └── aw_bridge.py
│
├── discourse/                       # Discourse state / info structure
│   ├── __init__.py
│   ├── state.py
│   ├── info_structure.py
│   ├── referring_expression.py
│   └── planner.py
│
├── lexicon/                         # Lexicon subsystem
│   ├── __init__.py
│   ├── types.py
│   ├── loader.py
│   ├── index.py
│   ├── normalization.py
│   ├── cache.py
│   ├── config.py
│   ├── errors.py
│   ├── schema.py
│   ├── wikidata_bridge.py
│   └── aw_lexeme_bridge.py
│
├── data/
│   ├── morphology_configs/
│   │   ├── __init__.py
│   │   ├── romance_grammar_matrix.json
│   │   ├── slavic_matrix.json
│   │   ├── agglutinative_matrix.json
│   │   └── germanic_matrix.json
│   ├── romance/
│   │   ├── it.json
│   │   └── es.json
│   ├── slavic/
│   │   └── ru.json
│   ├── semitic/
│   │   └── ar.json
│   ├── bant
│   ├── lexicon/
│   │   ├── __init__.py
│   │   ├── en_lexicon.json
│   │   ├── fr_lexicon.json
│   │   ├── it_lexicon.json
│   │   ├── es_lexicon.json
│   │   ├── pt_lexicon.json
│   │   ├── ro_lexicon.json
│   │   ├── ru_lexicon.json
│   │   ├── tr_lexicon.json
│   │   ├── sw_lexicon.json
│   │   └── ja_lexicon.json
│   ├── lexicon_schema.json
│   └── raw_wikidata/
│       ├── .gitignore
│       └── lexemes_dump.json.gz    # not committed; example location
│
├── qa_tools/                        # Test suite generator & helpers
│   ├── test_suite_generator.py
│   ├── lexicon_coverage_report.py
│   ├── generate_lexicon_regression_tests.py
│   └── generated_datasets/
│       ├── .keep
│       └── .gitignore
│
├── qa/                              # Test harness & unit tests
│   ├── __init__.py
│   ├── test_runner.py
│   ├── test_lexicon_loader.py
│   ├── test_lexicon_index.py
│   ├── test_lexicon_wikidata_bridge.py
│   └── generated_datasets/
│       └── .gitignore
│
├── utils/
│   ├── config_extractor.py          # Extract per-language JSON for Wikifunctions
│   ├── wikifunctions_api_mock.py    # Z6/Z9 helpers
│   ├── logging_setup.py             # Central logging config
│   ├── build_lexicon_from_wikidata.py
│   ├── dump_lexicon_stats.py
│   ├── refresh_lexicon_index.py
│   └── migrate_lexicon_schema.py
│
├── prototypes/                      # Experimental / matrix demos
│   ├── local_test_runner.py
│   └── shared_romance_engine.py
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ARCHITECTURE_GLOBAL.md
│   ├── ADDING_A_LANGUAGE.md
│   ├── LEXICON_ARCHITECTURE.md
│   ├── LEXICON_SCHEMA.md
│   ├── LEXICON_WORKFLOW.md
│   └── NLG_SIG_PROPOSAL.md
│
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Research & Future Work (Sketch)

* Generalize beyond `BioFrame` to a small inventory of abstract frames (office-holding, award, discovery, membership, etc.).
* Experiment with mapping AW semantic notations (e.g. Ninai / UMR proposals) onto these frame types.
* Improve discourse modelling:

  * richer info-structure decisions,
  * cross-sentence theme–rheme progression for languages with topic-marking and free word order.
* Scale lexicon coverage per language using Wikidata Lexemes, and explore community workflows for manual curation on top.
* Explore CI-style validation on Wikifunctions:

  * running test suites automatically on renderer changes,
  * tracking per-language pass rates over time.



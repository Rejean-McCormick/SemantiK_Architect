# Abstract Wiki Architect

Abstract Wiki Architect is a family-based, data-driven NLG toolkit for **Abstract Wikipedia** and **Wikifunctions**.

Instead of writing one renderer per language (“300 scripts for 300 languages”), this project builds:

- ~15 shared **family engines** (per language family, in Python),
- hundreds of per-language **configuration cards** (grammar matrices + language cards, in JSON),
- a small library of **cross-linguistic constructions** (sentence patterns),
- a **lexicon subsystem** (with bridges to Wikidata / Abstract Wikipedia-style lexemes),
- a small, well-defined inventory of **semantic frames**,
- and a **QA factory** for large, language-specific test suites.

The goal is to provide a **professional, testable architecture** for rule-based NLG across many languages, aligned with the ideas behind Abstract Wikipedia and Wikifunctions, but usable independently.

---

## Intuition: Consoles, Cartridges, and the Router

Think of each sentence as a game you want to play.

- Old way  
  Build **one console per game** (one monolithic renderer per language).

- Abstract Wiki Architect  
  Build **~15 universal consoles** (family engines: Romance, Slavic, Agglutinative, Bantu, etc.).  
  Load **hundreds of cartridges** (per-language JSON cards + lexica).  
  Use a **Router** to plug the right card into the right console.

Example (Romance family):

- The **Romance engine** knows how to:
  - feminize nouns/adjectives,
  - apply plural rules,
  - pick articles.
- The **Italian card** (`data/morphology_configs/romance_grammar_matrix.json` + `data/romance/it.json`) tells it:
  - `-o` → `-a` for feminine,
  - “use `uno` before /z/ or /sC/”.
- The **Spanish card** tweaks only what differs:
  - feminization also `-o` → `-a`,
  - but the singular masculine indefinite article is always `un`.

The **router** sees `lang="it"`, picks the Romance engine, loads the Italian card and lexicon, and calls the appropriate constructions to build the sentence.

---

## Architecture Overview

Very roughly, the architecture is:

> **Engines (families)** + **Configs (languages)** + **Constructions (sentence patterns)**  
> + **Lexica** + **Frames (semantics)** + **Discourse** + **Router/API**

### 1. Engines and Morphology

Family engines in `engines/` (Romance, Slavic, Agglutinative, Germanic, Bantu, Semitic, Indo-Aryan, Iranic, Austronesian, Japonic, Koreanic, Polysynthetic, Celtic, Dravidian, …):

- implement family-level logic (gender systems, cases, agreement, noun classes, etc.),
- do **not** hard-code per-language endings; they consult configuration and lexicon.

Family-specific morphology modules in `morphology/`:

- use grammar matrices in `data/morphology_configs/`  
  (e.g. `romance_grammar_matrix.json`, `slavic_matrix.json`, `agglutinative_matrix.json`),
- use per-language configs (e.g. `data/romance/it.json`, `data/slavic/ru.json`),
- use lemma features from the lexicon,
- expose a small API to constructions (inflect NP, choose article, inflect verb, join tokens).

### 2. Constructions (Sentence Patterns)

Under `constructions/` you get cross-linguistic sentence patterns, for example:

- `copula_equative_simple.py` — “X is a Y”
- `copula_equative_classification.py` — “X is a Polish physicist”
- `copula_attributive_np.py` / `copula_attributive_adj.py`
- `copula_existential.py` — “There is a Y in X”
- `copula_locative.py`
- `possession_have.py` — “X has Y”
- `intransitive_event.py`, `transitive_event.py`, `ditransitive_event.py`, `passive_event.py`
- `relative_clause_subject_gap.py` — “the scientist who discovered Y”
- `coordination_clauses.py`
- `comparative_superlative.py`
- `causative_event.py`
- `topic_comment_copular.py`
- `apposition_np.py`
- …

Constructions are **family-agnostic**:

- they choose roles (SUBJ, PRED, LOC, OBJ, etc.),
- they call morphology + lexicon to realise noun phrases and verbs,
- they can consult discourse state (topic vs focus) when available.

### 3. Frames and Semantics

Under `semantics/` and `docs/FRAMES_*.md`:

- **Core value types**
  - `Entity`, `Location`, `TimeSpan`, `Event`, quantities, etc.
- **Frame families**
  - **Entity frames** (article subjects: persons, organisations, places, works, products, laws, projects, …),
  - **Event frames** (single events / episodes with participants, time, and location),
  - **Relational frames** (statement-level facts: definitions, attributes, measurements, memberships, roles, part–whole, comparisons, …),
  - **Narrative / aggregate frames** (timelines, careers, developments, receptions, comparisons, lists),
  - **Meta frames** (article / section structure, sources).

Normalisation and AW bridge:

- `semantics/normalization.py` turns “loose” input (dicts, CSV rows, JSON) into typed frames.
- `semantics/aw_bridge.py` maps Abstract Wikipedia-style structures (Z-objects, typed slots) into these frames.

Example (biography frame):

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

### 4. Discourse and Information Structure

Under `discourse/`:

* `DiscourseState` for mentioned entities, current topic, and simple salience,
* information-structure helpers (topic vs focus),
* referring expression selection (full name vs short name vs pronoun vs zero subject),
* simple planners to order multiple frames into short multi-sentence descriptions.

This is what lets you move from:

> “Marie Curie is a Polish physicist. Marie Curie discovered radium.”

to:

> “Marie Curie is a Polish physicist. **She** discovered radium.”

and to topic–comment variants for languages where that matters.

### 5. Lexicon Subsystem

Under `lexicon/`:

* types (`Lexeme`, `Form`, …),
* loaders and indices,
* normalisation helpers for lemma lookup,
* bridges to Wikidata Lexemes and Abstract Wikipedia-style lexeme data.

Lexicon data (`data/lexicon/*.json`) typically includes:

* `lemma`, `pos` (`NOUN`, `ADJ`, `VERB`, …),
* features (gender, number, noun class, etc.),
* flags (e.g. `human`, `nationality`),
* cross-links (feminine/masculine, plural/singular),
* optional IDs (`wikidata_qid`, `wikidata_lexeme_id`),
* language-specific details needed by morphology.

Supporting tools:

* build/update lexica from Wikidata (`utils/build_lexicon_from_wikidata.py`),
* schema validation & smoke tests,
* coverage reports relative to QA test suites (`qa_tools/lexicon_coverage_report.py`),
* per-language lexicon statistics (`utils/dump_lexicon_stats.py`).

### 6. Router and NLG API

`language_profiles/profiles.json` defines per-language profiles (family, default constructions, key settings).

`router.py` is the internal entry point:

* given a language and either:

  * higher-level arguments (name, profession, nationality, …), or
  * explicit semantic frames,
* loads the language profile and lexicon,
* selects the family engine and constructions,
* returns a surface string.

Typical internal usages:

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

On top of this, there is a small **public NLG API** (see `docs/FRONTEND_API.md` and `NLG Frontend API Documentation.md`):

```python
from nlg.api import generate_bio, generate
from semantics.types import Entity, BioFrame

bio = BioFrame(
    main_entity=Entity(name="Douglas Adams", gender="male", human=True),
    primary_profession_lemmas=["writer"],
    nationality_lemmas=["british"],
)

result = generate_bio(lang="en", bio=bio)
print(result.text)       # "Douglas Adams was a British writer."
print(result.sentences)  # ["Douglas Adams was a British writer."]

result2 = generate(lang="fr", frame=bio)
print(result2.text)
```

The API returns a `GenerationResult` (final text, sentence list, debug info) and hides router/engine/lexicon internals from callers.

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

### 2. Minimal example

```python
from nlg.api import generate_bio
from semantics.types import Entity, BioFrame

albert = Entity(name="Albert Einstein", gender="male", human=True)

bio = BioFrame(
    main_entity=albert,
    primary_profession_lemmas=["physicist"],
    nationality_lemmas=["german"],
)

result = generate_bio(lang="en", bio=bio)
print(result.text)
# Example: "Albert Einstein was a German physicist."
```

### 3. Generate test suites

Use the test-suite generator to create CSV templates:

```bash
python qa_tools/test_suite_generator.py
```

Example outputs:

* `qa_tools/generated_datasets/test_suite_it.csv`
* `qa_tools/generated_datasets/test_suite_fr.csv`
* `qa_tools/generated_datasets/test_suite_tr.csv`
* …

Fill the `EXPECTED_OUTPUT` (or `EXPECTED_FULL_SENTENCE`) column with gold sentences (LLM-assisted or native speakers).

### 4. Run the test runner

```bash
python qa/test_runner.py
```

The test runner:

* scans `qa_tools/generated_datasets/` (or `qa/generated_datasets/`) for `test_suite_*.csv`,
* builds frames from each row,
* calls the renderer,
* compares actual vs expected outputs,
* prints per-language and global pass/fail statistics and a mismatch report.

### 5. Inspect lexicon coverage (optional)

```bash
python utils/dump_lexicon_stats.py
```

For test-suite alignment:

```bash
python qa_tools/lexicon_coverage_report.py
```

---

## Mapping to Wikifunctions

### Z-Object mock

`utils/wikifunctions_api_mock.py` provides a small Z-Object mock:

* `Z6(text)` to wrap a string as Z6,
* `Z9(zid)` to wrap a reference as Z9,
* `unwrap` / `unwrap_recursive` to convert nested Z-objects to plain Python.

Example (simulated Wikifunctions call):

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

### JSON cards for Wikifunctions

Language-specific JSON cards can be extracted for use as Z-data:

```bash
# Extract Italian Romance configuration payload for Wikifunctions
python utils/config_extractor.py it
```

The printed JSON can be passed as an argument to Z-implementations of family engines on Wikifunctions (logic in Z-functions, cards as Z-data).

---

## Adding a New Language (High-Level Recipe)

1. **Choose a family**

   * pick or create a family engine in `engines/<family>.py`,
   * ensure there is a matching morphology module in `morphology/`.

2. **Add lexicon entries**

   * create or edit `data/lexicon/<lang>_lexicon.json`,
   * include common professions, nationality adjectives, country/city names, basic biography verbs.

3. **Add or extend morphology config**

   * for Romance:

     * add the language entry to `data/morphology_configs/romance_grammar_matrix.json`,
     * optionally add `data/romance/<lang>.json` for overrides.
   * for other families:

     * add a similar entry under `data/morphology_configs/` (and `data/<family>/` if used).

4. **Create a language profile**

   * add an entry in `language_profiles/profiles.json`:

     * family,
     * default constructions,
     * key flags (e.g. postposed definite articles, topic-marker language).

5. **Generate and fill test suite**

   * run `qa_tools/test_suite_generator.py`,
   * fill `EXPECTED_OUTPUT` for `test_suite_<lang>.csv`.

6. **Run tests and iterate**

   * `python qa/test_runner.py`,
   * refine configs + lexicon until the language passes most tests.

More details are in `docs/ADDING_A_LANGUAGE.md`.

---

## Project Structure (High-Level)

```text
abstract-wiki-architect/
├── router.py
├── language_profiles/
├── engines/           # family engines
├── morphology/        # family-level morphology
├── constructions/     # sentence patterns
├── semantics/         # frames and core types
├── discourse/         # discourse and information structure
├── lexicon/           # lexicon subsystem
├── data/              # configs, cards, lexica
├── qa_tools/          # test suite generator & helpers
├── qa/                # test runner & unit tests
├── utils/             # tools (Wikifunctions mock, lexicon builders, etc.)
├── docs/              # architecture, frames, lexicon, API, hosting
└── pyproject.toml
```

For a more detailed description, see the wiki:

* [https://github.com/Rejean-McCormick/abstract-wiki-architect/wiki](https://github.com/Rejean-McCormick/abstract-wiki-architect/wiki)

---

## Status (December 2025)

**Works reasonably well**

* first-sentence biography generation from `BioFrame` across several families,
* end-to-end path (frames → constructions → engines → morphology → lexicon → text),
* JSON lexica and Wikidata bridges,
* CSV-based QA and test-suite tooling,
* basic Z-Object mock and config extractors for Wikifunctions.

**Still in progress**

* full coverage beyond biographies (events, roles, awards, membership, etc.),
* deeper lexicon and morphology coverage per language,
* richer discourse and multi-sentence output,
* more tooling for non-coders (card/lexicon/test editors),
* tighter integration with real Wikifunctions Z-implementations and data.

---

## Links

* Repository:
  [https://github.com/Rejean-McCormick/abstract-wiki-architect](https://github.com/Rejean-McCormick/abstract-wiki-architect)

* Wiki (architecture, frames, lexicon, API):
  [https://github.com/Rejean-McCormick/abstract-wiki-architect/wiki](https://github.com/Rejean-McCormick/abstract-wiki-architect/wiki)

* Meta-Wiki tools page:
  [https://meta.wikimedia.org/wiki/Abstract_Wikipedia/Tools/abstract-wiki-architect](https://meta.wikimedia.org/wiki/Abstract_Wikipedia/Tools/abstract-wiki-architect)


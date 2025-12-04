# Lexicon Architecture

This document describes the lexicon subsystem used by Abstract Wiki Architect.

The goal of the lexicon layer is to provide a **language-agnostic, data-driven source of lexical information** that can be used by:

- Morphology engines (to pick correct forms, gender, noun class, etc.).
- Constructions (to know which lemmas can fill which slots).
- Semantics and discourse (for entity typing, human/non-human, etc.).
- External bridges (Wikidata, Abstract Wikipedia lexemes).

---

## 1. High-level overview

The lexicon subsystem consists of four main pieces:

1. **Data files (`data/lexicon/*.json`)**

   - One or more JSON files per language (e.g. `en_lexicon.json`, `es_lexicon.json`).
   - Optional domain-specific shards (e.g. `en_science.json`).
   - A global JSON schema (`data/lexicon_schema.json`) that defines the allowed structure.

2. **Runtime package (`lexicon/*`)**

   - Pure-Python code that:
     - Loads lexicon JSON.
     - Normalizes keys.
     - Builds in-memory indices.
     - Exposes lookup functions.

3. **External bridges**

   - Code to convert Wikidata / Abstract Wikipedia lexeme objects into internal `Lexeme` structures:
     - `lexicon/wikidata_bridge.py`
     - `lexicon/aw_lexeme_bridge.py`

4. **Tools and QA**

   - Scripts to:
     - Build/update lexicon JSON files from external sources.
     - Check for collisions / schema violations.
     - Generate regression tests for lexicon inventories.

The lexicon is **read-only at runtime**: all heavy lifting (importing from Wikidata, cleaning data, merging shards) happens offline via scripts under `utils/`.

---

## 2. Data model

### 2.1. JSON layout

Each lexicon file has this general shape:

```json
{
  "_meta": {
    "language": "en",
    "version": 1,
    "domain": "science",
    "description": "Human-readable description"
  },
  "lemmas": {
    "physicist": {
      "pos": "NOUN",
      "gloss": "a scientist who studies physics",
      "human": true,
      "number": "count",
      "semantic_field": "physics"
    },
    "polish": {
      "pos": "ADJ",
      "gloss": "Polish (relating to Poland)",
      "nationality": true,
      "country_qid": "Q36"
    }
  }
}
````

Notes:

* The **lemma keys** under `"lemmas"` are not case-sensitive at runtime; they are normalized by `lexicon.normalization`.
* The `"pos"` field uses a small POS inventory (`"NOUN"`, `"ADJ"`, `"VERB"`, etc.).
* Additional fields are allowed (`"gender"`, `"human"`, `"irregular_forms"`, `"multiword"`, `"semantic_field"`, etc.), and are passed through to the runtime data model.

### 2.2. Python dataclasses

The lexicon package exposes typed structures in `lexicon/types.py`:

* `Form`
* `Sense`
* `Lexeme`

Example (conceptual, not required to be exact):

```python
@dataclass
class Form:
    form: str
    features: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Sense:
    id: Optional[str] = None
    glosses: Dict[str, str] = field(default_factory=dict)
    domains: List[str] = field(default_factory=list)


@dataclass
class Lexeme:
    id: Optional[str] = None       # e.g. Wikidata lexeme ID
    language: str = ""             # e.g. "en"
    lemma: str = ""                # canonical lemma
    pos: str = ""                  # e.g. "NOUN"
    forms: List[Form] = field(default_factory=list)
    senses: List[Sense] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
```

The JSON `"lemmas"` entries are mapped into `Lexeme` objects. Some fields (like `"gloss"`, `"gender"`, `"human"`) are placed in `Lexeme.extra` or further expanded into `Sense`/`Form` as needed.

---

## 3. Loading and normalization

### 3.1. Normalization strategy

The lexicon subsystem must be tolerant of:

* Differences in capitalization: `Physicist` vs `physicist`.
* Extra spaces, underscores, punctuation variants: `"Nobel Prize – Physics"` vs `"nobel_prize-physics"`.

This is handled by `lexicon/normalization.py`, which provides:

* `normalize_for_lookup(text: str) -> str`

  * NFKC Unicode normalization.
  * Standardize punctuation (curly quotes → `'`, en/em-dash → `-`).
  * Turn underscores into spaces.
  * Collapse whitespace.
  * Case-fold the result.

Example:

```python
from lexicon.normalization import normalize_for_lookup

normalize_for_lookup("  Nobel   Prize – in Physics ")
# -> "nobel prize - in physics"
```

Lookup keys in the index are always the normalized form.

### 3.2. Loading and indexing

* `lexicon/loader.py`:

  * Functions like `load_lexicon_file(path)` and `load_language_lexica(lang)` that read JSON into Python dicts and then construct `Lexeme` objects.

* `lexicon/index.py`:

  * Builds per-language indices:

    * `lemma_index[normalized_lemma] -> Lexeme`
    * `qid_index[qid] -> Lexeme` (if QIDs are present).
  * Exposes lookup helpers, e.g.:

    ```python
    from lexicon.index import get_lexeme_by_lemma, get_lexeme_by_qid

    lex = get_lexeme_by_lemma("en", "physicist", pos="NOUN")
    ```

* `lexicon/cache.py`:

  * Ensures that lexica are loaded once and reused.
  * Optionally preloads frequently used languages.

---

## 4. External bridges

### 4.1. Wikidata bridge

* `lexicon/wikidata_bridge.py`:

  * Target: offline import from Wikidata (lexemes or Q-items) into lexicon JSON.
  * Responsibilities:

    * Parse Wikidata lexeme or entity dumps.
    * Map fields to internal `Lexeme` structure.
    * Filter out irrelevant data and simplify features.

* Typical usage (offline):

  ```bash
  python utils/build_lexicon_from_wikidata.py --lang en --output data/lexicon/en_lexicon.json
  ```

### 4.2. Abstract Wikipedia lexeme bridge

* `lexicon/aw_lexeme_bridge.py`:

  * Converts AW/Wikifunctions Z-lexeme objects (or similar JSON) to `Lexeme`.
  * Uses `unwrap_recursive` from `utils/wikifunctions_api_mock.py` to strip Z6/Z9 wrappers.
  * Handles multiple shapes for senses and forms (lists, maps, etc.).

Example (conceptual):

```python
from lexicon.aw_lexeme_bridge import lexeme_from_z_object

lex = lexeme_from_z_object(z_lexeme)
```

This allows your engines to work with AW lexemes using the same internal model as locally defined lexicon entries.

---

## 5. Runtime usage

At runtime, the lexicon is used by:

1. **Router**

   * Accepts high-level semantic frames (`BioFrame`, etc.).
   * For each lemma string (profession, nationality, etc.):

     * Calls `lexicon.index` to resolve it to a `Lexeme`.
   * Passes the `Lexeme` (or at least its extra features) into engines and morphology.

2. **Morphology engines (`morphology/*.py`)**

   * Use the lexeme’s features:

     * `gender`, `human`, `irregular_forms`, `semantic_field`.
   * For languages with rich morphology:

     * `forms` may store precomputed forms.
     * Or the engine generates forms from lemma + features.

3. **Constructions**

   * Use lexicon info to:

     * Filter which lemmas can fill which slot (e.g. human-only subjects).
     * Implement language-specific constraints (e.g. “nationality as adjective” vs “nationality as noun”).

---

## 6. QA and maintenance

### 6.1. Coverage and collisions

* `qa_tools/lexicon_coverage_report.py`:

  * Compares lemmas in test suites (`qa_tools/generated_datasets/*.csv`) with lexica.
  * Reports which lemmas are missing from lexicon JSON files.

* `utils/refresh_lexicon_index.py`:

  * Loads lexicon JSON.
  * Applies `normalize_for_lookup` to all lemma keys.
  * Detects collisions:

    * Multiple raw keys that normalize to the same canonical key.
  * Prints a summary and non-zero exit on problems.

### 6.2. Regression tests

* `qa_tools/generate_lexicon_regression_tests.py`:

  * Scans `data/lexicon/*.json`.
  * Generates `qa/test_lexicon_regression.py` with a snapshot of lemma keys per file.
  * During `pytest`:

    * Any change in lemma inventories (added/removed/renamed lemma keys) is detected.
    * Intentional changes require regenerating the regression tests.

### 6.3. Schema evolution

* `data/lexicon_schema.json` and `lexicon/schema.py`:

  * Define the allowed structure of lexicon JSONs.
  * Used by smoke tests (`qa_tools/lexicon_smoke_tests.py`) and by migration scripts (`utils/migrate_lexicon_schema.py`).

---

## 7. Extending the lexicon

To add or grow lexicon coverage for a language:

1. **Add / edit JSON files**

   * Create or edit `data/lexicon/<lang>_lexicon.json`.
   * For domain-specific sets, add `data/lexicon/<lang>_<domain>.json` (e.g. `en_science.json`).

2. **Validate**

   * Run:

     ```bash
     python utils/refresh_lexicon_index.py
     python qa_tools/lexicon_coverage_report.py
     ```

   * Fix collisions and missing lemmas as reported.

3. **Regenerate regression tests**

   * If lemma inventories changed intentionally:

     ```bash
     python qa_tools/generate_lexicon_regression_tests.py
     pytest
     ```

4. **Integrate with Wikidata (optional)**

   * Use `utils/build_lexicon_from_wikidata.py` to bootstrap or update lexica from Wikidata data.

5. **Use in engines/constructions**

   * Ensure engines and constructions refer to lexicon features instead of hard-coded knowledge about lemmas.

---

## 8. Summary

The lexicon architecture:

* Separates **lexical data** from **code**.
* Provides a uniform **internal model (`Lexeme`)** across languages and sources.
* Integrates with **Wikidata** and **Abstract Wikipedia lexemes** via bridges.
* Is backed by **QA tooling** to detect collisions and unintended changes.
* Supports scaling to many domains and languages via JSON lexicon files + offline builders.

This layer underpins morphology, constructions, and semantics by providing a consistent, high-quality source of lexical information.


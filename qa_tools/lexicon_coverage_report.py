# Lexicon Workflow

This document describes how to work with the **lexicon subsystem** of
_Abstract Wiki Architect_:

- where lexicon files live,
- how they are structured,
- how to build / update them (manually or from Wikidata),
- how to run coverage and sanity checks.

The goal is that a contributor can:

1. Add or extend a lexicon for a new language.
2. Keep lexica in sync with evolving tests.
3. Integrate external sources (Wikidata, etc.) in a controlled way.

---

## 1. Where things live

### 1.1. On disk

All lexicon data and helpers are under:

- `data/lexicon/`
  - `*_lexicon.json` for each language.
  - Optional domain shards (e.g. `en_science.json`) if we ever split.
- `data/lexicon_schema.json`
  - JSON Schema for lexicon files.
- `data/raw_wikidata/`
  - For local Wikidata / lexeme dumps and intermediate files
    (ignored by git, see `.gitignore`).

Python code:

- `lexicon/`
  - `types.py` — data classes (`Lexicon`, `BaseLexicalEntry`, etc.).
  - `loader.py` — load JSON into `Lexicon`.
  - `index.py` — build lookup indices and provide convenient queries.
  - `normalization.py` — helper functions to normalize lemma strings.
  - `cache.py`, `config.py`, `errors.py`, `wikidata_bridge.py`, etc.

QA utilities:

- `qa_tools/lexicon_coverage_report.py` — compare tests vs lexicon.
- `qa_tools/lexicon_smoke_tests.py` — schema / sanity checks (optional).
- `qa/test_lexicon_index.py` — unit tests for the index layer.

---

## 2. Lexicon JSON structure (quick overview)

Each `data/lexicon/<lang>_lexicon.json` file has:

```json
{
  "meta": {
    "language": "it",
    "family": "romance",
    "version": "0.2.0",
    "description": "Short description of this lexicon"
  },

  "professions": { ... },
  "nationalities": { ... },
  "titles": { ... },
  "honours": { ... },
  "entries": { ... },
  "name_templates": { ... }
}
````

The schema is defined in `data/lexicon_schema.json` and mapped to code
via `lexicon/types.py`. In brief:

* `professions` → `ProfessionEntry`
* `nationalities` → `NationalityEntry`
* `titles` → `TitleEntry`
* `honours` → `HonourEntry`
* `entries` (catch-all) → `BaseLexicalEntry`
* `name_templates` → `NameTemplate`

Every lexical entry has at least:

* `key` — stable map key in the JSON file.
* `lemma` — canonical lemma / surface form.
* `pos` — part of speech (e.g. `"NOUN"`, `"ADJ"`, `"TITLE"`).
* `language` — language code (same as `meta.language`).
* `forms` — dictionary of inflected forms (may be empty `{}`).
* `extra` — free-form metadata.

`lexicon/types.py` has full documentation for each field.

---

## 3. Manual editing workflow

### 3.1. When to edit by hand

Edit lexicon JSON by hand when you:

* add or tweak a *small* number of entries (e.g. new profession),
* fix a grammatical gender or inflection,
* adjust a nationality label or country name,
* improve glosses or meta information.

For large-scale additions, see the Wikidata workflow (section 4).

### 3.2. Step-by-step: add a profession for a language

Example: add “composer” to Italian.

1. Open the file:

   ```text
   data/lexicon/it_lexicon.json
   ```

2. Locate or create the `professions` section:

   ```json
   "professions": {
     ...
   }
   ```

3. Add a new entry under a new key `compositore`:

   ```json
   "compositore": {
     "key": "compositore",
     "lemma": "compositore",
     "pos": "NOUN",
     "language": "it",
     "sense": "profession",
     "human": true,
     "gender": "m",
     "default_number": "sg",
     "default_formality": "neutral",
     "wikidata_qid": null,
     "forms": {
       "m.sg": "compositore",
       "f.sg": "compositrice",
       "m.pl": "compositori",
       "f.pl": "compositrici"
     },
     "extra": {
       "gloss": "composer"
     }
   }
   ```

4. Save the file.

5. Validate it (see section 5).

---

## 4. Building lexica from Wikidata (offline)

For broad coverage, you typically do **offline** or **one-off** builds
from Wikidata or lexeme dumps, then commit the resulting JSON.

### 4.1. Get a dump (or configure API access)

Place your dumps under:

```text
data/raw_wikidata/
```

Examples (not committed to git):

* `data/raw_wikidata/lexemes_dump.json.gz`
* `data/raw_wikidata/README.md` (with notes on source / date)

Alternatively, configure the bridge to call the Wikidata API directly
(if you choose to implement that).

### 4.2. Implement and run the builder

The builder script is:

```text
utils/build_lexicon_from_wikidata.py
```

Typical responsibilities:

* read a dump or API responses,
* filter relevant items (e.g. human professions, nationalities),
* map them into internal structures (see `lexicon/types.py`),
* write a `data/lexicon/<lang>_lexicon.json` file.

Example (for a single language):

```bash
python utils/build_lexicon_from_wikidata.py --lang it
```

Example (for several languages):

```bash
python utils/build_lexicon_from_wikidata.py --lang it --lang fr --lang sw
```

The exact CLI options depend on how you implement the script, but a
common pattern is:

* `--lang <code>` — language to build.
* `--dump-path <file>` — optional override for the raw dump path.
* `--output <file>` — optional override for output file.

---

## 5. Validating lexicon files

### 5.1. Structural validation against schema

Use a small smoke test (either `qa_tools/lexicon_smoke_tests.py` or a
pytest file) to validate all lexicon JSONs against
`data/lexicon_schema.json`.

If you create a dedicated script:

```bash
python qa_tools/lexicon_smoke_tests.py
```

Typical checks:

* JSON is well-formed.
* `meta.language` is present.
* required fields (`key`, `lemma`, `pos`, `language`) are present.
* no gross type mismatches.

### 5.2. Schema migration

If you change the schema (e.g. add new required fields), use the
migration helper:

```bash
python utils/migrate_lexicon_schema.py --all
```

Options:

* `--file <path>` — migrate a single lexicon file.
* `--all` — migrate all `data/lexicon/*.json`.
* `--dry-run` — show what would change, but do not write.
* `--no-backup` — do not create `*.bak` backups.

You can also set the target version:

```bash
python utils/migrate_lexicon_schema.py --all --target-version 0.2.0
```

---

## 6. Coverage vs QA test suites

The lexicon’s usefulness is measured by **how much of the QA test
data it covers**.

### 6.1. Run the coverage report

From project root:

```bash
python qa_tools/lexicon_coverage_report.py
```

What it does:

* scans QA CSVs in:

  * `qa_tools/generated_datasets/` or
  * `qa/generated_datasets/`
* extracts lemma-like columns (e.g. `PROFESSION_LEMMA`, `NATIONALITY_LEMMA`),
* checks if those lemmas exist in the lexicon for the corresponding
  language.

You can focus on a specific language:

```bash
python qa_tools/lexicon_coverage_report.py --lang it
```

You will see, for each language:

* how many lemmas appear in tests,
* how many are known to the lexicon,
* which lemmas are missing.

Use this to decide where to invest effort (e.g. add missing professions
for highly tested languages).

---

## 7. Runtime usage (how engines see the lexicon)

At runtime, typical flow is:

1. **Load lexicon**

   ```python
   from lexicon.loader import load_lexicon
   lex = load_lexicon("it")  # returns lexicon.types.Lexicon
   ```

2. **Build index**

   ```python
   from lexicon.index import LexiconIndex
   idx = LexiconIndex(lex)
   ```

3. **Look up entries from semantics / router**

   Example: from a `BioFrame` with `primary_profession_lemmas`:

   ```python
   from semantics.types import BioFrame

   def resolve_profession(frame: BioFrame, idx: LexiconIndex):
       for lemma in frame.primary_profession_lemmas:
           entry = idx.lookup_profession(lemma)
           if entry is not None:
               return entry
       return None
   ```

4. **Feed forms into morphology / constructions**

   ```python
   prof = idx.lookup_profession("physicist")
   surface = prof.get_form(gender="f", number="sg")  # e.g. 'fisica' in Italian
   ```

The lexicon APIs (`Lexicon`, `LexiconIndex`) are designed to keep
language-specific details **out** of the engines and constructions as
much as possible.

---

## 8. Adding a new language: lexicon checklist

When adding a new language to the whole system, you ultimately need to:

1. **Create an initial lexicon file**:

   ```text
   data/lexicon/<lang>_lexicon.json
   ```

   * You can:

     * copy a small template from an existing language and adapt it, or
     * generate it via `build_lexicon_from_wikidata.py`.

2. **Fill in `meta`**:

   * `language` (required),
   * `family` (optional but recommended),
   * `description`.

3. **Populate at least**:

   * `professions` (the set used by your current tests),
   * `nationalities` (for nationality adjectives / demonyms),
   * `entries` (basic nouns like “person”, “woman”, etc.),
   * `name_templates` (how personal names are assembled).

4. **Run schema and coverage checks**:

   ```bash
   python qa_tools/lexicon_coverage_report.py --lang <lang>
   ```

   If coverage is low, add missing entries or adjust the test set.

5. **Hook into morphology / engines**:

   * Ensure the appropriate family engine uses the lexicon entries
     (profession, nationality, etc.) rather than hard-coded strings.

---

## 9. Future extensions

The workflow above is intentionally simple but scales to more advanced
scenarios:

* Multiple domain lexica per language (`en_core.json`, `en_science.json`).
* Incremental builds from Wikidata.
* Integration with Abstract Wikipedia lexeme Z-objects via
  `lexicon/aw_lexeme_bridge.py`.
* More sophisticated sense inventories and disambiguation.

The important part is that **all** of those still flow through the
same types (`Lexicon`, `BaseLexicalEntry`, `ProfessionEntry`, etc.)
and are validated by the same schema (`data/lexicon_schema.json`),
so renderers and engines do not have to care where the data came from.



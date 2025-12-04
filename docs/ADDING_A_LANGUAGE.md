# Adding a New Language

This document describes the **end-to-end workflow** for adding a new language
to Abstract Wiki Architect.

The goal is:

- Minimal boilerplate per language.
- Most logic lives in **shared engines** and **constructions**.
- Each language contributes:
  - A **lexicon** (`data/lexicon/<lang>_lexicon.json`),
  - A **morphology config** (e.g. a family JSON / config),
  - A **language profile** (routing + flags),
  - A **test suite**.

Below, `<lang>` is the BCP-47 language code (e.g. `it`, `tr`, `sw`, `ja`).


---

## 0. Decide: which “family engine”?

Before writing anything, decide **which engine** should handle the new language:

- Romance → `engines/romance.py`
- Agglutinative → `engines/agglutinative.py`
- Germanic → `engines/germanic.py`
- Bantu / Niger-Congo → `engines/bantu.py` (or similar)
- Isolating → `engines/isolating.py`
- Slavic → `engines/slavic.py`
- … (others as you add them)

If your language doesn’t fit neatly, pick the **closest** family for now and
document the mismatches in the profile (see below).


---

## 1. Create (or extend) the lexicon

### 1.1 Create the lexicon JSON file

Create:

```text
data/lexicon/<lang>_lexicon.json
````

Start with this minimal structure:

```json
{
  "meta": {
    "language": "<lang>",
    "schema_version": 1,
    "description": "Lexicon for <LanguageName> (prototype).",
    "source": "hand_curated"
  },

  "lemmas": {
  }
}
```

You may also choose to split into sections (`professions`, `nationalities`,
`titles`, `honours`, …) like the Italian / Turkish / Japanese examples.

### 1.2 Populate core entries

At minimum, for **biographical first sentences**, you will need:

* Professions:

  * “physicist”, “chemist”, “writer”, “politician”, “doctor”, “musician”, etc.
* Nationalities:

  * “Polish”, “French”, “German”, “American”, `<your country>`…
* Titles (optional but recommended):

  * “king”, “queen”, “president”, etc.
* Honours (optional):

  * Nobel prizes, major awards.

Follow the schema in `docs/LEXICON_SCHEMA.md`. Example (profession):

```json
"professions": {
  "physicist_lemma_key": {
    "lemma": "PHYSICIST_SURFACE_OR_BASE",
    "pos": "NOUN",
    "category": "profession",
    "human": true,
    "gender": "none",
    "forms": {
      "default": "PHYSICIST_SURFACE_FORM"
    },
    "features": {
      "scientific_field": ["physics"]
    },
    "qid": "Q169470"
  }
}
```

Adapt `forms` to your language’s inflection (`masc_sg`, `fem_sg`, `plural`, etc.).

### 1.3 (Optional) Build from Wikidata

If you want broad coverage, you can seed your lexicon from a **Wikidata Lexeme
dump**:

1. Put (or reference) a filtered dump under `data/raw_wikidata/`.

2. Run:

   ```bash
   python utils/build_lexicon_from_wikidata.py \
       --lang <lang> \
       --dump data/raw_wikidata/lexemes_dump.json.gz \
       --out data/lexicon/<lang>_lexicon.json
   ```

3. Hand-edit / prune / augment as needed.

---

## 2. Hook the lexicon into the loader & schema

No extra file is needed if you follow the naming convention
`<lang>_lexicon.json` in `data/lexicon/`. The loader automatically picks it up.

You *should* run the lexicon smoke tests:

```bash
pytest qa_tools/lexicon_smoke_tests.py
```

This checks:

* JSON is valid.
* Basic structural schema is respected.
* `meta.language` matches `<lang>`.

---

## 3. Add family-specific morphology config

Each engine expects its language configuration in a family-specific place.

Typical patterns (examples; adapt to your project layout):

* Romance:

  * `data/morphology_configs/romance_grammar_matrix.json`
  * Add an entry for `<lang>` in the `languages` section.
* Agglutinative:

  * `data/morphology_configs/agglutinative/<lang>.json`
* Isolating:

  * `data/morphology_configs/isolating/<lang>.json`
* Bantu:

  * `data/morphology_configs/bantu/<lang>.json`
* etc.

The config usually contains:

* Article system (if any),
* Gender/number categories,
* Noun/adjective inflection rules,
* Phonological triggers (vowel harmony, sandhi, elision).

Follow the existing family examples (e.g. Italian / Turkish configs). Make sure
your engine (e.g. `engines/romance.py`) knows how to read the config.

---

## 4. Register the language profile (router)

The router needs to know:

* Which **engine** to use,
* Where to get **morphology config**,
* Any flags (e.g. topic–comment default, pro-drop, copula schemes).

This usually lives in something like:

```text
language_profiles/profiles.json
```

(Or a Python equivalent.)

Add an entry:

```json
"<lang>": {
  "name": "<LanguageName>",
  "family": "romance | agglutinative | isolating | ...",
  "engine": "romance | agglutinative | ...",
  "morphology_config_path": "data/morphology_configs/<family>/<lang>.json",
  "lexicon_path": "data/lexicon/<lang>_lexicon.json",
  "features": {
    "pro_drop": true,
    "has_gender": false,
    "uses_postposed_definite_article": false,
    "default_order": "SVO",
    "topic_comment_preference": "neutral | strong | weak"
  }
}
```

Then update `router.py` (or equivalent) so that:

* `render_bio(..., lang_code="<lang>")`:

  * finds this profile,
  * instantiates the correct engine,
  * loads the config / lexicon.

---

## 5. Add test suites (QA)

### 5.1 Generate a CSV test template

Use the QA generator (adapt path if needed):

```bash
python qa_tools/test_suite_generator.py
```

This normally creates:

```text
qa_tools/generated_datasets/test_suite_<lang>.csv
```

Check that `<lang>` is included; if not, add it to whatever config the generator uses.

### 5.2 Fill the expected outputs

Open `qa_tools/generated_datasets/test_suite_<lang>.csv` in a spreadsheet or editor.

For each row:

* Fill `EXPECTED_OUTPUT` or `EXPECTED_FULL_SENTENCE` (depending on your schema).
* Use your language’s correct sentence for the abstract data in that row.

You can use an LLM or native speakers to help, but treat it as **gold** once
you commit it.

### 5.3 Run the universal test runner

Run:

```bash
python qa/test_runner.py
```

Check that the summary includes `<lang>` with reasonable pass rates. Iterate on:

* lexicon entries,
* morphology config,
* constructions / engine behavior,

until most tests pass.

For a new language, even ~60–70% pass on a rich test suite is a good start.

---

## 6. Wire constructions (if needed)

Most **constructions** are family-agnostic and should work out of the box:

* `constructions/copula_equative.py`
* `constructions/copula_existential.py`
* `constructions/possession_have.py`
* `constructions/relative_clause_subject_gap.py`
* etc.

Only adjust them when:

* Your language needs different **clause types** (e.g. topic markers, copula
  omission, serial verbs).
* You want to add language-specific variants for some constructions.

Any language-specific behavior should be:

* Expressed via **features** in the language profile, or
* Encoded in the **family engine** and morphology, not as a gap in the generic constructions if possible.

---

## 7. Document the language

Finally, document your new language in `docs/`:

* Add a section to `docs/LEXICON_ARCHITECTURE.md` (or a new file such as
  `docs/LANGUAGE_NOTES_<LANG>.md`) with:

  * Overview of:

    * Word order,
    * Morphology type (agglutinative, fusional, isolating, etc.),
    * Articles / definiteness,
    * Gender / noun classes.
  * Any non-standard choices you made in:

    * `data/lexicon/<lang>_lexicon.json`,
    * morphology config.

This will help future contributors understand why the language behaves the way it does.

---

## 8. Checklist

Use this quick checklist before committing:

* [ ] `data/lexicon/<lang>_lexicon.json` created, passes:

  * [ ] `pytest qa_tools/lexicon_smoke_tests.py`
* [ ] Morphology config added under `data/morphology_configs/...`.
* [ ] Language profile entry added (family, engine, paths).
* [ ] Router updated so `render_bio(..., lang_code="<lang>")` works.
* [ ] `qa_tools/generated_datasets/test_suite_<lang>.csv` filled with gold sentences.
* [ ] `python qa/test_runner.py` runs and reports `<lang>` with non-trivial coverage.
* [ ] Basic manual sanity checks (a few `render_bio` calls) look correct.
* [ ] Documentation updated under `docs/`.

Once all boxes are checked, your new language is integrated into the system and
ready to be shown to others or proposed for Abstract Wikipedia experiments.



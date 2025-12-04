# Lexicon JSON Schema

This document specifies the JSON schema used for all lexicon files under:

```text
data/lexicon/*.json
````

These lexica are consumed by:

* `lexicon/loader.py`
* `lexicon/schema.py`
* `qa_tools/lexicon_smoke_tests.py`
* morphology / engines / router

The goal is to keep the schema:

* **Simple** enough for hand-editing.
* **Regular** enough for tooling and validation.
* **Flexible** enough to host Wikidata-derived entries and hand-curated data.

## 1. Versioning

The current internal schema version is:

```python
SCHEMA_VERSION = 1  # see lexicon/schema.py
```

Each lexicon file must declare this in its metadata:

```json
{
  "meta": {
    "language": "it",
    "schema_version": 1,
    "...": "..."
  },
  ...
}
```

## 2. Top-level structure

Each lexicon file is a single JSON object (dict). At minimum:

```json
{
  "meta": { ... },
  "...lemma_sections...": { ... }
}
```

Allowed top-level keys:

* `meta` (preferred) or `_meta` (legacy)
* Any number of **lemma sections**, such as:

  * `lemmas`
  * `entries`
  * `professions`
  * `nationalities`
  * `titles`
  * `honours`

Example (Italian):

```json
{
  "meta": {
    "language": "it",
    "schema_version": 1,
    "description": "Demonstrative Italian lexicon..."
  },
  "professions": { ... },
  "nationalities": { ... },
  "titles": { ... },
  "honours": { ... }
}
```

## 3. `meta` section

`meta` **must** be an object:

```json
"meta": {
  "language": "it",
  "schema_version": 1,
  "description": "Short human-readable description",
  "source": "hand_curated | wikidata_lexeme_dump | mixed",
  "source_dump": "lexemes_dump.json.gz",
  "entries_total": 123456,
  "entries_used": 7890
}
```

Fields:

* `language` (string, recommended)

  * Language code for this lexicon, e.g. `"it"`, `"tr"`, `"ja"`.
  * The validator compares this to the filename-derived language.

* `schema_version` (int, recommended)

  * Must be `1` for this schema version.

* `description` (string, optional)

  * Short text describing the lexicon.

* `source` (string, optional)

  * Example values: `"hand_curated"`, `"wikidata_lexeme_dump"`, `"mixed"`.

* `source_dump` (string, optional)

  * Name of the source dump file if applicable.

* `entries_total` / `entries_used` (int, optional)

  * Statistics recorded by offline builders (e.g. from Wikidata).

## 4. Lemma sections

Each lemma section is a **dictionary mapping lemma → entry object**.

Common section names:

* `lemmas`
* `entries`
* `professions`
* `nationalities`
* `titles`
* `honours`

Example (excerpt from `data/lexicon/it_lexicon.json`):

```json
"professions": {
  "fisico": {
    "lemma": "fisico",
    "pos": "NOUN",
    "category": "profession",
    "human": true,
    "gender": "masc",
    "forms": {
      "masc_sg": "fisico",
      "fem_sg": "fisica",
      "masc_pl": "fisici",
      "fem_pl": "fisiche"
    },
    "features": {
      "scientific_field": ["fisica"]
    },
    "qid": "Q169470"
  }
}
```

Constraints:

* Section must be an object (`{}`).
* Keys must be strings (the lemma key.
* Values must be objects (entry definitions).

## 5. Lexeme entry structure

Each lemma entry is an object with at least:

```json
{
  "lemma": "fisico",
  "pos": "NOUN",
  "category": "profession",
  "human": true,
  "gender": "masc",
  "forms": {
    "masc_sg": "fisico",
    "fem_sg": "fisica",
    "masc_pl": "fisici",
    "fem_pl": "fisiche"
  },
  "features": {
    "scientific_field": ["fisica"]
  },
  "qid": "Q169470"
}
```

### 5.1 Fields

* `lemma` (string, required)

  * Canonical lemma form.

* `pos` (string, recommended)

  * Coarse part-of-speech; suggested values:

    * `"NOUN"`, `"VERB"`, `"ADJ"`, `"ADV"`, `"PROPN"`, `"X"`.
  * For Wikidata-derived entries, this is mapped from `lexicalCategory`.

* `category` (string, optional but recommended)

  * Semantic category of the entry:

    * `"profession"`, `"nationality"`, `"title"`, `"honour"`, `"lexeme"`, etc.

* `human` (bool, optional)

  * Whether this lemma typically denotes humans.
  * Useful for pronoun choice, agreement rules, etc.

* `gender` (string, optional)

  * Coarse gender class where applicable:

    * e.g. `"masc"`, `"fem"`, `"common"`, `"none"`, `"unknown"`.
  * Interpretation is language-dependent and used mainly by morphology.

* `forms` (object, optional but recommended)

  * Key → surface form mapping.

  * Keys are language-specific feature bundles. Examples:

    Italian (profession):

    ```json
    "forms": {
      "masc_sg": "fisico",
      "fem_sg": "fisica",
      "masc_pl": "fisici",
      "fem_pl": "fisiche"
    }
    ```

    Turkish (no gender):

    ```json
    "forms": {
      "default": "fizikçi",
      "plural": "fizikçiler"
    }
    ```

    Japanese (no inflection):

    ```json
    "forms": {
      "default": "物理学者"
    }
    ```

  * At minimum, `"default"` is often used where no richer inflection is needed.

* `features` (object, optional)

  * Arbitrary additional data:

    * semantic domain, ISO / QID references, lexeme ID, etc.

  Examples:

  ```json
  "features": {
    "scientific_field": ["fisica"],
    "lexeme_id": "L12345"
  }
  ```

* `qid` (string or null, optional)

  * A representative Wikidata QID for this lemma, if known.
  * Example: `"Q169470"` for “physicist”.

## 6. Examples

### 6.1 Italian profession entry

```json
"professions": {
  "fisico": {
    "lemma": "fisico",
    "pos": "NOUN",
    "category": "profession",
    "human": true,
    "gender": "masc",
    "forms": {
      "masc_sg": "fisico",
      "fem_sg": "fisica",
      "masc_pl": "fisici",
      "fem_pl": "fisiche"
    },
    "features": {
      "scientific_field": ["fisica"]
    },
    "qid": "Q169470"
  }
}
```

### 6.2 Turkish nationality entry

```json
"nationalities": {
  "turk": {
    "lemma": "Türk",
    "pos": "ADJ",
    "category": "nationality",
    "human": true,
    "gender": "none",
    "forms": {
      "default": "Türk",
      "plural": "Türkler"
    },
    "features": {
      "country_qid": "Q43"
    },
    "qid": "QTODO_TURK"
  }
}
```

### 6.3 Japanese profession entry (no inflection)

```json
"professions": {
  "物理学者": {
    "lemma": "物理学者",
    "pos": "NOUN",
    "category": "profession",
    "human": true,
    "gender": "none",
    "forms": {
      "default": "物理学者"
    },
    "features": {
      "scientific_field": ["物理学"]
    },
    "qid": "Q169470"
  }
}
```

### 6.4 Wikidata-derived generic entry

When building from a lexeme dump via `utils/build_lexicon_from_wikidata.py`:

```json
"lemmas": {
  "autore": {
    "lemma": "autore",
    "pos": "NOUN",
    "category": "lexeme",
    "human": false,
    "gender": "none",
    "forms": {
      "default": "autore"
    },
    "features": {
      "lexeme_id": "L10"
    },
    "qid": "Q1"
  }
}
```

## 7. Validation rules

`lexicon/schema.py` implements the validator used by:

* `qa_tools/lexicon_smoke_tests.py`
* other QA scripts.

The validator enforces:

1. Top-level is an object.
2. `meta` / `_meta` is an object (if present).
3. Lemma-bearing sections (`lemmas`, `entries`, `professions`, etc.):

   * must be objects,
   * lemma keys must be strings,
   * entry values must be objects.
4. If a section is expected to have POS (e.g. `entries`, `lemmas`, `professions`, `nationalities`),

   * `pos` should be present and a string (warnings if missing, error if wrong type).
5. `schema_version` (if present) must be an integer and is compared to the internal `SCHEMA_VERSION`.

Warnings are allowed for:

* missing `meta`,
* missing `language`,
* missing `schema_version`,
* unknown lemma sections.

Errors cause `qa_tools/lexicon_smoke_tests.py` to fail.



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

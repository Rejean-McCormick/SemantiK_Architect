# Lexicon Architecture & Workflow

## 1\. Strategy: Source vs. Usage

We distinguish between where data comes from (Source) and how it is organized for the application (Usage).

  * **Upstream Source:** **Wikidata**.

      * We treat Wikidata as the raw material. [cite_start]All lexical entries should ideally link back to a Wikidata QID (e.g., `Q142` for France) to maintain verifiable data lineage[cite: 302, 536, 557].
      * [cite_start]Raw dumps or temporary processing files belong in `data/raw_wikidata/`, which is ignored by version control[cite: 805].

  * **Downstream Usage:** **Domain-Sharded JSON**.

      * Instead of monolithic files per language, we organize data by **semantic domain** (e.g., Science, People, Geography).
      * [cite_start]This allows the system to load only what is necessary, improves maintainability, and simplifies debugging[cite: 461, 805].

## 2\. Directory Structure

The legacy flat structure (e.g., `data/lexicon/en_lexicon.json`) is deprecated. The new standard uses a nested, language-specific folder structure.

```text
data/lexicon/
├── schema.json          # Master validation schema (Draft-07)
├── loader.py            # Runtime script: Merges domain files into one dict
├── en/                  # English Namespace
│   ├── core.json        # High-quality manual entries: verbs 'to be', pronouns
│   ├── people.json      # Biography: Professions, titles, family relations
│   ├── science.json     # Domain: Scientific fields, awards, terminology
│   └── geography.json   # Domain: Countries, cities, demonyms
├── fr/                  # French Namespace
│   ├── core.json
│   ├── people.json
│   └── ...
└── ...
```

[cite_start]This structure is supported by `data/lexicon/init.py`, which allows the directory to be treated as a package if needed[cite: 461, 462].

## 3\. Domain Definitions

We organize files based on the *topic* of the content to facilitate modular loading.

  * **`core.json`**: The grammatical "skeleton" of the language.

      * [cite_start]*Contents:* Copulas (to be), auxiliary verbs, articles, pronouns, and basic high-frequency nouns (person, man, woman)[cite: 254, 267].
      * *Maintenance:* High - likely manual curation.

  * **`people.json`**: Entities and predicates for biographical generation.

      * [cite_start]*Contents:* Professions (Physicist, Writer), Titles (King, President), relationships, and human-centric verbs (born, died)[cite: 294, 296, 304].
      * *Source:* Often semi-automated imports from Wikidata.

  * **`science.json`**: Specialized vocabulary for scientific biographies.

      * [cite_start]*Contents:* Fields of study (Physics, Chemistry), awards (Nobel Prize), and specific verbs (discover, publish)[cite: 316, 320, 326].

  * **`geography.json`**: Location data.

      * [cite_start]*Contents:* Countries, cities, and their associated adjectival/demonym forms (e.g., "France" $\to$ "French")[cite: 298, 299].

## 4\. The Schema (Simplified)

[cite_start]Every entry in the lexicon files must adhere to the schema defined in `data/lexicon_schema.json`[cite: 38].

### Base Entry Structure

```json
"physicist": {
  [cite_start]"pos": "NOUN",            // Part of Speech: NOUN, VERB, ADJ [cite: 46]
  [cite_start]"gender": "m",            // Grammatical Gender (m, f, n, common) [cite: 48]
  [cite_start]"human": true,            // Semantic tag for "Who" vs "What" [cite: 48]
  [cite_start]"qid": "Q169470",         // Link to Wikidata [cite: 51]
  [cite_start]"forms": {                // Explicit overrides for irregulars [cite: 44]
    "pl": "physicists"
  }
}
```

### Key Schema Types

  * [cite_start]**Professions:** Inherit from Base Entry but are specifically tagged for professional roles[cite: 52].
  * [cite_start]**Nationalities:** Include specific fields for `adjective` (e.g., "Polish"), `demonym` (noun for the person), and `country_name`[cite: 53, 54].
  * [cite_start]**Titles:** Include positioning logic (e.g., `pre_name` for "Dr.", `post_name` for "PhD")[cite: 56, 57].

## 5\. Workflow: Adding a New Word

### Step 1: Identify Domain

  * Is it a functional word like "is" or "the"? $\to$ `core.json`
  * Is it a job title like "Senator"? $\to$ `people.json`
  * Is it a chemical element or scientific theory? $\to$ `science.json`

### Step 2: Extract from Wikidata

Use the QID to find the target language label.

  * [cite_start]*Example:* `Q169470` $\to$ "physicien" (French)[cite: 391].

### Step 3: Define Morphology

Add necessary properties based on the language family's Grammar Matrix.

  * [cite_start]**Romance:** Define `gender` (m/f)[cite: 772].
  * [cite_start]**Slavic:** Define stem or case endings if irregular[cite: 791].
  * [cite_start]**Agglutinative:** Ensure vowel harmony rules can apply (e.g., front/back vowels)[cite: 692].

### Step 4: Validate

Run the validation script to ensure the JSON adheres to `lexicon_schema.json` and that the word inflects correctly in a generated test sentence.


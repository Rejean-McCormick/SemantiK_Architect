# Developer Guide: Adding a New Language

This guide documents the standard workflow for adding support for a new language (e.g., `pt` for Portuguese or `ko` for Korean) to the Abstract Wiki Architect.

## Prerequisite Checklist

1.  **ISO Code:** Identify the 2-letter ISO 639-1 code (e.g., `pt`, `ko`, `fi`).
2.  **Language Family:** Determine if the language fits an existing family matrix (Romance, Germanic, Slavic, Agglutinative) or requires a new one.

-----

## Step 1: Create the Lexicon Structure

The lexicon is no longer a single file. You must create a namespace folder for your language.

**Action:** Create directory `data/lexicon/{lang_code}/`.

**Required Files:**
At a minimum, you must create the following JSON files in that directory:

### 1\. `core.json`

Contains essential grammar function words.

```json
{
  "verb_be": {
    "pos": "VERB",
    "lemma": "ser",
    "forms": { "pres_3sg": "é", "past_3sg": "foi" }
  },
  "art_indef_m": { "pos": "ART", "lemma": "um" }
}
```

### 2\. `geography.json`

Contains the country name and nationality adjective for the language itself (to allow "X is a Portuguese physicist").

```json
{
  "portugal": { "pos": "NOUN", "gender": "m", "qid": "Q45" },
  "portuguese": { 
    "pos": "ADJ", 
    "forms": { "m": "português", "f": "portuguesa" },
    "qid": "Q17413" 
  }
}
```

*Note: You can add `people.json` and `science.json` later as you expand vocabulary.*

-----

## Step 2: Configure Morphology

### Scenario A: Language fits an existing Family (e.g., Portuguese $\to$ Romance)

If the language belongs to a supported family (Romance, Germanic, Slavic, Agglutinative), you only need a configuration file.

**Action:** Create `data/{family}/{lang_code}.json`.

**Example (`data/romance/pt.json`):**

```json
{
  "meta": { "family": "romance", "code": "pt" },
  "articles": {
    "m": { "default": "um" },
    "f": { "default": "uma" }
  },
  "morphology": {
    "suffixes": [
      { "ends_with": "or", "replace_with": "ora" },
      { "ends_with": "o", "replace_with": "a" }
    ]
  },
  "structure": "{name} é {article} {profession} {nationality}."
}
```

### Scenario B: Language requires a NEW Family Matrix

If the language structure is fundamentally different (e.g., adding Klingon or a specialized Polysynthetic language not covered by existing matrices).

1.  **Create Matrix:** `data/morphology_configs/klingon_matrix.json`.
2.  **Define Rules:** Define the specific inflection logic (e.g., prefixes, vowel harmony groups) in the matrix.

-----

## Step 3: Register in the Engine

The system uses a **MorphologyFactory** to instantiate the correct processor.

**Location:** `architect_engine/morphology/factory.py` (or equivalent registry).

### For Standard Languages (Scenario A)

**No code changes are usually required.** The `MorphologyFactory` automatically scans the `data/` directories. If it finds `data/romance/pt.json`, it knows to instantiate the `RomanceMorphology` class with the Portuguese configuration.

### For Custom Logic (Scenario B or Complex Cases)

If your language requires logic that JSON configuration cannot capture (e.g., complex Sandhi rules in Sanskrit or specific particle attachment order in Japanese), you must create a custom class.

1.  **Create Class:**

    ```python
    # architect_engine/morphology/custom/portuguese.py
    from ..romance import RomanceMorphology

    class PortugueseMorphology(RomanceMorphology):
        def apply_sandhi(self, word, next_word):
            # Custom logic to handle "de" + "o" -> "do"
            if word == "de" and next_word == "o":
                return "do"
            return f"{word} {next_word}"
    ```

2.  **Register:** Update the Factory to map `'pt'` to `PortugueseMorphology`.

-----

## Step 4: Validation & Testing

### 1\. Validate JSON Schemas

Run the schema validator to ensure your new lexicon files match `data/lexicon_schema.json`.

```bash
python scripts/validate_lexicon.py --lang=pt
```

### 2\. Generate a Test Sentence

Use the CLI or API to generate a bio frame to verify the pipeline.

```bash
# Using the CLI tool
python main.py generate --lang=pt --name="Marie Curie" --prof="physicist" --nat="polish"
```

**Expected Output:**

> "Marie Curie é uma física polonesa."

### 3\. Add Regression Test

Add a test case to `tests/test_generation.py` to prevent future regressions.

```python
def test_portuguese_generation():
    result = generate_bio("Marie Curie", "physicist", "polish", lang="pt")
    assert result == "Marie Curie é uma física polonesa."
```

-----

## Summary of Files to Add

| File Path | Purpose |
| :--- | :--- |
| `data/lexicon/{lang}/core.json` | Basic vocabulary. |
| `data/lexicon/{lang}/geography.json` | Country/Nationality data. |
| `data/{family}/{lang}.json` | Grammar configuration and sentence template. |
| `tests/test_{lang}.py` | (Optional) Specific unit tests. |
Contributing to Abstract Wiki Architect

Welcome! This project aims to support 300+ languages for Abstract Wikipedia. We cannot do this alone.

Whether you are a Native Speaker (Non-Coder) or a Python Developer, there is a place for you here.

1. I am a Native Speaker (No Code Required)

Your goal is to add support for your language by creating a Language Card.

Step 1: Identify your Language Family

Check abstract-wiki-architect/router.py or ask in the project chat.

Romance: Italian, Spanish, French, Portuguese, Catalan, Galician...

Germanic: English, German, Dutch, Swedish, Danish...

Slavic: Russian, Polish, Czech, Ukrainian, Serbian...

Agglutinative: Turkish, Finnish, Hungarian, Estonian...

and 10+ others.

Step 2: Create the JSON Card

Navigate to data/{family}/.

Copy an existing file (e.g., if adding Catalan, copy es.json -> ca.json).

Open the file and modify the rules for your language.

Example: Editing Catalan (ca.json)

{
  "name": "Catalan",
  "articles": {
    "m": { "default": "un" },
    "f": { "default": "una" }
  },
  "morphology": {
    "suffixes": [
      { "ends_with": "dor", "replace_with": "dora" },  // Spanish style
      { "ends_with": "t", "replace_with": "da" }       // Catalan specific
    ]
  }
}


Step 3: Verify

Run the test generator to create a template for your language:

python qa_tools/test_suite_generator.py


This will create test_suite_ca.csv. Fill in the "Expected Output" column with correct sentences and verify.

2. I am a Python Developer

Your goal is to build Logic Engines or improve existing ones.

Adding a New Engine

If a language family (e.g., Celtic) is missing:

Create engines/celtic.py.

Implement the standard interface:

def render_bio(name, gender, prof_lemma, nat_lemma, config):
    # Implementation here
    return sentence


Register the engine in router.py:

LANGUAGE_FAMILY_MAP = {
    'cy': 'celtic',
    'ga': 'celtic',
    # ...
}


Improving Existing Engines

Performance: Engines must be pure Python (no heavy libraries like pandas or numpy in the runtime path).

Robustness: Use .get() for dictionary access to prevent crashes on partial configs.

3. Pull Request Process

Fork the repository.

Create a branch: git checkout -b add-catalan-support.

Add your files:

data/romance/ca.json

qa_tools/generated_datasets/test_suite_ca.csv (with filled expected outputs).

Run Tests: python qa_tools/universal_test_runner.py. Ensure all pass.

Submit PR.

4. Style Guide

JSON: Use 2 spaces for indentation. Ensure keys are lowercase snake_case.

Python: Follow PEP8.

Commit Messages: Use conventional commits (e.g., feat: add Catalan language card, fix: correct Italian s-impure logic).

Thank you for helping us build a multilingual future!
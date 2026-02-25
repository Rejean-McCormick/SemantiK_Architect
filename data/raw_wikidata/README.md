# data/raw_wikidata/

This directory is reserved for **local Wikidata / Lexeme dump files** used to
build or refresh the project lexica. These files are **not** meant to be
committed to version control (see `.gitignore` in this directory).

## What goes here?

Examples of files you might place here:

- `lexemes_dump.json.gz`  
  A filtered Wikidata Lexeme dump (e.g. only selected languages / domains).

- `entities_dump.json.gz`  
  A filtered dump of Q-items (e.g. people, countries) used to enrich lexicon
  entries with `qid`, `country_qid`, etc.

File names are not fixed; the build scripts in `utils/` should take the actual
paths as CLI arguments.

## How is this used?

Typical workflow:

1. Download or prepare a Wikidata / Lexeme dump.
2. Put the dump in this directory (or somewhere on disk).
3. Run the builder script, for example:

   ```bash
   python utils/build_lexicon_from_wikidata.py \
       --lang it \
       --dump data/raw_wikidata/lexemes_dump.json.gz \
       --out data/lexicon/it_lexicon.json
````

4. Run QA tools on the resulting lexicon:

   ```bash
   python qa_tools/lexicon_coverage_report.py
   ```

## Git policy

* Raw dumps can be **very large** and change often.
* They should **never** be committed to the repository.
* Only keep:

  * this `README.md`,
  * the `.gitignore` file,
  * very small synthetic fixtures if needed for tests.

If you need to share a specific dump configuration, document the download
command or filtering pipeline instead of the file itself.


This exhaustive inventory documents every executable script, tool, and test suite found in your codebase (v2.5).

---

# 📚 The Complete Tools & Tests Inventory (v2.5)

**Abstract Wiki Architect**

This document serves as the **Single Source of Truth** for:

1. **GUI Tools** (Web Dashboard)
2. **CLI Orchestration** (Backend Management)
3. **Specialized Debugging Tools** (Deep Dives)
4. **Data Operations** (Lexicon & Imports)
5. **Quality Assurance** (Testing & Validation)
6. **AI Services** (Agents)

---

## 1. 🕹️ Core Orchestration (The "God Mode")

These are your primary entry points for managing the entire system lifecycle.

| Command / Script | Location | Purpose | Key Arguments |
| --- | --- | --- | --- |
| **`manage.py`** | `Root` | **The Commander.** Unified CLI for starting, building, and cleaning the system. | `start`: Check env & launch API/Worker.<br>

<br>`build`: Compile grammar (`--clean`, `--parallel`).<br>

<br>`doctor`: Run diagnostics.<br>

<br>`clean`: Remove artifacts. |
| **`Run-Architect.ps1`** | `Root` | **Windows Launcher.** PowerShell wrapper that handles zombie process cleanup (Node/Python) and spawns the 3-window hybrid setup (API/Worker/Frontend). | *None (Run directly)* |
| **`Makefile`** | `Root` | **Legacy Build.** Make commands for compiling Tier 1 languages directly via `gf`. | `all`: Compiles 4 Tier-1 languages.<br>

<br>`clean`: Removes `.gfo` and `.pgf`. |
| **`StartWSL.bat`** | `Root` | **Quick Shell.** Launches a new PowerShell window pre-connected to WSL with the virtual environment activated. | *None* |

---

## 2. 🏭 The Build System (The Factory)

These scripts handle the complex logic of turning source code into the binary runtime.

| Tool | Location | Purpose | Key Arguments |
| --- | --- | --- | --- |
| **Orchestrator** | `builder/orchestrator.py` | **The Compiler.** Runs the **Two-Phase Build** (Verify → Link). It compiles individual languages to `.gfo` and links them into `AbstractWiki.pgf`. Triggers the **Factory** for missing Tier 3 languages. | *(None, config driven by `everything_matrix.json`)* |
| **Compiler** | `builder/compiler.py` | **Sandboxed Builder.** Low-level wrapper around the `gf` binary. Manages include paths and environment isolation. | *(Internal module)* |
| **Strategist** | `builder/strategist.py` | **The Planner.** Analyzes available RGL modules and decides which build strategy to use (GOLD, SILVER, BRONZE, IRON). Generates `build_plan.json`. | *(Internal module)* |
| **Forge** | `builder/forge.py` | **The Executor.** Reads the `build_plan.json` and physically writes the `Wiki*.gf` concrete files based on the chosen strategy. | *(Internal module)* |
| **Healer** | `builder/healer.py` | **The Medic.** Reads `build_failures.json` and dispatches the **AI Surgeon** to repair broken grammar files. | *(Internal module)* |

---

## 3. 🧠 The "Everything Matrix" (System Intelligence)

The central nervous system that scans your codebase to determine language health.

| Tool | Location | Purpose | Key Arguments |
| --- | --- | --- | --- |
| **Matrix Builder** | `tools/everything_matrix/build_index.py` | **The Census Taker.** Scans RGL, Lexicon, App, and QA layers to build `everything_matrix.json`. Calculates Maturity Scores (0-10) and Build Strategies. | `--force`: Ignore cache.<br>

<br>`--regen-[rgl/lex/app/qa]`: Force rescan of specific zones.<br>

<br>`--verbose`: Debug logs. |
| **RGL Scanner** | `tools/everything_matrix/rgl_scanner.py` | **Zone A Audit.** Scans `gf-rgl/src` to find which modules (Cat, Noun, Syntax) exist for each language. | `--write`: Save to disk.<br>

<br>`--output`: Custom path. |
| **Lexicon Scanner** | `tools/everything_matrix/lexicon_scanner.py` | **Zone B Audit.** Scans `data/lexicon/` to count Core/Domain words and calculate semantic coverage. | `--lex-root`: Custom path.<br>

<br>`--lang`: Scan single language. |
| **App Scanner** | `tools/everything_matrix/app_scanner.py` | **Zone C Audit.** Scans frontend profiles and assets to determine application readiness. | *(Internal/Library)* |
| **QA Scanner** | `tools/everything_matrix/qa_scanner.py` | **Zone D Audit.** Scans JUnit reports and PGF binaries to calculate pass rates and binary presence. | `--gf-root`: Custom path.<br>

<br>`--junit`: Custom XML path. |

---

## 4. 🚑 Maintenance & Diagnostics (Health)

Tools to keep the system clean and running smoothly.

| Tool | Location | Purpose | Key Arguments |
| --- | --- | --- | --- |
| **Language Health** | `tools/language_health.py` | **Deep Scan.** Replaces `audit_languages`. Compiles a specific language and runs a runtime API test against it. Generates `audit_report.json`. | `--mode [compile/api/both]`<br>

<br>`--langs [en fr]`<br>

<br>`--verbose`<br>

<br>`--fast`: Use cache. |
| **Diagnostic Audit** | `tools/diagnostic_audit.py` | **Forensics.** Detects "Zombie" files (leftover `.gf` files from failed builds) and suspicious content that might break compilation. | `--verbose`<br>

<br>`--json`: Machine readable output. |
| **Root Cleanup** | `tools/cleanup_root.py` | **Garbage Collector.** Moves stray `.gf/.pgf` files to the `gf/` folder and deletes temp files (`.tmp`, `.log`, `junit.xml`). | `--dry-run`: Preview only.<br>

<br>`--verbose`<br>

<br>`--json` |
| **Bootstrap Tier 1** | `tools/bootstrap_tier1.py` | **Initializer.** Creates the `Wiki*.gf` bridge files for Tier 1 languages, linking them to the RGL. | `--force`: Overwrite.<br>

<br>`--dry-run`<br>

<br>`--langs`: Filter list. |
| **Config Syncer** | `sync_config_from_gf.py` | **Data Sync.** Reads the compiled PGF and updates `language_profiles.json` with available languages. | *(None)* |

---

## 5. ⛏️ Data Operations (Lexicon & Mining)

Tools for ingesting, managing, and fixing vocabulary data.

| Tool | Location | Purpose | Key Arguments |
| --- | --- | --- | --- |
| **Universal Harvester** | `tools/harvest_lexicon.py` | **The Miner.** Fetches words from local **GF WordNet** files (`--source wordnet`) or **Wikidata** (`--source wikidata`) to populate `wide.json`. | `wordnet --root <path>`<br>

<br>`wikidata --input <qids.json>`<br>

<br>`--lang`: Target ISO code. |
| **Wikidata Importer** | `scripts/lexicon/wikidata_importer.py` | **The Linker.** Enriches existing lexicon files by looking up their lemmas on Wikidata and adding QIDs. | `--lang`: Target language.<br>

<br>`--domain`: Target shard.<br>

<br>`--apply`: Write changes. |
| **RGL Syncer** | `scripts/lexicon/sync_rgl.py` | **The Big Pull.** Extracts ALL lexical functions from the compiled PGF and dumps them into `data/lexicon/{lang}/rgl_sync.json`. | `--pgf`: Custom PGF path.<br>

<br>`--max-funs`: Limit count.<br>

<br>`--dry-run` |
| **Gap Filler** | `tools/lexicon/gap_filler.py` | **The Analyst.** Compares a target language (e.g., French) against a pivot language (English) to find missing vocabulary entries. | `--target`: Language code.<br>

<br>`--pivot`: Reference code (default: eng).<br>

<br>`--json-out`: Save report. |
| **Link Libraries** | `link_libraries.py` | **The Patcher.** Modifies `Wiki*.gf` files to ensure they `open` the `Dict` and `Symbolic` modules required for runtime lexicon injection. | *(None)* |

---

## 6. 🧪 Quality Assurance (Testing & Evaluation)

Tools to verify the linguistic output and system stability.

| Tool | Location | Purpose | Key Arguments |
| --- | --- | --- | --- |
| **Universal Test Runner** | `tools/qa/universal_test_runner.py` | **The Executor.** Runs CSV-based test suites (v2 & Legacy) against the engine using the **GF Grammar Engine Adapter**. | `--dataset-dir`: Folder with CSVs.<br>

<br>`--langs`: Filter.<br>

<br>`--fail-fast`<br>

<br>`--strict`: Fail on missing expected text. |
| **Bio Evaluator** | `tools/qa/eval_bios.py` | **Real-World QA.** Renders biographies for a sample of real humans (from local file or Wikidata) and checks coverage/quality. | `--source [local/wikidata]`<br>

<br>`--input`: JSON/CSV file.<br>

<br>`--langs`: Target languages. |
| **Lexicon Coverage** | `tools/qa/lexicon_coverage_report.py` | **Data Stats.** Generates detailed reports on lexicon size, collisions, and missing shards. | `--out`: Output JSON.<br>

<br>`--include-files`: Detailed breakdown.<br>

<br>`--fail-on-errors` |
| **Ambiguity Detector** | `tools/qa/ambiguity_detector.py` | **Linguistics QA.** Checks for "Ambiguity Traps" (sentences with >1 parse tree). Can generate candidates via AI or check specific sentences. | `--lang`: Target code.<br>

<br>`--sentence`: Custom input.<br>

<br>`--topic`: AI generation topic. |
| **Test Suite Gen** | `tools/qa/test_suite_generator.py` | **Template Maker.** Creates empty `test_suite_{lang}.csv` files for human linguists to fill with expected translations. | `--langs`: Target languages.<br>

<br>`--matrix`: Path to matrix config. |
| **Batch Generator** | `tools/qa/batch_test_generator.py` | **Bulk QA.** Programmatically generates large regression datasets for stress testing. | *(None)* |
| **Regression Gen** | `tools/qa/generate_lexicon_regression_tests.py` | **Snapshotter.** Generates a pytest module (`test_lexicon_regression.py`) that snapshots the current lexicon inventory to detect changes. | `--out`: Output file path.<br>

<br>`--langs`: Filter. |
| **Profiler** | `tools/health/profiler.py` | **Benchmarker.** Measures API latency (ms), throughput (TPS), and memory usage under load. | `--lang`: Target code.<br>

<br>`--iterations`: Request count.<br>

<br>`--update-baseline` |

---

## 7. 🤖 AI Services (The Staff)

Autonomous agents that perform complex tasks.

| Agent | File | Role | Triggered By |
| --- | --- | --- | --- |
| **The Architect** | `ai_services/architect.py` | **Grammar Generator.** Writes raw GF code for missing languages (Tier 3) based on topology constraints. | `manage.py generate` |
| **The Surgeon** | `ai_services/surgeon.py` | **Code Repair.** Analyzes compiler error logs and patches broken `.gf` files automatically. | `builder/healer.py` (Build failure) |
| **The Lexicographer** | `ai_services/lexicographer.py` | **Data Bootstrapper.** Generates `core.json` files for empty languages by translating basic concepts. | CLI or Missing Data Event |
| **The Judge** | `ai_services/judge.py` | **QA Evaluator.** Grades generated text against Gold Standards. Auto-files GitHub issues for regressions. | `tests/integration/test_quality.py` |
| **AI Refiner** | `tools/ai_refiner.py` | **Upgrader.** Takes a "Pidgin" grammar and upgrades it to a proper RGL implementation using LLM reasoning. | CLI Tool |

---

## 8. 🧪 Test Suites (Pytest)

The automated regression harness. Run with `pytest <path>`.

| Category | File | Description |
| --- | --- | --- |
| **Integration** | `tests/integration/test_quality.py` | **The Judge.** Runs Gold Standard regression tests using the AI Judge. |
| **Integration** | `tests/integration/test_worker_flow.py` | **Async.** Verifies the Redis job queue and worker compilation logic. |
| **Integration** | `tests/integration/test_ninai.py` | **Protocol.** Tests the Ninai JSON Adapter parsing logic. |
| **Smoke** | `tests/test_api_smoke.py` | **HTTP.** Checks `/health` and `/generate` endpoints. |
| **Smoke** | `tests/test_gf_dynamic.py` | **Engine.** Verifies binary loading and linearization. |
| **Smoke** | `tests/test_lexicon_smoke.py` | **Data.** Validates JSON schema of all lexicon files. |
| **Lexicon** | `tests/test_lexicon_loader.py` | **IO.** Tests lazy-loading of lexicon shards. |
| **Lexicon** | `tests/test_lexicon_index.py` | **Search.** Tests in-memory indexing and lookups. |
| **Lexicon** | `tests/test_lexicon_wikidata_bridge.py` | **ETL.** Tests Wikidata QID extraction logic. |
| **Frames** | `tests/test_frames_*.py` | **Semantics.** Unit tests for all Semantic Frame dataclasses (Entity, Event, Narrative, Relational, Meta). |
| **API** | `tests/http_api/test_generate.py` | **Endpoints.** Tests `POST /generate` with various payloads. |
| **API** | `tests/http_api/test_ai.py` | **Endpoints.** Tests AI suggestion endpoints. |
| **Core** | `tests/core/test_use_cases.py` | **Logic.** Tests domain use cases (GenerateText, BuildLanguage). |
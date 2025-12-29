Yes, I am **100% aligned** with that file listing.

I have updated the **Tools & Tests Inventory (v2.1)** below to explicitly include the **additional utilities and QA tools** found in your specific file dump (e.g., `universal_test_runner.py`, `dump_lexicon_stats.py`, `seed_lexicon_ai.py`) that were missing from the previous version.

---

# 🛠️ Tools & Tests Inventory (v2.1)

**Abstract Wiki Architect**

This document acts as the definitive registry for all executable scripts, maintenance tools, and automated tests in the system. It maps each file to its physical location and explains its specific usage.

---

## 1. 🕹️ Core Orchestration (The "Command Center")

These are the primary entry points for developers. You should rarely need to run anything else manually.

| Tool File | Usage | Description |
| --- | --- | --- |
| **`Run-Architect.ps1`** | `.\Run-Architect.ps1` | **The "God Mode" Launcher.** Kills zombie processes, checks Docker, and spawns visible windows for API, Worker, and Frontend. |
| **`manage.py`** | `python manage.py start` | **The Backend Commander.** Unified CLI for building, cleaning, and starting backend services. Wraps all other tools. |

---

## 2. 🏭 The Build System ("The Factory")

Tools responsible for compiling the Grammatical Framework (GF) code and constructing the runtime binary.

| Tool File | Location | Usage | Description |
| --- | --- | --- | --- |
| **`build_orchestrator.py`** | `gf/` | `manage.py build` | **The Compiler.** Runs the Two-Phase Build (Verify -> Link) to create `AbstractWiki.pgf`. |
| **`grammar_factory.py`** | `utils/` | *Imported Lib* | **The Logic Engine.** Implements Weighted Topology to generate Tier 3 grammars (SVO/SOV) dynamically. |
| **`generate_path_map.py`** | `root` | `python generate_path_map.py` | **The Mapper.** Generates `rgl_paths.json` by finding where RGL modules live on disk. |

---

## 3. 🧠 The "Everything Matrix" Suite

These scripts run automatically to generate the `everything_matrix.json` registry. They provide the "Self-Awareness" of the system.

| Tool File | Location | Usage | Description |
| --- | --- | --- | --- |
| **`build_index.py`** | `tools/everything_matrix/` | `manage.py build` | **The Master Scanner.** Orchestrates all sub-scanners and writes the final JSON registry. |
| **`rgl_auditor.py`** | `tools/everything_matrix/` | *Internal* | **Zone A Auditor.** physically checks `gf-rgl` for valid grammar modules. |
| **`lexicon_scanner.py`** | `tools/everything_matrix/` | *Internal* | **Zone B Auditor.** Counts vocabulary size in `data/lexicon/` to score maturity. |
| **`qa_scanner.py`** | `tools/everything_matrix/` | *Internal* | **Zone D Auditor.** Parses `pytest` logs to update quality scores. |
| **`app_scanner.py`** | `tools/everything_matrix/` | *Internal* | **Zone C Auditor.** Checks frontend assets and backend routes for language support. |

---

## 4. 🛠️ General System Tools (Maintenance)

Ad-hoc utilities for cleaning, fixing, and diagnosing the system.

| Tool File | Location | Usage | Description |
| --- | --- | --- | --- |
| **`audit_languages.py`** | `tools/` | `python tools/audit_languages.py` | **Health Check.** Rapidly scans all languages to report which are Valid, Broken, or Skipped. |
| **`check_all_languages.py`** | `tools/` | `python tools/check_all_languages.py` | **Deep Verification.** Sends a test payload to the API for every language to verify runtime generation. |
| **`diagnostic_audit.py`** | `tools/` | `python tools/diagnostic_audit.py` | **Forensics.** Finds "Zombie" files (old builds) that might be breaking the compiler. |
| **`cleanup_root.py`** | `tools/` | `python tools/cleanup_root.py` | **Janitor.** Deletes temporary `.gfo` files and moves source files to `gf/`. |
| **`bootstrap_tier1.py`** | `tools/` | `python tools/bootstrap_tier1.py` | **Initializer.** Bootstraps the `Wiki*.gf` files for all RGL (Tier 1) languages. |
| **`ai_refiner.py`** | `tools/` | `python tools/ai_refiner.py` | **The Upgrade Tool.** Uses AI to upgrade a "Pidgin" grammar to a full recursive grammar. |
| **`config_extractor.py`** | `tools/` | `python tools/config_extractor.py` | **Exporter.** Extracts configuration chunks for Wikifunctions deployment. |

---

## 5. ⛏️ Data Ingestion ("The Refinery")

Tools for mining vocabulary, importing data, and managing the lexicon.

| Tool File | Location | Usage | Description |
| --- | --- | --- | --- |
| **`build_lexicon_from_wikidata.py`** | `tools/` | `python tools/build_...py` | **The Miner.** Fetches QIDs (e.g., Planets, Professions) from Wikidata and saves JSON shards. |
| **`harvest_lexicon.py`** | `tools/` | `python tools/harvest_lexicon.py` | **The Harvester.** Advanced tool for mining local `gf-wordnet` or Wikidata with fine-grained control. |
| **`seed_lexicon_ai.py`** | `utils/` | `python utils/seed_lexicon_ai.py` | **The Seeder.** Uses AI to generate initial `core.json` vocabulary lists for new languages. |
| **`dump_lexicon_stats.py`** | `utils/` | `python utils/dump_...py` | **The Analyst.** Outputs raw statistics about lexicon coverage and size. |
| **`migrate_lexicon_schema.py`** | `utils/` | `python utils/migrate...` | **The Migrator.** Upgrades old JSON lexicon files to the v2.1 schema. |
| **`refresh_lexicon_index.py`** | `utils/` | `python utils/refresh...` | **The Indexer.** Rebuilds the fast lookup index for the API. |

---

## 6. 🧪 QA & Testing Suite

Tools for validating quality and correctness.

| File Type | Location | Usage | Description |
| --- | --- | --- | --- |
| **Simple Runner** | `tools/qa/test_runner.py` | `python tools/qa/test_runner.py` | **CSV Runner (Simple).** Executes basic "BioFrame" tests from `test_suite_*.csv`. |
| **Universal Runner** | `tools/qa/universal_test_runner.py` | `python tools/qa/universal...` | **CSV Runner (Advanced).** Supports complex construction testing beyond simple bios. |
| **Suite Generator** | `tools/qa/test_suite_generator.py` | `python tools/qa/test_...` | **Template Factory.** Creates empty CSV test files for humans or AI to fill. |
| **Batch Generator** | `tools/qa/batch_test_generator.py` | `python tools/qa/batch...` | **Bulk Factory.** Generates large-scale test datasets for regression testing. |
| **Bio Evaluator** | `tools/qa/eval_bios.py` | `python tools/qa/eval_bios.py` | **Bio QA.** Compares generated biographies against Wikidata facts. |
| **Coverage Report** | `tools/qa/lexicon_coverage_report.py` | `python tools/qa/lexicon...` | **Metrics.** Generates a report on how much of the intended lexicon is actually implemented. |
| **Smoke Tests** | `tests/test_lexicon_smoke.py` | `pytest tests/test_lexicon_smoke.py` | **Data Validation.** Checks if lexicon files are syntactically valid and structure is sound. |

### 🧩 Automated Unit Tests (`pytest`)

The system uses a modular testing strategy split across the `tests/` directory.

#### 📂 Domain Logic

| Category | Location | Description |
| --- | --- | --- |
| **Core Logic** | `tests/core/` | Tests pure business logic, domain models, and abstract use cases. |
| **API Adapters** | `tests/adapters/` | Verifies external interfaces, specifically Wikidata connectivity and endpoints. |
| **HTTP Layer** | `tests/http_api/` | Tests the FastAPI controllers, routes, and JSON response payloads. |
| **Integration** | `tests/integration/` | End-to-End tests validating full workflows, including NiNai and Worker queues. |

#### 📂 Engine & Data

| Category | File Pattern | Description |
| --- | --- | --- |
| **Frames** | `tests/test_frames_*.py` | Validation for semantic frame logic (Entity, Event, Meta, Narrative, Relational). |
| **Lexicon** | `tests/test_lexicon_*.py` | Tests for the dictionary loader, indexer, and Wikidata bridge components. |
| **GF Engine** | `tests/test_gf_dynamic.py` | Validates the dynamic loading and linearization of GF grammars. |
| **API Smoke** | `tests/test_api_smoke.py` | Lightweight checks to ensure the API starts and responds to basic pings. |
| **Generation** | `tests/test_multilingual_generation.py` | Verifies the system can generate text across multiple languages simultaneously. |

---

## 7. 🤖 AI Services ("The Staff")

Autonomous agents that act as specialized workers.

| Agent | Location | Trigger | Role |
| --- | --- | --- | --- |
| **Architect** | `ai_services/architect.py` | `manage.py generate` | **The Builder.** Writes new GF code for missing languages. |
| **Surgeon** | `ai_services/surgeon.py` | *Build Failure* | **The Fixer.** Patches broken code based on compiler error logs. |
| **Lexicographer** | `ai_services/lexicographer.py` | *Missing Data* | **The Dictionary Maker.** Generates `core.json` for empty languages. |
| **Judge** | `ai_services/judge.py` | *QA Pipeline* | **The Critic.** Evaluates output quality against Gold Standards. |
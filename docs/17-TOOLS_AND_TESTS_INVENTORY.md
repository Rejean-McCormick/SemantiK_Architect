# 📚 The Complete Tools & Tests Inventory (v2.5.1)

**SemantiK Architect**

This document serves as the **Single Source of Truth** for:

1. **GUI Tools** (Web Dashboard)
2. **CLI Orchestration** (Backend Management)
3. **Specialized Debugging Tools** (Deep Dives)
4. **Data Operations** (Lexicon & Imports)
5. **Quality Assurance** (Testing & Validation)
6. **AI Services** (Agents)

---

## 1. 🕹️ Core Orchestration

Primary entry points for managing the overall system lifecycle.

| Command / Script        | Location | Purpose                                                                                          | Key Arguments                                                                                                                                                           |
| ----------------------- | -------- | ------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`manage.py`**         | `Root`   | Unified CLI for starting, building, and cleaning the system.                                     | `start`: Launch API/Worker (checks env).<br><br>`build`: Compile grammar (`--clean`, `--parallel`).<br><br>`doctor`: Run diagnostics.<br><br>`clean`: Remove artifacts. |
| **`Run-Architect.ps1`** | `Root`   | Windows launcher that handles process cleanup and spawns the hybrid setup (API/Worker/Frontend). | *(None; run directly)*                                                                                                                                                  |
| **`Makefile`**          | `Root`   | Legacy build shortcuts for compiling Tier 1 languages directly via `gf`.                         | `all`, `clean`                                                                                                                                                          |
| **`StartWSL.bat`**      | `Root`   | Quick shell launcher into WSL with venv activated.                                               | *(None)*                                                                                                                                                                |

---

## 2. 🏭 The Build System

Scripts that turn source grammars into the runtime PGF.

| Tool                    | Location                  | Purpose                                                                                                                                            | Key Arguments                                                                                                                                                                   |
| ----------------------- | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Orchestrator**        | `builder/orchestrator/`   | Canonical two-phase build (Verify → Link). Compiles `.gfo` and links into `AbstractWiki.pgf`. Supports SAFE_MODE generation for missing languages. | CLI: `python -m builder.orchestrator` supports `--strategy`, `--langs`, `--clean`, `--verbose`, `--max-workers`, `--no-preflight`, `--regen-safe` (and matrix-driven defaults). |
| **Orchestrator (Shim)** | `builder/orchestrator.py` | Backwards-compatible wrapper that delegates to the package entrypoint (kept for legacy callers/tools).                                             | *(Same as package CLI; delegates to `python -m builder.orchestrator`)*                                                                                                          |
| **Compiler**            | `builder/compiler.py`     | Low-level wrapper around `gf`. Manages include paths and environment isolation.                                                                    | *(Internal module)*                                                                                                                                                             |
| **Strategist**          | `builder/strategist.py`   | Chooses build strategy (GOLD/SILVER/BRONZE/IRON) and writes build plan.                                                                            | *(Internal module)*                                                                                                                                                             |
| **Forge**               | `builder/forge.py`        | Writes `Wiki*.gf` concrete files according to build plan.                                                                                          | *(Internal module)*                                                                                                                                                             |
| **Healer**              | `builder/healer.py`       | Reads build failures and dispatches AI repair for broken grammars.                                                                                 | *(Internal module)*                                                                                                                                                             |

---

## 3. 🧠 The Everything Matrix

System intelligence layer that scans repo state and language readiness.

| Tool                | Location                                     | Purpose                                                                                                                  | Key Arguments                                                                                                  |
| ------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| **Matrix Builder**  | `tools/everything_matrix/build_index.py`     | Scans RGL, Lexicon, App, and QA layers to build `everything_matrix.json`. Computes maturity scores and build strategies. | `--out` (path), `--langs …`, `--force`, `--regen-rgl`, `--regen-lex`, `--regen-app`, `--regen-qa`, `--verbose` |
| **RGL Scanner**     | `tools/everything_matrix/rgl_scanner.py`     | Audits `gf-rgl/src` module presence/consistency (outputs JSON).                                                          | *(scanner-specific; used by build_index)*                                                                      |
| **Lexicon Scanner** | `tools/everything_matrix/lexicon_scanner.py` | Scores lexicon maturity by scanning shard coverage (outputs JSON).                                                       | *(scanner-specific; used by build_index)*                                                                      |
| **App Scanner**     | `tools/everything_matrix/app_scanner.py`     | Scans frontend/backend surfaces for language support signals (outputs JSON).                                             | *(scanner-specific; used by build_index)*                                                                      |
| **QA Scanner**      | `tools/everything_matrix/qa_scanner.py`      | Parses QA artifacts/logs to update quality scoring (outputs JSON).                                                       | *(scanner-specific; used by build_index)*                                                                      |

---

## 4. 🚑 Maintenance & Diagnostics

Tools used to keep the repo sane and the system healthy.

> **Note (GUI Tools):** The Tools Dashboard runs via a strict backend allowlist. The “Key Arguments” below reflect the allowlisted argv flags for GUI execution.
> **Security:** Do **not** pass secrets via argv. Tool args can be echoed into logs/telemetry/UI/debug bundles. For API-mode checks, provide the API key via environment/secret injection (recommended: `ARCHITECT_API_KEY`; fallbacks: `AWA_API_KEY`, `API_SECRET`, `API_KEY`).

| Tool                 | Location                    | Purpose                                                                    | Key Arguments                                                                                                                    |
| -------------------- | --------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **Language Health**  | `tools/language_health.py`  | Deep scan utility for the language pipeline.                               | `--mode`, `--fast`, `--parallel`, `--api-url`, `--timeout`, `--limit`, `--langs …`, `--no-disable-script`, `--verbose`, `--json` |
| **Diagnostic Audit** | `tools/diagnostic_audit.py` | Forensics audit for stale artifacts and inconsistent outputs.              | `--verbose`, `--json`                                                                                                            |
| **Root Cleanup**     | `tools/cleanup_root.py`     | Moves loose artifacts into expected folders and cleans known junk outputs. | `--dry-run`, `--verbose`, `--json`                                                                                               |
| **Bootstrap Tier 1** | `tools/bootstrap_tier1.py`  | Scaffolds Tier 1 wrappers / bridge files for selected languages.           | `--langs …`, `--force`, `--dry-run`, `--verbose`                                                                                 |

---

## 5. ⛏️ Data Operations

Lexicon mining/harvesting and related vocabulary maintenance.

| Tool                                     | Location                               | Purpose                                                                                                                                                                               | Key Arguments                                                                                                                                                                                  |
| ---------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Universal Lexicon Harvester**          | `tools/harvest_lexicon.py`             | **Two-mode harvester (subcommands)** for lexicon data. WordNet mode builds `wide.json`. Wikidata mode fetches labels + limited facts for provided QIDs and saves a domain shard JSON. | **`wordnet`**: `wordnet --root <gf-wordnet> --lang <iso2> [--out <data/lexicon>]`<br><br>**`wikidata`**: `wikidata --lang <iso2> --input <qids.json> [--domain people] [--out <data/lexicon>]` |
| **Wikidata Importer (Legacy/Reference)** | `scripts/lexicon/wikidata_importer.py` | Legacy/reference importer logic; not wired into v2.5 tools runner allowlist.                                                                                                          | *(varies; not authoritative in v2.5 runtime)*                                                                                                                                                  |
| **RGL Syncer**                           | `scripts/lexicon/sync_rgl.py`          | Extracts lexical functions from compiled PGF into `data/lexicon/{lang}/rgl_sync.json`.                                                                                                | `--pgf`, `--out-dir`, `--langs`, `--max-funs`, `--dry-run`, `--validate`                                                                                                                       |
| **Gap Filler**                           | `tools/lexicon/gap_filler.py`          | Compares target language lexicon vs pivot language to find missing concepts.                                                                                                          | `--target`, `--pivot`, `--data-dir`, `--json-out`, `--verbose`                                                                                                                                 |
| **Link Libraries**                       | `link_libraries.py`                    | Ensures `Wiki*.gf` opens required modules for runtime lexicon injection.                                                                                                              | *(None)*                                                                                                                                                                                       |
| **Schema/Index Utilities**               | `utils/…`                              | Maintenance utilities for lexicon index/schema and stats.                                                                                                                             | `utils/refresh_lexicon_index.py`, `utils/migrate_lexicon_schema.py`, `utils/dump_lexicon_stats.py`                                                                                             |

---

## 6. 🧪 Quality Assurance

QA tools that validate runtime output, lexicon integrity, and regression coverage.

| Tool                                  | Location                                        | Purpose                                                                         | Key Arguments                                                                              |
| ------------------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| **Universal Test Runner**             | `tools/qa/universal_test_runner.py`             | Runs CSV-based suites and emits a report.                                       | `--suite`, `--in`, `--out`, `--langs …`, `--limit`, `--verbose`, `--fail-fast`, `--strict` |
| **Bio Evaluator**                     | `tools/qa/eval_bios.py`                         | Compares generated biographies against Wikidata facts (QA harness).             | `--langs …`, `--limit`, `--out`, `--verbose`                                               |
| **Lexicon Coverage Report**           | `tools/qa/lexicon_coverage_report.py`           | Coverage report for intended vs implemented lexicon and errors.                 | `--langs …`, `--out`, `--format`, `--verbose`, `--fail-on-errors`                          |
| **Ambiguity Detector**                | `tools/qa/ambiguity_detector.py`                | Generates/uses curated ambiguous sentences and checks for multiple parse trees. | `--lang`, `--sentence`, `--topic`, `--json-out`, `--verbose`                               |
| **Batch Test Generator**              | `tools/qa/batch_test_generator.py`              | Generates large regression datasets (CSV) for QA.                               | `--langs …`, `--out`, `--limit`, `--seed`, `--verbose`                                     |
| **Test Suite Generator**              | `tools/qa/test_suite_generator.py`              | Generates empty CSV templates for manual fill-in.                               | `--langs …`, `--out`, `--verbose`                                                          |
| **Lexicon Regression Test Generator** | `tools/qa/generate_lexicon_regression_tests.py` | Builds regression tests from lexicon inventory for CI.                          | `--langs …`, `--out`, `--limit`, `--verbose`, `--lexicon-dir`                              |
| **Profiler**                          | `tools/health/profiler.py`                      | Benchmarks Grammar Engine performance.                                          | `--lang`, `--iterations`, `--update-baseline`, `--threshold`, `--verbose`                  |
| **AST Visualizer**                    | `tools/debug/visualize_ast.py`                  | Generates JSON AST from sentence/intent or explicit AST.                        | `--lang`, `--sentence`, `--ast`, `--pgf`                                                   |

---

## 7. 🤖 AI Services

Autonomous agents and AI-gated tools.

| Agent / Tool          | File                           | Role                                                                 | Triggered By                        |
| --------------------- | ------------------------------ | -------------------------------------------------------------------- | ----------------------------------- |
| **The Architect**     | `ai_services/architect.py`     | Generates missing grammars (Tier 3) based on topology constraints.   | Build/CLI workflow                  |
| **The Surgeon**       | `ai_services/surgeon.py`       | Repairs broken `.gf` files using compiler logs.                      | `builder/healer.py`                 |
| **The Lexicographer** | `ai_services/lexicographer.py` | Bootstraps core vocabulary for empty languages.                      | CLI / missing-data workflows        |
| **The Judge**         | `ai_services/judge.py`         | Grades generated text against gold standards; regression evaluation. | `tests/integration/test_quality.py` |
| **AI Refiner**        | `tools/ai_refiner.py`          | Upgrades “Pidgin” grammars toward RGL compliance.                    | Tools runner (AI-gated)             |
| **Seed Lexicon (AI)** | `utils/seed_lexicon_ai.py`     | Generates seed lexicon for selected languages.                       | Tools runner (AI-gated)             |

**AI gating:** backend enforces `ARCHITECT_ENABLE_AI_TOOLS=1` for AI-gated tool IDs.

---

## 8. 🧪 Test Suites (Pytest)

Automated regression harness. Run with `pytest <path>`.

| Category        | File                                    | Description                                             |
| --------------- | --------------------------------------- | ------------------------------------------------------- |
| **Integration** | `tests/integration/test_quality.py`     | Judge-based regression checks (AI Judge integration).   |
| **Integration** | `tests/integration/test_worker_flow.py` | Verifies worker compilation/job flow.                   |
| **Integration** | `tests/integration/test_ninai.py`       | Tests Ninai adapter parsing logic.                      |
| **Smoke**       | `tests/test_api_smoke.py`               | Checks `/health` and `/generate` endpoints.             |
| **Smoke**       | `tests/test_gf_dynamic.py`              | Validates dynamic loading/linearization of GF grammars. |
| **Smoke**       | `tests/test_lexicon_smoke.py`           | Validates lexicon JSON schema/syntax.                   |
| **Lexicon**     | `tests/test_lexicon_loader.py`          | Tests lazy-loading of lexicon shards.                   |
| **Lexicon**     | `tests/test_lexicon_index.py`           | Tests in-memory indexing and lookups.                   |
| **Lexicon**     | `tests/test_lexicon_wikidata_bridge.py` | Tests Wikidata QID extraction/bridge logic.             |
| **Frames**      | `tests/test_frames_*.py`                | Unit tests for semantic frame dataclasses.              |
| **API**         | `tests/http_api/test_generate.py`       | Tests `POST /generate` with various payloads.           |
| **API**         | `tests/http_api/test_ai.py`             | Tests AI suggestion endpoints.                          |
| **Core**        | `tests/core/test_use_cases.py`          | Tests domain use cases (GenerateText, BuildLanguage).   |

---

## 9. 🧩 Tools Runner (Backend API)

The GUI runs tools through a strict **backend allowlist registry** (no arbitrary execution).

| Endpoint                     | Purpose                                                                                                                                                                                                                                  |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /api/v1/tools/registry` | Returns tool metadata (`tool_id`, description, timeout, availability, AI gating).                                                                                                                                                        |
| `POST /api/v1/tools/run`     | Runs a tool by `tool_id` plus argv-style args and optional dry-run mode. Returns a **stable response envelope** containing `trace_id`, command, stdout/stderr, truncation info, accepted/rejected args, lifecycle events, and exit code. |

**Request shape (high-level):**

* `tool_id`: string
* `args`: string[] *(argv-style)*
* `dry_run`: boolean *(optional; preferred for GUI-level dry-run switching)*

**Dry-run note:** Prefer using `dry_run=true` at the API layer. Avoid relying on per-tool argv conventions for “dry run” flags.

**Secret handling:** Do **not** pass API keys/tokens/passwords in `args`. Args may be echoed into response envelopes and UI debug bundles. Provide secrets via environment variables / secret injection (recommended: `ARCHITECT_API_KEY`; fallbacks: `AWA_API_KEY`, `API_SECRET`, `API_KEY`).

**Execution constraints:** repo-root fixed by `FILESYSTEM_REPO_PATH`; output truncation by `ARCHITECT_TOOLS_MAX_OUTPUT_CHARS`; default timeout by `ARCHITECT_TOOLS_DEFAULT_TIMEOUT_SEC`; AI gating by `ARCHITECT_ENABLE_AI_TOOLS`.

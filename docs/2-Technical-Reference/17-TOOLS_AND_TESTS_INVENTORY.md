# 📚 The Complete Tools & Tests Inventory (Final)

**SemantiK Architect**

Status: normative
Owner: Tools / QA / Runtime / Frontend
Scope: complete inventory and usage model for tools, test surfaces, QA flows, and AI-assisted utilities in the final planner-first multilingual runtime

This document is the **Single Source of Truth** for:

1. **GUI Tools** (Web Dashboard)
2. **Workflow Filters** (Tools Page)
3. **CLI Orchestration** (Backend Management)
4. **Build & Matrix Operations**
5. **Diagnostics & Recovery**
6. **Data Operations** (Lexicon & Imports)
7. **Quality Assurance** (Testing & Validation)
8. **AI Services** (Agents and AI-gated tools)
9. **Pytest Surfaces** (Regression and acceptance tests)

It exists to prevent the following failure modes:

* treating debug-only tools as part of the normal path,
* confusing matrix/scanner tools with user-facing workflows,
* treating compile success as language readiness,
* treating non-empty output as acceptance success,
* and letting EN/FR cutover validation drift away from the final planner-first runtime model.

---

## 0. Architectural anchor

All tooling and testing described here must align with the final runtime model:

```text
canonical input
  -> normalized frame/domain form
  -> planner
  -> lexical resolution
  -> realizer
  -> SurfaceResult
  -> public response mapping
  -> HTTP JSON response
```

The nominal runtime is **planner-first**.

Normal tool and test flows must validate:

* planner-first runtime behavior,
* explicit runtime metadata,
* correct concrete language realization,
* stable public response contract,
* and language readiness beyond mere compilation or routing.

For EN/FR bio/person generation, the accepted vertical slice is:

* request normalization,
* planner-first generation,
* language-specific realization,
* coherent public envelope,
* acceptance checks,
* and surface-language correctness.

---

## 1. Tools Dashboard UX model

The Tools Dashboard is organized around **user intent**, not backend internals.

### Main controls

* **Workflow / Tool Set** dropdown
* **Power user (debug)** checkbox
* **Advanced filters** shown only when Power user is enabled

### Workflow filters

| Workflow Filter          | Purpose                                                | Normal Tool Set                                                                                                                      |
| ------------------------ | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Recommended**          | Short deterministic path for most work                 | `build_index`, `compile_pgf`, `language_health`, `run_judge`                                                                         |
| **EN/FR Cutover**        | Final runtime/API/QA validation for EN/FR bio/person   | `build_index`, `compile_pgf`, `language_health`, `eval_bios`, `run_judge`                                                            |
| **Language Integration** | Add or repair one language                             | `build_index`, `lexicon_coverage`, `compile_pgf`, `language_health`, `run_judge`, `harvest_lexicon`, `gap_filler`, `bootstrap_tier1` |
| **Lexicon Work**         | Data and vocabulary work                               | `harvest_lexicon`, `gap_filler`, `lexicon_coverage`                                                                                  |
| **Build & Matrix**       | Build-state / inventory work                           | `build_index`, `compile_pgf`                                                                                                         |
| **QA & Validation**      | Runtime, contract, regression, acceptance, performance | `language_health`, `eval_bios`, `run_judge`, `profiler`                                                                              |
| **Debug & Recovery**     | Broken or inconsistent system state                    | `diagnostic_audit`                                                                                                                   |
| **AI Assist**            | AI-gated repair or bootstrap flows                     | `ai_refiner`, `seed_lexicon_ai`                                                                                                      |
| **All**                  | Full visible inventory                                 | All visible tools                                                                                                                    |

### Power user behavior

**Power user** is a **visibility modifier**, not a workflow.

When enabled, it may reveal:

* hidden tools
* scanner-level tools
* test-oriented tools
* internal tools
* heavy tools
* legacy or transitional tools

### Recommended workflow cards

When a workflow filter is selected, the UI should display a short **Recommended Workflow** card.

Examples:

* **Recommended**
  `Build Index → Compile PGF → Language Health → Generate sentence → Run Judge`

* **EN/FR Cutover**
  `Change code/docs → Build Index → Compile PGF → Language Health → Generate EN/FR planner-first examples → Run eval_bios → Run Judge`

* **Language Integration**
  `Add/change files → Build Index → Lexicon Coverage → Harvest / Gap Fill if needed → Bootstrap Tier 1 if needed → Compile PGF → Language Health → Generate sentence → Run Judge`

* **Lexicon Work**
  `Harvest / Seed → Gap Fill → Lexicon Coverage → Build Index → Language Health`

* **Build & Matrix**
  `Build Index → Compile PGF → Language Health`

* **QA & Validation**
  `Language Health → Generate sentence → Run eval_bios or Judge → Profiler`

* **Debug & Recovery**
  `Diagnostic Audit → targeted scanner or pytest surface → fix → Build Index → Compile PGF → Language Health`

* **AI Assist**
  `Use only after deterministic tools show a real gap → AI assist → Build Index → Compile PGF → Language Health → Run Judge`

---

## 2. Core orchestration

Primary entry points for managing the overall system lifecycle.

| Command / Script        | Location | Purpose                                                                    | Key Arguments                       |
| ----------------------- | -------- | -------------------------------------------------------------------------- | ----------------------------------- |
| **`manage.py`**         | `Root`   | Unified CLI for starting, building, and cleaning the system.               | `start`, `build`, `doctor`, `clean` |
| **`Run-Architect.ps1`** | `Root`   | Windows launcher that handles process cleanup and starts the hybrid stack. | none                                |
| **`Makefile`**          | `Root`   | Legacy build shortcuts and convenience wrappers.                           | `all`, `clean`                      |
| **`StartWSL.bat`**      | `Root`   | Quick shell launcher into WSL with venv activated.                         | none                                |

### Core orchestration rule

Normal runtime validation is not complete until it includes:

1. build or rebuild as needed,
2. runtime health checks,
3. at least one real generation request,
4. and the relevant QA or acceptance surface.

---

## 3. The build system

Scripts that turn source grammars into runtime artifacts.

| Tool                    | Location                  | Purpose                                                                   | Key Arguments                                                                                      |
| ----------------------- | ------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **Orchestrator**        | `builder/orchestrator/`   | Canonical build pipeline. Compiles intermediates and links the final PGF. | `--strategy`, `--langs`, `--clean`, `--verbose`, `--max-workers`, `--no-preflight`, `--regen-safe` |
| **Orchestrator (Shim)** | `builder/orchestrator.py` | Backwards-compatible wrapper for legacy callers.                          | delegates to package entrypoint                                                                    |
| **Compiler**            | `builder/compiler.py`     | Low-level wrapper around `gf`. Manages includes and isolation.            | internal                                                                                           |
| **Strategist**          | `builder/strategist.py`   | Chooses build strategy and writes build plan.                             | internal                                                                                           |
| **Forge**               | `builder/forge.py`        | Writes or materializes concrete grammar files according to build plan.    | internal                                                                                           |
| **Healer**              | `builder/healer.py`       | Reads build failures and dispatches AI repair for broken grammars.        | internal                                                                                           |

### Build rule

A successful build is not equivalent to language readiness.

Build success proves only part of the stack:

* grammar compiles,
* artifacts link,
* runtime artifacts exist.

It does **not** prove:

* planner-first correctness,
* surface-language correctness,
* public contract correctness,
* or acceptance readiness.

---

## 4. The Everything Matrix

System intelligence layer that scans repository state and language readiness signals.

> **Important:** `build_index.py` is the **normal** entrypoint. Scanner scripts are Power user / debug tools unless a workflow explicitly requires them.

| Tool                | Location                                     | Purpose                                                                                                                   | Key Arguments                                                                                           |
| ------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| **Matrix Builder**  | `tools/everything_matrix/build_index.py`     | Scans RGL, Lexicon, App, and QA layers to build `everything_matrix.json`. Computes maturity signals and build strategies. | `--out`, `--langs …`, `--force`, `--regen-rgl`, `--regen-lex`, `--regen-app`, `--regen-qa`, `--verbose` |
| **RGL Scanner**     | `tools/everything_matrix/rgl_scanner.py`     | Audits `gf-rgl/src` presence and consistency.                                                                             | scanner-specific                                                                                        |
| **Lexicon Scanner** | `tools/everything_matrix/lexicon_scanner.py` | Scores lexicon maturity by scanning coverage.                                                                             | scanner-specific                                                                                        |
| **App Scanner**     | `tools/everything_matrix/app_scanner.py`     | Scans backend/frontend surfaces for language support signals.                                                             | scanner-specific                                                                                        |
| **QA Scanner**      | `tools/everything_matrix/qa_scanner.py`      | Parses QA artifacts and logs to update quality scoring.                                                                   | scanner-specific                                                                                        |

### Matrix rule in normal workflows

For onboarding and cutover work:

1. add or change files,
2. refresh the Everything Matrix,
3. validate build and runtime,
4. validate the public contract,
5. validate acceptance.

### Readiness rule

Matrix presence or routing signals do not imply language readiness.

A language is not acceptance-ready because it:

* appears in inventory,
* compiles,
* loads,
* routes,
* or emits non-empty output.

---

## 5. Maintenance & diagnostics

Tools used to keep the repository sane and the system healthy.

> **GUI note:** The Tools Dashboard runs through a strict backend allowlist. The “Key Arguments” below reflect allowlisted argv flags for GUI execution.

> **Security note:** Do **not** pass secrets via argv. Tool args may appear in logs, telemetry, UI output, or debug bundles. Use environment-based secret injection.

| Tool                 | Location                    | Purpose                                                                    | Key Arguments                                                                                                                    | Typical Workflow                                                  |
| -------------------- | --------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| **Language Health**  | `tools/language_health.py`  | Deep scan utility for language pipeline health.                            | `--mode`, `--fast`, `--parallel`, `--api-url`, `--timeout`, `--limit`, `--langs …`, `--no-disable-script`, `--verbose`, `--json` | Recommended, EN/FR Cutover, Language Integration, QA & Validation |
| **Diagnostic Audit** | `tools/diagnostic_audit.py` | Forensics audit for stale artifacts and inconsistent outputs.              | `--verbose`, `--json`                                                                                                            | Debug & Recovery                                                  |
| **Root Cleanup**     | `tools/cleanup_root.py`     | Moves loose artifacts into expected folders and cleans known junk outputs. | `--dry-run`, `--verbose`, `--json`                                                                                               | Debug & Recovery                                                  |
| **Bootstrap Tier 1** | `tools/bootstrap_tier1.py`  | Scaffolds Tier 1 wrappers or bridge files for selected languages.          | `--langs …`, `--force`, `--dry-run`, `--verbose`                                                                                 | Language Integration                                              |

### Health rule

`language_health` is necessary but not sufficient for final acceptance.

It is a health tool, not the entire proof layer.

---

## 6. Data operations

Lexicon mining, harvesting, syncing, and vocabulary maintenance.

| Tool                                     | Location                               | Purpose                                                                  | Key Arguments                                                                    | Typical Workflow |
| ---------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------- | ---------------- |
| **Universal Lexicon Harvester**          | `tools/harvest_lexicon.py`             | Two-mode harvester for lexicon data.                                     | `wordnet ...`, `wikidata ...`                                                    |                  |
| **Wikidata Importer (Legacy/Reference)** | `scripts/lexicon/wikidata_importer.py` | Legacy/reference importer logic. Not the authoritative v2 runtime path.  | varies                                                                           |                  |
| **RGL Syncer**                           | `scripts/lexicon/sync_rgl.py`          | Extracts lexical functions from compiled PGF into language shards.       | `--pgf`, `--out-dir`, `--langs`, `--max-funs`, `--dry-run`, `--validate`         |                  |
| **Gap Filler**                           | `tools/lexicon/gap_filler.py`          | Compares target lexicon vs pivot language to find missing concepts.      | `--target`, `--pivot`, `--data-dir`, `--json-out`, `--verbose`                   |                  |
| **Link Libraries**                       | `link_libraries.py`                    | Ensures `Wiki*.gf` opens required modules for runtime lexicon injection. | none                                                                             |                  |
| **Schema/Index Utilities**               | `utils/...`                            | Lexicon index/schema and stats maintenance.                              | `refresh_lexicon_index.py`, `migrate_lexicon_schema.py`, `dump_lexicon_stats.py` |                  |
| **Seed Lexicon (AI)**                    | `utils/seed_lexicon_ai.py`             | Generates seed lexicon for selected languages.                           | AI-gated                                                                         |                  |

### Lexicon rule

Lexicon sufficiency is part of readiness, but it is still not enough by itself.

A language with good lexicon coverage may still fail:

* planner-first generation,
* public contract parity,
* concrete language realization,
* or acceptance correctness.

---

## 7. Quality assurance tools

QA tools that validate runtime output, contract shape, lexicon integrity, acceptance gates, and regression behavior.

| Tool                                  | Location                                        | Purpose                                                                                                                                                 | Key Arguments                                                                              | Typical Workflow                   |
| ------------------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ---------------------------------- |
| **Universal Test Runner**             | `tools/qa/universal_test_runner.py`             | Runs CSV-based suites and emits a report.                                                                                                               | `--suite`, `--in`, `--out`, `--langs …`, `--limit`, `--verbose`, `--fail-fast`, `--strict` | QA & Validation                    |
| **Bio Evaluator**                     | `tools/qa/eval_bios.py`                         | EN/FR and multilingual bio/person evaluator. Validates response contract, runtime path, fallback behavior, language plausibility, and acceptance gates. | `--langs …`, `--limit`, `--out`, `--verbose`                                               | EN/FR Cutover, QA & Validation     |
| **Lexicon Coverage Report**           | `tools/qa/lexicon_coverage_report.py`           | Coverage report for intended vs implemented lexicon and errors.                                                                                         | `--lang`, `--include-files`, `--verbose`, `--fail-on-errors`                               | Language Integration, Lexicon Work |
| **Ambiguity Detector**                | `tools/qa/ambiguity_detector.py`                | Checks curated ambiguous sentences for multiple parse trees.                                                                                            | `--lang`, `--sentence`, `--topic`, `--json-out`, `--verbose`                               | QA & Validation                    |
| **Batch Test Generator**              | `tools/qa/batch_test_generator.py`              | Generates large regression datasets for QA.                                                                                                             | `--langs …`, `--out`, `--limit`, `--seed`, `--verbose`                                     | QA & Validation                    |
| **Test Suite Generator**              | `tools/qa/test_suite_generator.py`              | Generates empty CSV templates for manual fill-in.                                                                                                       | `--langs …`, `--out`, `--verbose`                                                          | QA & Validation                    |
| **Lexicon Regression Test Generator** | `tools/qa/generate_lexicon_regression_tests.py` | Builds lexicon regression tests for CI.                                                                                                                 | `--langs …`, `--out`, `--limit`, `--verbose`, `--lexicon-dir`                              | QA & Validation                    |
| **Profiler**                          | `tools/health/profiler.py`                      | Benchmarks grammar/runtime performance.                                                                                                                 | `--lang`, `--iterations`, `--update-baseline`, `--threshold`, `--verbose`                  | QA & Validation                    |
| **AST Visualizer**                    | `tools/debug/visualize_ast.py`                  | Generates JSON AST from sentence, intent, or explicit AST.                                                                                              | `--lang`, `--sentence`, `--ast`, `--pgf`                                                   | Debug & Recovery                   |

### EN/FR acceptance validation chain

For the final EN/FR bio/person vertical slice:

1. `build_index`
2. `compile_pgf`
3. `language_health`
4. generate real EN and FR planner-first requests
5. validate the public response envelope
6. run `eval_bios`
7. run targeted pytest surfaces
8. only then treat EN/FR as accepted

### Evaluator rule

`eval_bios` must reject false positives such as:

* routed language looks correct but surface language is wrong,
* planner-first claimed but required metadata is missing,
* fallback used when nominal planner-first success is required.

---

## 8. AI services

Autonomous agents and AI-gated tools.

| Agent / Tool          | File                           | Role                                                                      | Triggered By                 |
| --------------------- | ------------------------------ | ------------------------------------------------------------------------- | ---------------------------- |
| **The Architect**     | `ai_services/architect.py`     | Generates missing grammars based on topology constraints.                 | Build/CLI workflow           |
| **The Surgeon**       | `ai_services/surgeon.py`       | Repairs broken `.gf` files using compiler logs.                           | `builder/healer.py`          |
| **The Lexicographer** | `ai_services/lexicographer.py` | Bootstraps core vocabulary for empty languages.                           | CLI / missing-data workflows |
| **The Judge**         | `ai_services/judge.py`         | Grades generated text against gold standards and regression expectations. | quality workflows            |
| **AI Refiner**        | `tools/ai_refiner.py`          | Upgrades weak grammars toward RGL compliance.                             | AI-gated tools runner        |
| **Seed Lexicon (AI)** | `utils/seed_lexicon_ai.py`     | Generates seed lexicon for selected languages.                            | AI-gated tools runner        |

### AI gating

Backend enforces `ARCHITECT_ENABLE_AI_TOOLS=1` for AI-gated tools.

### AI usage rule

AI tools do not replace deterministic proof.

They belong to **AI Assist** and should not appear in the normal deterministic path unless explicitly requested or Power user mode is enabled.

---

## 9. Pytest surfaces

Automated regression and acceptance harness. Run with `pytest <path>`.

| Category            | File                                                       | Description                                                                                                                     |
| ------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| **Core**            | `tests/core/test_use_cases.py`                             | Tests use cases such as `GenerateText`, including planner-first behavior, fallback behavior, and runtime metadata expectations. |
| **Core**            | `tests/core/test_domain_models.py`                         | Tests runtime model behavior including `SurfaceResult` expectations and debug/top-level consistency rules.                      |
| **Integration**     | `tests/integration/test_generate_via_planner_en.py`        | EN planner-first generation integration checks.                                                                                 |
| **Integration**     | `tests/integration/test_generate_via_planner_fr.py`        | FR planner-first generation integration checks.                                                                                 |
| **Integration**     | `tests/integration/test_quality.py`                        | Judge-based regression checks and quality evaluation.                                                                           |
| **Integration**     | `tests/integration/test_worker_flow.py`                    | Verifies worker compilation/job flow.                                                                                           |
| **Integration**     | `tests/integration/test_ninai.py`                          | Tests Ninai adapter parsing logic.                                                                                              |
| **Smoke**           | `tests/test_api_smoke.py`                                  | Checks `/health` and generation-related endpoints.                                                                              |
| **Smoke**           | `tests/test_gf_dynamic.py`                                 | Validates dynamic loading and linearization of GF grammars.                                                                     |
| **Smoke**           | `tests/test_lexicon_smoke.py`                              | Validates lexicon JSON schema and syntax.                                                                                       |
| **Multilingual**    | `tests/test_multilingual_generation.py`                    | Cross-language generation regression surface.                                                                                   |
| **Lexicon**         | `tests/test_lexicon_loader.py`                             | Tests lazy-loading of lexicon shards.                                                                                           |
| **Lexicon**         | `tests/test_lexicon_index.py`                              | Tests in-memory indexing and lookups.                                                                                           |
| **Lexicon**         | `tests/test_lexicon_wikidata_bridge.py`                    | Tests Wikidata QID extraction and bridge logic.                                                                                 |
| **Frames**          | `tests/test_frames_*.py`                                   | Unit tests for semantic frame dataclasses.                                                                                      |
| **API**             | `tests/http_api/test_generate.py`                          | Tests `POST /generate` request/response behavior.                                                                               |
| **API**             | `tests/http_api/test_generations.py`                       | Tests generation API variants and response contract behavior.                                                                   |
| **API**             | `tests/http_api/test_ai.py`                                | Tests AI suggestion endpoints.                                                                                                  |
| **Planning**        | `tests/unit/planning/test_construction_plan.py`            | Tests construction plan behavior and invariants.                                                                                |
| **Planning**        | `tests/unit/planning/test_frame_to_plan.py`                | Tests frame-to-plan conversion.                                                                                                 |
| **Planning**        | `tests/unit/planning/test_frame_to_slots.py`               | Tests slot extraction and mapping.                                                                                              |
| **Lexicon Runtime** | `tests/unit/lexicon/test_lexical_resolution.py`            | Tests lexical resolution behavior.                                                                                              |
| **Use Cases**       | `tests/unit/use_cases/test_plan_text.py`                   | Tests planning use case behavior.                                                                                               |
| **Use Cases**       | `tests/unit/use_cases/test_realize_text.py`                | Tests realization use case behavior.                                                                                            |
| **Renderers**       | `tests/unit/renderers/test_family_construction_adapter.py` | Tests family renderer adapter behavior.                                                                                         |
| **Renderers**       | `tests/unit/renderers/test_gf_construction_adapter.py`     | Tests GF renderer adapter behavior.                                                                                             |

### Pytest rule

For final EN/FR cutover proof, pytest must cover:

* nominal planner-first success,
* explicit fallback behavior,
* fallback-disabled failure behavior,
* runtime metadata presence,
* public contract expectations,
* EN/FR realization correctness,
* and regression against routed-but-wrong-language false positives.

### Pytest tools in the dashboard

Pytest-backed tools belong mainly to:

* **QA & Validation**
* **Debug & Recovery**
* Power user mode

---

## 10. Tools runner (backend API)

The GUI runs tools through a strict backend allowlist registry. There is no arbitrary execution.

| Endpoint                     | Purpose                                                                                                                                                                                                                         |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /api/v1/tools/registry` | Returns tool metadata, availability, UI metadata, and workflow metadata for the dashboard.                                                                                                                                      |
| `POST /api/v1/tools/run`     | Runs a tool by `tool_id` plus argv-style args and optional dry-run mode. Returns a stable response envelope containing trace, command, stdout/stderr, truncation info, accepted/rejected args, lifecycle events, and exit code. |

### Request shape

* `tool_id`: string
* `args`: string[]
* `dry_run`: boolean, optional

### Dry-run note

Prefer using `dry_run=true` at the API layer instead of relying on per-tool argv conventions.

### Secret handling

Do **not** pass API keys, tokens, or passwords in `args`.

Use environment variables or secret injection instead.

### Execution constraints

* repository root fixed by `FILESYSTEM_REPO_PATH`
* output truncation by `ARCHITECT_TOOLS_MAX_OUTPUT_CHARS`
* default timeout by `ARCHITECT_TOOLS_DEFAULT_TIMEOUT_SEC`
* AI gating by `ARCHITECT_ENABLE_AI_TOOLS`

---

## 11. Registry metadata model

The tools registry carries both execution metadata and UI/workflow metadata.

### Tool-level registry metadata

Each tool may expose:

* `tool_id`
* `label`
* `description`
* `timeout_sec`
* `allow_args`
* `requires_ai_enabled`
* `available`
* `category`
* `hidden`
* `legacy`
* `internal`
* `heavy`
* `is_test`
* `allowed_flags`
* `allow_positionals`
* `flags_with_value`
* `flags_with_multi_value`
* `workflow_tags`
* `workflow_order`

### Workflow registry metadata

The registry may also expose a `workflows` array, where each workflow includes:

* `workflow_id`
* `label`
* `summary`
* `steps`
* `tool_ids`
* `power_user_addons`

### Why this exists

This lets the frontend:

* render the workflow dropdown,
* render the recommended workflow card,
* filter tools by user intent,
* keep workflow taxonomy synchronized with backend truth.

---

## 12. Normal workflow reference

### Recommended

1. `build_index`
2. `compile_pgf`
3. `language_health`
4. generate a sentence
5. `run_judge`

### EN/FR Cutover

1. change grammar, runtime, contract, or docs
2. `build_index`
3. `compile_pgf`
4. `language_health`
5. generate real EN and FR planner-first requests
6. inspect public response shape
7. `eval_bios`
8. run targeted pytest surfaces
9. only then declare the slice accepted

### Language Integration

1. add or change language files
2. `build_index`
3. `lexicon_coverage`
4. `harvest_lexicon` or `gap_filler` if needed
5. `bootstrap_tier1` if needed
6. `compile_pgf`
7. `language_health`
8. generate a sentence
9. `run_judge`

### Lexicon Work

1. `harvest_lexicon` or `seed_lexicon_ai`
2. `gap_filler`
3. `lexicon_coverage`
4. `build_index`
5. `language_health`

### Build & Matrix

1. `build_index`
2. `compile_pgf`
3. `language_health`

### QA & Validation

1. `language_health`
2. generate a sentence
3. `eval_bios` or `run_judge`
4. run targeted pytest surface
5. `profiler` if needed

### Debug & Recovery

1. `diagnostic_audit`
2. targeted scanner or pytest surface
3. fix
4. `build_index`
5. `compile_pgf`
6. `language_health`

### AI Assist

1. confirm deterministic workflow failed or is incomplete
2. run AI assist tool
3. `build_index`
4. `compile_pgf`
5. `language_health`
6. `run_judge`

---

## 13. Acceptance-oriented rules

### 13.1 Build is not acceptance

A language is not accepted because it:

* compiles,
* loads,
* routes,
* or emits non-empty text.

### 13.2 Planner-first is the nominal path

The expected primary runtime is planner-first.

Legacy success does not count as nominal planner-first acceptance.

### 13.3 EN/FR are the first full vertical slice

EN and FR bio/person generation are the first acceptance-ready slice that must prove:

* planner-first runtime,
* correct concrete language realization,
* coherent public contract,
* evaluator success,
* and regression protection.

### 13.4 Evaluators and tests must reject false positives

The system must fail EN/FR acceptance when:

* FR resolves correctly but surfaces English,
* planner-first is claimed but required metadata is absent,
* fallback is used where nominal success is required,
* or top-level public fields and debug info disagree.

---

## 14. Summary rules

* **Power user** is a visibility switch, not a workflow.
* **Workflow dropdown** is the primary navigation model for the Tools page.
* **`build_index`** is a normal visible workflow tool, not a debug-only tool.
* **Scanners** are debug-level tools unless explicitly needed.
* **AI tools** belong to **AI Assist**, not the normal deterministic path.
* **Build success is not language readiness.**
* **Routing success is not language correctness.**
* **A language is not truly integrated until it generates correctly on the required runtime path and passes the relevant acceptance gates.**

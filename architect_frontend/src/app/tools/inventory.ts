// architect_frontend/src/app/tools/inventory.ts
import type { Tool } from "./types";

/**
 * Tools Command Center
 * Inventory v2.6.0 (generated 2026-03-19)
 * API: http://localhost:8000/api/v1
 *
 * Normal mode shows backend-wired runnable tools aligned to the planner-first
 * runtime workflows.
 *
 * Enable Power user (debug) to reveal the broader inventory, including scanners,
 * deeper QA surfaces, and legacy/reference paths that still matter for audits.
 */
export const INVENTORY = {
  version: "2.6.0",
  generated_on: "2026-03-19",
  root_entrypoints: [
    "Makefile",
    "context_gatherer.py",
    "generate_path_map.py",
    "GitSink.bat",
    "link_libraries.py",
    "manage.py",
    "Run-Architect.ps1",
    "smoke_test.py",
    "StartWSL.bat",
    "sync_config_from_gf.py",
    "disable_broken_compile.sh",
    "docker-compose.yml",
    "tempo.py",
  ],
  gf: ["builder/orchestrator.py"],
  tools: {
    root: [
      "tools/ai_refiner.py",
      "tools/bootstrap_tier1.py",
      "tools/cleanup_root.py",
      "tools/diagnostic_audit.py",
      "tools/harvest_lexicon.py",
      "tools/language_health.py",
    ],
    everything_matrix: [
      "tools/everything_matrix/app_scanner.py",
      "tools/everything_matrix/build_index.py",
      "tools/everything_matrix/lexicon_scanner.py",
      "tools/everything_matrix/qa_scanner.py",
      "tools/everything_matrix/rgl_scanner.py",
    ],
    qa: [
      "tools/qa/ambiguity_detector.py",
      "tools/qa/batch_test_generator.py",
      "tools/qa/eval_bios.py",
      "tools/qa/generate_lexicon_regression_tests.py",
      "tools/qa/lexicon_coverage_report.py",
      "tools/qa/test_suite_generator.py",
      "tools/qa/universal_test_runner.py",
    ],
    debug: ["tools/debug/visualize_ast.py"],
    health: ["tools/health/profiler.py"],
    lexicon: ["tools/lexicon/gap_filler.py"],
  },
  scripts: {
    root: [
      "scripts/demo_generation.py",
      "scripts/demo_quad.py",
      "scripts/test_api_generation.py",
      "scripts/test_tier1_load.py",
    ],
    lexicon: ["scripts/lexicon/sync_rgl.py", "scripts/lexicon/wikidata_importer.py"],
  },
  utils: [
    "utils/__init__.py",
    "utils/build_lexicon_from_wikidata.py",
    "utils/dump_lexicon_stats.py",
    "utils/grammar_factory.py",
    "utils/logging_setup.py",
    "utils/migrate_lexicon_schema.py",
    "utils/refresh_lexicon_index.py",
    "utils/seed_lexicon_ai.py",
    "utils/wikifunctions_api_mock.py",
  ],
  ai_services: [
    "ai_services/__init__.py",
    "ai_services/architect.py",
    "ai_services/client.py",
    "ai_services/judge.py",
    "ai_services/lexicographer.py",
    "ai_services/prompts.py",
    "ai_services/surgeon.py",
  ],
  nlg: ["nlg/api.py", "nlg/cli_frontend.py", "nlg/semantics/__init__.py"],
  prototypes: [],
  tests: {
    root: [
      "tests/__init__.py",
      "tests/conftest.py",
      "tests/test_api_smoke.py",
      "tests/test_frames_entity.py",
      "tests/test_frames_event.py",
      "tests/test_frames_meta.py",
      "tests/test_frames_narrative.py",
      "tests/test_frames_relational.py",
      "tests/test_gf_dynamic.py",
      "tests/test_lexicon_index.py",
      "tests/test_lexicon_loader.py",
      "tests/test_lexicon_smoke.py",
      "tests/test_lexicon_wikidata_bridge.py",
      "tests/test_multilingual_generation.py",
    ],
    // Canonical HTTP API surface
    http_api: [
      "tests/http_api/test_ai.py",
      "tests/http_api/test_entities.py",
      "tests/http_api/test_frames_registry.py",
      "tests/http_api/test_generate.py",
      "tests/http_api/test_generations.py",
    ],
    // Backward-compatible alias kept to avoid breaking any old readers of this snapshot
    http_api_legacy: [
      "tests/http_api/test_ai.py",
      "tests/http_api/test_entities.py",
      "tests/http_api/test_frames_registry.py",
      "tests/http_api/test_generate.py",
      "tests/http_api/test_generations.py",
    ],
    core: [
      "tests/core/test_domain_models.py",
      "tests/core/test_use_cases.py",
    ],
    integration: [
      "tests/integration/test_generate_via_planner_en.py",
      "tests/integration/test_generate_via_planner_fr.py",
      "tests/integration/test_ninai.py",
      "tests/integration/test_quality.py",
      "tests/integration/test_worker_flow.py",
    ],
    unit_use_cases: [
      "tests/unit/use_cases/test_plan_text.py",
      "tests/unit/use_cases/test_realize_text.py",
    ],
    unit_renderers: [
      "tests/unit/renderers/test_family_construction_adapter.py",
      "tests/unit/renderers/test_gf_construction_adapter.py",
    ],
    unit_planning: [
      "tests/unit/planning/test_construction_plan.py",
      "tests/unit/planning/test_frame_to_plan.py",
      "tests/unit/planning/test_frame_to_slots.py",
    ],
    unit_lexicon: ["tests/unit/lexicon/test_lexical_resolution.py"],
    // Backward-compatible catch-all bucket retained for older UI assumptions
    adapters_core_integration: [
      "tests/adapters/test_api_endpoints.py",
      "tests/adapters/test_wikidata_adapter.py",
      "tests/core/test_domain_models.py",
      "tests/core/test_use_cases.py",
      "tests/integration/test_generate_via_planner_en.py",
      "tests/integration/test_generate_via_planner_fr.py",
      "tests/integration/test_ninai.py",
      "tests/integration/test_quality.py",
      "tests/integration/test_worker_flow.py",
    ],
  },
} as const;

export type Inventory = typeof INVENTORY;

/**
 * Flattened, de-duplicated list of every file path in the snapshot.
 * Handy for quick lookups, search indices, or sanity checks.
 */
export const INVENTORY_PATHS: readonly string[] = (() => {
  const out: string[] = [];
  const seen = new Set<string>();

  const addMany = (arr?: readonly string[]) => {
    if (!arr) return;
    for (const p of arr) {
      if (!p || seen.has(p)) continue;
      seen.add(p);
      out.push(p);
    }
  };

  addMany(INVENTORY.root_entrypoints);
  addMany(INVENTORY.gf);

  addMany(INVENTORY.tools.root);
  addMany(INVENTORY.tools.everything_matrix);
  addMany(INVENTORY.tools.qa);
  addMany(INVENTORY.tools.debug);
  addMany(INVENTORY.tools.health);
  addMany(INVENTORY.tools.lexicon);

  addMany(INVENTORY.scripts.root);
  addMany(INVENTORY.scripts.lexicon);

  addMany(INVENTORY.utils);
  addMany(INVENTORY.ai_services);
  addMany(INVENTORY.nlg);
  addMany(INVENTORY.prototypes);

  addMany(INVENTORY.tests.root);
  addMany(INVENTORY.tests.http_api);
  addMany(INVENTORY.tests.http_api_legacy);
  addMany(INVENTORY.tests.core);
  addMany(INVENTORY.tests.integration);
  addMany(INVENTORY.tests.unit_use_cases);
  addMany(INVENTORY.tests.unit_renderers);
  addMany(INVENTORY.tests.unit_planning);
  addMany(INVENTORY.tests.unit_lexicon);
  addMany(INVENTORY.tests.adapters_core_integration);

  return Object.freeze(out);
})();

// --- ACTIVE TOOL REGISTRY (GUI) ---
// Keep this list user-facing & curated (not necessarily 1:1 with every inventory path).
// These tools align with the current planner-first runtime workflows and the
// EN/FR final cutover validation chain.
export const TOOLS = [
  {
    id: "build_index",
    name: "Build Index",
    description:
      "Refresh the Everything Matrix and repository readiness signals before build, runtime, or QA work.",
    category: "build",
    defaultArgs: "--verbose",
  },
  {
    id: "compile_pgf",
    name: "Compile Grammar",
    description: "Trigger a full PGF compilation sequence.",
    category: "build",
    defaultArgs: "",
  },
  {
    id: "language_health",
    name: "Language Health",
    description: "Deep scan of compilation status and API runtime health.",
    category: "maintenance",
    defaultArgs: "--verbose",
  },
  {
    id: "diagnostic_audit",
    name: "Diagnostic Audit",
    description: "Identify stale artifacts, zombie files, and broken grammar links.",
    category: "maintenance",
    defaultArgs: "--verbose",
  },
  {
    id: "lexicon_coverage",
    name: "Lexicon Coverage",
    description: "Report on vocabulary size, intended coverage, and semantic gaps per language.",
    category: "data",
    defaultArgs: "--include-files",
  },
  {
    id: "harvest_lexicon",
    name: "Harvest Lexicon",
    description: "Import words from Wikidata or WordNet.",
    category: "data",
    defaultArgs: "",
  },
  {
    id: "gap_filler",
    name: "Lexicon Gap Filler",
    description: "Find missing words compared to a pivot language.",
    category: "data",
    defaultArgs: "--verbose",
  },
  {
    id: "bootstrap_tier1",
    name: "Bootstrap Tier 1",
    description: "Scaffold Tier 1 wrappers or bridge files for selected languages.",
    category: "maintenance",
    defaultArgs: "--verbose",
  },
  {
    id: "eval_bios",
    name: "Bio Evaluator",
    description:
      "Run EN/FR and multilingual bio/person evaluation with runtime-path, contract, and surface-language checks.",
    category: "qa",
    defaultArgs: "--verbose",
  },
  {
    id: "run_judge",
    name: "Run Judge",
    description: "Execute Gold Standard regression tests via AI Judge.",
    category: "qa",
    defaultArgs: "--verbose",
  },
  {
    id: "profiler",
    name: "Performance Profiler",
    description: "Measure runtime latency and performance regressions.",
    category: "health",
    defaultArgs: "--verbose",
  },
  {
    id: "ai_refiner",
    name: "AI Refiner",
    description: "Refine grammar rules using AI after deterministic workflows identify a real gap.",
    category: "ai",
    defaultArgs: "--verbose",
  },
] as const satisfies readonly Tool[];

export type ToolId = (typeof TOOLS)[number]["id"];

export const TOOL_BY_ID: Readonly<Record<ToolId, (typeof TOOLS)[number]>> = Object.freeze(
  TOOLS.reduce((acc, t) => {
    acc[t.id] = t;
    return acc;
  }, {} as Record<ToolId, (typeof TOOLS)[number]>)
);

export const TOOL_DEFAULT_ARGS: Readonly<Record<ToolId, string>> = Object.freeze(
  TOOLS.reduce((acc, t) => {
    acc[t.id] = t.defaultArgs;
    return acc;
  }, {} as Record<ToolId, string>)
);


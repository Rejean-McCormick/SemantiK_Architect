// architect_frontend/src/app/tools/classify.ts
import { BACKEND_TOOL_REGISTRY, type Risk } from "./backendRegistry";

export type Status = "active" | "legacy" | "experimental" | "internal";
export type Visibility = "default" | "debug";

export type ToolKind =
  | "entrypoint"
  | "tool"
  | "script"
  | "test"
  | "utility"
  | "agent"
  | "prototype";

// ----------------------------------------------------------------------------
// Small helpers (fast + consistent)
// ----------------------------------------------------------------------------
const lc = (s: string) => s.toLowerCase();

const startsWithAny = (s: string, prefixes: readonly string[]) => {
  for (const p of prefixes) if (s.startsWith(p)) return true;
  return false;
};

const includesAny = (s: string, needles: readonly string[]) => {
  for (const n of needles) if (s.includes(n)) return true;
  return false;
};

const riskRank = (r: Risk): number => (r === "heavy" ? 3 : r === "moderate" ? 2 : 1);
const maxRisk = (a: Risk, b: Risk): Risk => (riskRank(a) >= riskRank(b) ? a : b);

// ----------------------------------------------------------------------------
// Backend registry helpers (one-time derived maps)
// ----------------------------------------------------------------------------
type BackendMetaLite = { path: string; hidden?: boolean; risk?: Risk };

const BACKEND_BY_ID = BACKEND_TOOL_REGISTRY as unknown as Record<string, BackendMetaLite | undefined>;

const BACKEND_BY_PATH_LOWER: ReadonlyMap<string, { hidden: boolean; risk?: Risk }> = (() => {
  const m = new Map<string, { hidden: boolean; risk?: Risk }>();

  for (const meta of Object.values(BACKEND_BY_ID)) {
    if (!meta?.path) continue;
    const key = lc(meta.path);

    const prev = m.get(key);
    const hidden = Boolean(prev?.hidden) || Boolean(meta.hidden);

    const risk = prev?.risk
      ? meta.risk
        ? maxRisk(prev.risk, meta.risk)
        : prev.risk
      : meta.risk;

    m.set(key, { hidden, risk });
  }

  return m;
})();

/**
 * Central place to decide whether a backend-wired tool should be hidden
 * from normal users (revealed when Debug/Power user is enabled).
 *
 * Source of truth: backendRegistry.hidden flag.
 */
export const isPowerUserToolId = (toolId?: string): boolean => {
  if (!toolId) return false;
  return Boolean(BACKEND_BY_ID[toolId]?.hidden);
};

// ----------------------------------------------------------------------------
// Exclusion / runnable utility policy
// ----------------------------------------------------------------------------
/**
 * Files we never want to show in the Tools UI (even in debug mode).
 * These are not meaningful “runnable tools” and create noise/confusion.
 */
export const shouldExcludeFromToolsUI = (path: string): boolean => {
  const p = lc(path);

  // Python package markers / pure module markers
  if (p.endsWith("/__init__.py") || p.endsWith("__init__.py")) return true;

  // Generated outputs are not “tools” (they’re build artifacts)
  if (p.startsWith("generated/")) return true;

  // If you later add docs/config to the inventory, keep them out of Tools UI:
  if (startsWithAny(p, ["docs/", "config/"])) return true;

  return false;
};

const RUNNABLE_UTIL_ALLOWLIST = [
  "refresh_lexicon_index",
  "migrate_lexicon_schema",
  "dump_lexicon_stats",
  "seed_lexicon_ai",
  "build_lexicon_from_wikidata",
] as const;

/**
 * Some utilities are “real tools” (runnable CLIs) even if they live under utils/.
 * Keep these visible by default.
 */
export const isRunnableUtility = (path: string): boolean => {
  const p = lc(path);
  if (!p.startsWith("utils/")) return false;
  return includesAny(p, RUNNABLE_UTIL_ALLOWLIST);
};

// ----------------------------------------------------------------------------
// Risk / Status / Title / CLI helpers
// ----------------------------------------------------------------------------
const HEAVY_HINTS = [
  "gf/build_orchestrator",
  "build_orchestrator",
  "compile_pgf",
  "seed_lexicon_ai",
  "seed_lexicon",
  "ai_refiner",
] as const;

const MODERATE_HINTS = [
  "migrate",
  "wikidata",
  "bootstrap_tier1",
  "universal_test_runner",
  "batch_test_generator",
  "build_index",
  "harvest_lexicon",
  "test_runner",
] as const;

export const riskFromPath = (path: string): Risk => {
  const p = lc(path);
  if (includesAny(p, HEAVY_HINTS)) return "heavy";
  if (includesAny(p, MODERATE_HINTS)) return "moderate";
  return "safe";
};

export const statusFromPath = (path: string): Status => {
  const p = lc(path);
  if (p.startsWith("prototypes/")) return "experimental";
  if (p.startsWith("tests/http_api/")) return "legacy";
  if (p.startsWith("scripts/lexicon/")) return "legacy";
  if (p.endsWith("/__init__.py") || p.endsWith("__init__.py")) return "internal";
  if (p.includes("test_api_generation.py")) return "legacy";
  return "active";
};

export const titleFromPath = (path: string): string => {
  const base = path.split("/").pop() || path;
  const stem = base.replace(/\.[^.]+$/, "");
  return stem.replace(/[_-]+/g, " ").replace(/\b\w/g, (m) => m.toUpperCase());
};

export const cliFromPath = (path: string): string[] => {
  const ext = (path.split(".").pop() || "").toLowerCase();
  if (path.startsWith("tests/")) return [`python -m pytest ${path}`];
  if (ext === "ps1") return [`powershell -ExecutionPolicy Bypass -File ${path}`];
  if (ext === "bat" || ext === "cmd") return [path];
  if (ext === "sh") return [`bash ${path}`];
  if (ext === "py") return [`python ${path}`];
  return [path];
};

// ----------------------------------------------------------------------------
// Visibility policy
// ----------------------------------------------------------------------------
const rootSetCache = new WeakMap<readonly string[], ReadonlySet<string>>();
const getRootSet = (arr: readonly string[]) => {
  const cached = rootSetCache.get(arr);
  if (cached) return cached;
  const s = new Set(arr);
  rootSetCache.set(arr, s);
  return s;
};

/**
 * Visibility policy:
 * - "default": stuff we expect normal users to browse/run regularly
 * - "debug": noisy/legacy/experimental/internal things that power users may want
 */
export const visibilityFromPath = (
  inventoryRootEntrypoints: readonly string[],
  path: string
): Visibility => {
  const p = lc(path);
  const rootSet = getRootSet(inventoryRootEntrypoints);

  // Root entrypoints are always “default”
  if (rootSet.has(path)) return "default";

  // Primary “tool surfaces”
  if (startsWithAny(p, ["tools/", "gf/"])) return "default";

  // Runnable CLIs under utils/ are useful in default mode
  if (isRunnableUtility(path)) return "default";

  // Everything else is debug-only (noise / reference / internal modules)
  if (startsWithAny(p, ["tests/", "scripts/", "prototypes/", "ai_services/", "nlg/", "utils/"]))
    return "debug";

  return "debug";
};

// ----------------------------------------------------------------------------
// Classification
// ----------------------------------------------------------------------------
type Classification = {
  category: string;
  group: string;
  kind: ToolKind;
  statusOverride?: Status;
  riskOverride?: Risk;
  visibility: Visibility;
  hideByDefault: boolean;
  excludeFromUI: boolean;
  notes: string[];
  uiSteps: string[];
};

const mk = (base: Omit<Classification, "hideByDefault"> & { hideByDefault?: boolean }): Classification => ({
  ...base,
  hideByDefault: Boolean(base.hideByDefault),
});

export const classify = (
  inventoryRootEntrypoints: readonly string[],
  path: string
): Classification => {
  const p = lc(path);
  const rootSet = getRootSet(inventoryRootEntrypoints);

  const status = statusFromPath(path);
  const visibility = visibilityFromPath(inventoryRootEntrypoints, path);
  const excludeFromUI = shouldExcludeFromToolsUI(path);

  const backend = BACKEND_BY_PATH_LOWER.get(p);
  const hideBecauseBackend = Boolean(backend?.hidden);

  const backendNote = hideBecauseBackend
    ? ["Backend-wired but hidden: visible only in Power user (debug) mode."]
    : [];

  // If it’s excluded, still return a coherent classification (caller can filter it out).
  if (excludeFromUI) {
    return mk({
      category: "Internal",
      group: "Hidden",
      kind: "utility",
      statusOverride: "internal",
      visibility: "debug",
      hideByDefault: true,
      excludeFromUI: true,
      notes: ["Hidden from Tools UI (non-actionable file / artifact)."],
      uiSteps: ["(Hidden)"],
    });
  }

  if (rootSet.has(path)) {
    return mk({
      category: "Launch & Entry Points",
      group: "Root",
      kind: "entrypoint",
      visibility,
      hideByDefault: visibility === "debug" || hideBecauseBackend,
      excludeFromUI,
      notes: ["Prefer these entrypoints over ad-hoc runs when possible.", ...backendNote],
      uiSteps: ["Select the entrypoint.", "Open in Repo for parameters.", "Run only if backend wiring exists."],
    });
  }

  if (p.startsWith("gf/")) {
    return mk({
      category: "Build System",
      group: "GF Build",
      kind: "tool",
      riskOverride: backend?.risk ?? "heavy",
      visibility,
      hideByDefault: visibility === "debug" || hideBecauseBackend,
      excludeFromUI,
      notes: [
        "Heaviest operation (CPU/time). Avoid parallel heavy runs.",
        "If build fails, run Diagnostics & Maintenance next, then retry.",
        ...backendNote,
      ],
      uiSteps: ["Click Run and monitor console output.", "On failure, copy logs and inspect the tool."],
    });
  }

  if (p.startsWith("tools/everything_matrix/")) {
    return mk({
      category: "Build System",
      group: "Everything Matrix",
      kind: "tool",
      visibility,
      hideByDefault: visibility === "debug" || hideBecauseBackend,
      excludeFromUI,
      notes: ["Scanners used to compute everything_matrix.json and maturity/QA signals.", ...backendNote],
      uiSteps: ["Prefer running build_index unless debugging a specific scanner."],
    });
  }

  if (p.startsWith("tools/qa/")) {
    return mk({
      category: "QA & Testing",
      group: "QA Tools",
      kind: "tool",
      visibility,
      hideByDefault: visibility === "debug" || hideBecauseBackend,
      excludeFromUI,
      notes: ["QA utilities (runners/generators/reports). Batch generators can be long-running.", ...backendNote],
      uiSteps: ["Click Run and monitor output.", "If it generates files, check git status and review diffs."],
    });
  }

  if (p.startsWith("tools/")) {
    if (/(diagnostic|cleanup|health|doctor)/.test(p)) {
      return mk({
        category: "Diagnostics & Maintenance",
        group: "Health & Cleanup",
        kind: "tool",
        visibility,
        hideByDefault: visibility === "debug" || hideBecauseBackend,
        excludeFromUI,
        notes: ["Safe to run frequently; use first when debugging.", ...backendNote],
        uiSteps: ["Click Run and review warnings/errors.", "If files changed, verify via git diff."],
      });
    }

    if (/(lexicon|wikidata|harvest)/.test(p)) {
      return mk({
        category: "Lexicon & Data",
        group: "Mining & Harvesting",
        kind: "tool",
        visibility,
        hideByDefault: visibility === "debug" || hideBecauseBackend,
        excludeFromUI,
        notes: [
          "May write many JSON shards; keep git clean. Prefer running on a branch for large refreshes.",
          ...backendNote,
        ],
        uiSteps: ["Click Run and monitor output.", "Inspect generated artifacts and indices afterward."],
      });
    }

    if (/(ai_refiner)/.test(p)) {
      return mk({
        category: "AI Tools & Services",
        group: "Agents",
        kind: "tool",
        riskOverride: backend?.risk ?? "heavy",
        visibility,
        hideByDefault: true, // force hide-by-default for AI agents in tools/
        excludeFromUI,
        notes: ["AI tools may require credentials and can be costly; run on a branch.", ...backendNote],
        uiSteps: ["Confirm credentials/config.", "Click Run and monitor output carefully."],
      });
    }

    if (/(bootstrap_tier1)/.test(p)) {
      return mk({
        category: "Build System",
        group: "Tier Bootstrapping",
        kind: "tool",
        riskOverride: backend?.risk ?? "moderate",
        visibility,
        hideByDefault: visibility === "debug" || hideBecauseBackend,
        excludeFromUI,
        notes: ["Bootstraps Tier 1 scaffolding; may create or update code/artifacts.", ...backendNote],
        uiSteps: ["Click Run.", "Review console output and git diffs afterward."],
      });
    }

    return mk({
      category: "Tools",
      group: "Misc Tools",
      kind: "tool",
      visibility,
      hideByDefault: visibility === "debug" || hideBecauseBackend,
      excludeFromUI,
      notes: ["General-purpose tool script.", ...backendNote],
      uiSteps: ["Click Run and review console output."],
    });
  }

  if (p.startsWith("scripts/lexicon/")) {
    return mk({
      category: "Lexicon & Data",
      group: "Legacy Lexicon Scripts",
      kind: "script",
      statusOverride: "legacy",
      visibility,
      hideByDefault: true, // legacy scripts are always hidden by default
      excludeFromUI,
      notes: ["Legacy DB-era scripts (reference only unless DB pipeline exists)."],
      uiSteps: ["Open in Repo to confirm environment assumptions.", "Run only in the intended legacy environment."],
    });
  }

  if (p.startsWith("scripts/")) {
    if (p.includes("demo_")) {
      return mk({
        category: "Demos & Prototypes",
        group: "Demos",
        kind: "script",
        visibility,
        hideByDefault: true,
        excludeFromUI,
        notes: ["Local demos. Useful for manual validation."],
        uiSteps: ["Prefer running via CLI for interactive output."],
      });
    }

    if (p.includes("test_")) {
      return mk({
        category: "QA & Testing",
        group: "Diagnostic Scripts",
        kind: "script",
        statusOverride: status,
        visibility,
        hideByDefault: true,
        excludeFromUI,
        notes: ["Ad-hoc diagnostic scripts; prefer pytest for repeatable regression."],
        uiSteps: ["Open in Repo to confirm args; run from CLI when needed."],
      });
    }

    return mk({
      category: "Scripts",
      group: "Misc Scripts",
      kind: "script",
      visibility,
      hideByDefault: true,
      excludeFromUI,
      notes: ["Ad-hoc scripts; prefer tools/ or manage.py for standardized ops."],
      uiSteps: ["Open in Repo to confirm args; run from CLI when needed."],
    });
  }

  if (p.startsWith("utils/")) {
    if (isRunnableUtility(path)) {
      // Some runnable utils are power-user tools (AI), keep hidden by default.
      const hideBecausePowerUser = p.includes("seed_lexicon_ai") || p.includes("seed_lexicon");

      return mk({
        category: hideBecausePowerUser ? "AI Tools & Services" : "Lexicon & Data",
        group: hideBecausePowerUser ? "AI Utilities" : "Schema & Index",
        kind: "utility",
        visibility: hideBecausePowerUser ? "debug" : "default",
        hideByDefault: hideBecausePowerUser || hideBecauseBackend,
        excludeFromUI,
        riskOverride: backend?.risk, // if registry is more precise than path heuristics
        notes: hideBecausePowerUser
          ? ["AI utility may require credentials and can be costly; run on a branch.", ...backendNote]
          : ["Runnable utility (CLI). Often used in lexicon pipeline (schema/index/stats).", ...backendNote],
        uiSteps: hideBecausePowerUser
          ? ["Confirm credentials/config. Run and monitor output carefully."]
          : ["Run carefully; if it writes files, check git status and review diffs."],
      });
    }

    if (/(seed_lexicon|ai)/.test(p)) {
      return mk({
        category: "AI Tools & Services",
        group: "AI Utilities",
        kind: "utility",
        visibility,
        hideByDefault: true,
        excludeFromUI,
        riskOverride: backend?.risk,
        notes: ["AI utilities may require credentials and can be costly; run on a branch.", ...backendNote],
        uiSteps: ["Confirm credentials/config. Run and monitor output carefully."],
      });
    }

    return mk({
      category: "Libraries",
      group: "Utilities & Libraries",
      kind: "utility",
      visibility,
      hideByDefault: true,
      excludeFromUI,
      notes: ["Mostly library modules; not all are meant to be executed directly."],
      uiSteps: ["Use Open in Repo to confirm if it is executable."],
    });
  }

  if (p.startsWith("ai_services/")) {
    return mk({
      category: "AI Tools & Services",
      group: "Agents",
      kind: "agent",
      visibility,
      hideByDefault: true,
      excludeFromUI,
      riskOverride: backend?.risk,
      notes: ["AI services/agents may require credentials/config and can be costly. Run on a branch.", ...backendNote],
      uiSteps: ["Confirm credentials/config. Prefer invoking via backend service layer."],
    });
  }

  if (p.startsWith("nlg/")) {
    return mk({
      category: "Demos & Prototypes",
      group: "NLG",
      kind: "utility",
      visibility,
      hideByDefault: true,
      excludeFromUI,
      notes: ["NLG experiments and supporting modules."],
      uiSteps: ["Prefer CLI for interactive workflows."],
    });
  }

  if (p.startsWith("prototypes/")) {
    return mk({
      category: "Demos & Prototypes",
      group: "Experimental",
      kind: "prototype",
      statusOverride: "experimental",
      visibility,
      hideByDefault: true,
      excludeFromUI,
      notes: ["Experimental code. Not guaranteed stable."],
      uiSteps: ["Prefer CLI and isolate changes."],
    });
  }

  if (p.startsWith("tests/")) {
    let group = "Pytest";
    if (p.includes("smoke")) group = "Pytest • Smoke";
    else if (p.includes("gf")) group = "Pytest • GF Engine";
    else if (p.includes("lexicon")) group = "Pytest • Lexicon";
    else if (p.includes("frames")) group = "Pytest • Frames";
    else if (p.includes("api")) group = "Pytest • API";
    else if (p.includes("integration")) group = "Pytest • Integration";

    return mk({
      category: "QA & Testing",
      group,
      kind: "test",
      visibility,
      hideByDefault: true,
      excludeFromUI,
      notes: ["Prefer running via pytest for consistent, repeatable results."],
      uiSteps: ["Copy the pytest command from CLI equivalents and run locally/CI."],
    });
  }

  return mk({
    category: "Other",
    group: "Other",
    kind: "utility",
    visibility,
    hideByDefault: visibility === "debug" || hideBecauseBackend,
    excludeFromUI,
    notes: ["Unclassified item.", ...backendNote],
    uiSteps: ["Open in Repo for details."],
  });
};

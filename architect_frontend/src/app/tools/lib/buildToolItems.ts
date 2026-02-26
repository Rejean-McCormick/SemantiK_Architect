// architect_frontend/src/app/tools/lib/buildToolItems.ts
import { INVENTORY } from "../inventory";
import {
  BACKEND_TOOL_REGISTRY,
  type BackendToolId,
  type BackendToolMeta, // ✅ use the exported meta type (includes parameterDocs, hidden, etc.)
  type Risk,
  type ToolParameter,
} from "../backendRegistry";
import { TOOL_DESCRIPTIONS, defaultDesc } from "../descriptions";
import {
  classify,
  cliFromPath,
  riskFromPath,
  statusFromPath,
  titleFromPath,
  type Status,
  type ToolKind,
} from "../classify";

/**
 * Canonical ToolItem type for the Tools UI.
 * Import this everywhere (ToolListPanel, ToolDetailsCard, page.tsx, etc.)
 * so you don't end up with drifting definitions in multiple files.
 */
export type ToolItem = {
  key: string;
  title: string;
  path: string; // repo-relative (normalized with forward slashes)
  category: string;
  group: string;
  kind: ToolKind;
  risk: Risk;
  status: Status;

  desc?: string;

  cli: string[];
  notes: string[];
  uiSteps: string[];

  wiredToolId?: BackendToolId;
  toolIdGuess: string;
  commandPreview?: string;

  hiddenInNormalMode?: boolean;
  parameterDocs?: ToolParameter[];
};

type BuildToolItemsOpts = {
  /**
   * If true, items are returned sorted. Default true.
   * (If you sort elsewhere, you can disable to save work.)
   */
  sort?: boolean;
};

const collator = new Intl.Collator(undefined, { sensitivity: "base", numeric: true });

function normalizePath(p: string) {
  // Defensive: accept backslashes (windows) but standardize to repo-style.
  return (p || "").replace(/\\/g, "/").trim();
}

/** Stable, URL-safe-ish key used by docsHref() and selection logic */
export function toolKeyFromPath(path: string) {
  const p = normalizePath(path);
  return `file-${p.replace(/[^a-zA-Z0-9]+/g, "-")}`;
}

function basenameNoExt(path: string) {
  const p = normalizePath(path);
  const base = p.split("/").pop() || p;
  return base.replace(/\.[^.]+$/, "");
}

function toolIdGuessFromPath(path: string, wiredToolId?: BackendToolId) {
  return wiredToolId || basenameNoExt(path);
}

function mergeUniqueStrings(...lists: Array<readonly (string | undefined)[]>) {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const list of lists) {
    for (const s of list) {
      const v = (s || "").trim();
      if (!v) continue;
      if (seen.has(v)) continue;
      seen.add(v);
      out.push(v);
    }
  }
  return out;
}

function isRisk(x: unknown): x is Risk {
  return x === "safe" || x === "moderate" || x === "heavy";
}

function coerceRisk(...candidates: unknown[]): Risk {
  for (const c of candidates) {
    if (isRisk(c)) return c;
  }
  return "safe";
}

function cliEquivalents(path: string): string[] {
  const p = normalizePath(path);

  // preserve special-cases
  if (p === "manage.py") {
    return ["python manage.py start", "python manage.py build", "python manage.py doctor"];
  }
  if (p === "builder/orchestrator.py") {
    return ["python builder/orchestrator.py", "python manage.py build"];
  }
  return cliFromPath(p);
}

// -----------------------------------------------------------------------------
// Module-level caches (built once)
// -----------------------------------------------------------------------------
const TOOL_ID_BY_PATH: Record<string, BackendToolId> = (() => {
  const out: Record<string, BackendToolId> = {};
  const entries = Object.entries(BACKEND_TOOL_REGISTRY) as [BackendToolId, BackendToolMeta][];

  for (const [toolId, meta] of entries) {
    const p = normalizePath(meta.path);
    // keep first mapping if duplicates ever exist
    if (!out[p]) out[p] = toolId;
  }
  return out;
})();

/**
 * Inventory path sources in the same order as your original page.tsx.
 * Keeping order stable helps with debugging and predictable outputs.
 */
function collectInventoryPaths(): string[] {
  const seen = new Set<string>();
  const all: string[] = [];

  const addMany = (arr?: readonly string[] | string[]) => {
    if (!arr) return;
    for (let i = 0; i < arr.length; i++) {
      const raw = arr[i];
      if (!raw) continue;
      const p = normalizePath(raw);
      if (!p) continue;
      if (seen.has(p)) continue;
      seen.add(p);
      all.push(p);
    }
  };

  addMany(INVENTORY.root_entrypoints as readonly string[]);
  addMany(INVENTORY.gf as readonly string[]);
  addMany(INVENTORY.tools?.root || []);
  addMany(INVENTORY.tools?.everything_matrix || []);
  addMany(INVENTORY.tools?.qa || []);
  addMany(INVENTORY.tools?.debug || []);
  addMany(INVENTORY.tools?.health || []);
  addMany(INVENTORY.tools?.lexicon || []);

  addMany(INVENTORY.scripts?.root || []);
  addMany(INVENTORY.scripts?.lexicon || []);
  addMany(INVENTORY.utils as readonly string[]);
  addMany(INVENTORY.ai_services as readonly string[]);
  addMany(INVENTORY.nlg as readonly string[]);
  addMany(INVENTORY.prototypes as readonly string[]);
  addMany(INVENTORY.tests?.root || []);
  addMany(INVENTORY.tests?.http_api_legacy || []);
  addMany(INVENTORY.tests?.adapters_core_integration || []);

  return all;
}

/**
 * Build ToolItem[] from the inventory snapshot plus backend wired registry.
 * Pure and cheap enough to use in useMemo(() => buildToolItems(), []).
 */
export function buildToolItems(opts: BuildToolItemsOpts = {}): ToolItem[] {
  const shouldSort = opts.sort !== false;

  const rootEntrypoints = ((INVENTORY.root_entrypoints as readonly string[]) ?? []).map(normalizePath);

  // 1) Items from inventory snapshot
  const allPaths = collectInventoryPaths();
  const presentPaths = new Set(allPaths);

  const out: ToolItem[] = [];

  for (let i = 0; i < allPaths.length; i++) {
    const path = allPaths[i];

    const cls = classify(rootEntrypoints, path);
    if (cls.excludeFromUI) continue;

    const wiredToolId = TOOL_ID_BY_PATH[path];
    const wiredMeta: BackendToolMeta | undefined = wiredToolId ? BACKEND_TOOL_REGISTRY[wiredToolId] : undefined;
    const wired = Boolean(wiredToolId);

    const status = (cls.statusOverride ?? statusFromPath(path)) as Status;
    const risk = coerceRisk(cls.riskOverride, wiredMeta?.risk, riskFromPath(path));

    const desc = TOOL_DESCRIPTIONS[path] ?? defaultDesc(path);

    const toolIdGuess = toolIdGuessFromPath(path, wiredToolId);

    const commandPreview = wiredMeta?.cmd?.join(" ").trim() || undefined;

    // For wired tools, show backend command first, then local equivalents (deduped).
    const cli = wired
      ? mergeUniqueStrings([commandPreview], cliEquivalents(path))
      : cliEquivalents(path);

    const notes = mergeUniqueStrings(
      cls.notes ?? [],
      [
        wired
          ? "Wired: Run is enabled (backend allowlist)."
          : "Not wired: shown for reference only (not in backend allowlist).",
      ],
      status === "legacy" ? ["Legacy/compat: may require endpoint or pipeline updates."] : [],
      status === "experimental" ? ["Experimental: not guaranteed stable."] : [],
      status === "internal" ? ["Internal module: usually not executed directly."] : []
    );

    out.push({
      key: toolKeyFromPath(path),
      title: wiredMeta?.title ?? titleFromPath(path),
      path,
      category: wiredMeta?.category ?? cls.category,
      group: wiredMeta?.group ?? cls.group,
      kind: cls.kind,
      risk,
      status,
      desc,
      cli,
      notes,
      uiSteps: cls.uiSteps,
      wiredToolId,
      toolIdGuess,
      commandPreview,
      hiddenInNormalMode: cls.hideByDefault || false,
      parameterDocs: wiredMeta?.parameterDocs || [], // ✅ now recognized
    });
  }

  // 2) Backend-wired tools missing from inventory snapshot
  const backendEntries = Object.entries(BACKEND_TOOL_REGISTRY) as [BackendToolId, BackendToolMeta][];

  for (const [toolId, meta] of backendEntries) {
    const path = normalizePath(meta.path);
    if (presentPaths.has(path)) continue;

    const cls = classify(rootEntrypoints, path);
    if (cls.excludeFromUI) continue;

    const desc = TOOL_DESCRIPTIONS[path] ?? `${meta.title} (backend-wired tool).`;
    const status = (cls.statusOverride ?? statusFromPath(path)) as Status;
    const risk = coerceRisk(meta.risk, cls.riskOverride, riskFromPath(path));

    const commandPreview = meta.cmd.join(" ").trim();

    const notes = mergeUniqueStrings(
      cls.notes ?? [],
      [
        "Wired: Run is enabled (backend allowlist).",
        "This tool is wired but missing from the current inventory snapshot.",
      ],
      status === "legacy" ? ["Legacy/compat: may require endpoint or pipeline updates."] : [],
      status === "experimental" ? ["Experimental: not guaranteed stable."] : [],
      status === "internal" ? ["Internal module: usually not executed directly."] : []
    );

    out.push({
      key: `wired-${toolId}`,
      title: meta.title,
      path,
      category: meta.category ?? cls.category,
      group: meta.group ?? cls.group,
      kind: cls.kind,
      risk,
      status,
      desc,
      cli: mergeUniqueStrings([commandPreview], cliEquivalents(path)),
      notes,
      uiSteps:
        cls.uiSteps?.length
          ? cls.uiSteps
          : ["Select the tool.", "Optionally add args.", "Click Run and review output."],
      wiredToolId: toolId,
      toolIdGuess: toolId,
      commandPreview,
      hiddenInNormalMode: cls.hideByDefault || false,
      parameterDocs: meta.parameterDocs || [], // ✅ now recognized
    });
  }

  if (shouldSort) {
    out.sort((a, b) => {
      const c1 = collator.compare(a.category, b.category);
      if (c1) return c1;
      const c2 = collator.compare(a.group, b.group);
      if (c2) return c2;
      return collator.compare(a.title, b.title);
    });
  }

  return out;
}
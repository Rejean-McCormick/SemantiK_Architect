// architect_frontend/src/app/tools/page.tsx
"use client";

import React, {
  useCallback,
  useDeferredValue,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Terminal,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  PlugZap,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

import { INVENTORY } from "./inventory";
import ToolListPanel, { type GroupedTools } from "./components/ToolListPanel";
import ToolDetailsCard from "./components/ToolDetailsCard";
import ConsoleCard from "./components/ConsoleCard";

import { buildToolItems, type ToolItem } from "./lib/buildToolItems";
import { useToolRunner } from "./hooks/useToolRunner";
import { normalizeApiV1, normalizeRepoUrl } from "./utils";
import type { HealthReady } from "./types";

// ----------------------------------------------------------------------------
// API base normalization
// ----------------------------------------------------------------------------
const RAW_API_BASE =
  process.env.NEXT_PUBLIC_ARCHITECT_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000";

const API_V1 = normalizeApiV1(RAW_API_BASE);
const REPO_URL = normalizeRepoUrl(process.env.NEXT_PUBLIC_REPO_URL || "");

// ----------------------------------------------------------------------------
// Local persistence
// ----------------------------------------------------------------------------
const LS_PREFS_KEY = "tools_dashboard_prefs_v3";
const LS_ARGS_KEY = "tools_dashboard_args_v2";

// ----------------------------------------------------------------------------
// LocalStorage hook (hydrates after mount; persists on change)
// ----------------------------------------------------------------------------
function safeJsonParse<T>(
  s: string
): { ok: true; value: T } | { ok: false; error: unknown } {
  try {
    return { ok: true, value: JSON.parse(s) as T };
  } catch (e) {
    return { ok: false, error: e };
  }
}

function useLocalStorageState<T>(key: string, initialValue: T) {
  const [value, setValue] = useState<T>(initialValue);
  const hydratedRef = useRef(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(key);
      if (raw) {
        const parsed = safeJsonParse<T>(raw);
        if (parsed.ok) setValue(parsed.value);
      }
    } catch {
      // ignore
    } finally {
      hydratedRef.current = true;
    }
  }, [key]);

  useEffect(() => {
    if (!hydratedRef.current) return;
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // ignore
    }
  }, [key, value]);

  return [value, setValue] as const;
}

// ----------------------------------------------------------------------------
// UI helpers
// ----------------------------------------------------------------------------
function healthBadge(label: string, value?: unknown) {
  const s =
    typeof value === "string"
      ? value
      : value == null
      ? undefined
      : String(value);

  const v = (s || "").toLowerCase();
  const ok = v === "ok" || v === "ready" || v === "up" || v === "healthy";
  const bad = v === "down" || v === "unhealthy" || v === "error" || v === "fail";

  return (
    <span className="inline-flex items-center gap-1 text-xs">
      {ok ? (
        <CheckCircle2 className="w-3 h-3 text-green-500" />
      ) : bad ? (
        <XCircle className="w-3 h-3 text-red-500" />
      ) : (
        <AlertTriangle className="w-3 h-3 text-amber-500" />
      )}
      <span className="text-slate-600">{label}:</span>
      <span className="font-mono text-slate-700">{s ?? "unknown"}</span>
    </span>
  );
}

const collator = new Intl.Collator(undefined, {
  sensitivity: "base",
  numeric: true,
});

function groupItems(items: ToolItem[]): GroupedTools {
  const byCat: GroupedTools = new Map();

  for (const it of items) {
    if (!byCat.has(it.category)) byCat.set(it.category, new Map());
    const byGroup = byCat.get(it.category)!;

    if (!byGroup.has(it.group)) byGroup.set(it.group, []);
    byGroup.get(it.group)!.push(it);
  }

  // Stable rendering (group-level sort; ToolListPanel sorts cat/group labels)
  for (const [, byGroup] of byCat) {
    for (const [, arr] of byGroup) {
      arr.sort((a, b) => collator.compare(a.title, b.title));
    }
  }

  return byCat;
}

// ----------------------------------------------------------------------------
// Page
// ----------------------------------------------------------------------------
export default function ToolsDashboard() {
  // Persisted prefs
  const [prefs, setPrefs] = useLocalStorageState(LS_PREFS_KEY, {
    powerUser: false,
    showLegacy: true,
    showTests: true,
    showInternal: false,
    wiredOnly: false,
    showHeavy: true,
    leftCollapsed: false,
    autoScrollConsole: true,
    dryRun: false,
  });

  const powerUser = Boolean(prefs.powerUser);
  const showLegacy = Boolean(prefs.showLegacy);
  const showTests = Boolean(prefs.showTests);
  const showInternal = Boolean(prefs.showInternal);
  const wiredOnly = Boolean(prefs.wiredOnly);
  const showHeavy = Boolean(prefs.showHeavy);
  const leftCollapsed = Boolean(prefs.leftCollapsed);
  const autoScrollConsole = Boolean(prefs.autoScrollConsole);
  const dryRun = Boolean(prefs.dryRun);

  const setPref = useCallback(
    (k: keyof typeof prefs, v: boolean) => setPrefs((p) => ({ ...p, [k]: v })),
    [setPrefs]
  );

  // Persisted args
  const [argsByToolId, setArgsByToolId] = useLocalStorageState<
    Record<string, string>
  >(LS_ARGS_KEY, {});

  // UI state
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);

  // Build inventory-derived + backend-wired items once
  const items = useMemo(() => buildToolItems({ sort: true }), []);
  const wiredCount = useMemo(
    () => items.filter((x) => Boolean(x.wiredToolId)).length,
    [items]
  );

  // Filtering model (normal mode forces wired-only)
  const filteredItems = useMemo(() => {
    const q = deferredQuery.trim().toLowerCase();

    const effectiveWiredOnly = powerUser ? wiredOnly : true;
    const effectiveShowLegacy = powerUser ? showLegacy : false;
    const effectiveShowTests = powerUser ? showTests : false;
    const effectiveShowInternal = powerUser ? showInternal : false;

    // Important: normal mode does NOT hide heavy tools
    const effectiveShowHeavy = powerUser ? showHeavy : true;

    return items.filter((it) => {
      if (!effectiveShowHeavy && it.risk === "heavy") return false;

      if (effectiveWiredOnly && !it.wiredToolId) return false;
      if (!effectiveShowLegacy && it.status === "legacy") return false;
      if (!effectiveShowTests && it.kind === "test") return false;
      if (!effectiveShowInternal && it.status === "internal") return false;

      if (!powerUser && it.hiddenInNormalMode) return false;

      if (!q) return true;

      return (
        it.title.toLowerCase().includes(q) ||
        it.path.toLowerCase().includes(q) ||
        it.category.toLowerCase().includes(q) ||
        it.group.toLowerCase().includes(q) ||
        it.toolIdGuess.toLowerCase().includes(q) ||
        (it.wiredToolId
          ? String(it.wiredToolId).toLowerCase().includes(q)
          : false)
      );
    });
  }, [
    deferredQuery,
    items,
    powerUser,
    showHeavy,
    showInternal,
    showLegacy,
    showTests,
    wiredOnly,
  ]);

  const grouped = useMemo(() => groupItems(filteredItems), [filteredItems]);

  const selected = useMemo(() => {
    if (!selectedKey) return null;
    return items.find((x) => x.key === selectedKey) || null;
  }, [items, selectedKey]);

  const selectedToolId = selected?.wiredToolId ? String(selected.wiredToolId) : null;

  // If selected becomes filtered out, clear it
  useEffect(() => {
    if (!selectedKey) return;
    const stillVisible = filteredItems.some((x) => x.key === selectedKey);
    if (!stillVisible) setSelectedKey(null);
  }, [filteredItems, selectedKey]);

  // ----------------------------------------------------------------------------
  // Health
  // ----------------------------------------------------------------------------
  const [health, setHealth] = useState<HealthReady | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);

  const refreshHealth = useCallback(async () => {
    const controller = new AbortController();
    setHealthLoading(true);
    try {
      const res = await fetch(`${API_V1}/health/ready`, {
        cache: "no-store",
        signal: controller.signal,
      });
      const text = await res.text();
      const parsed = safeJsonParse<HealthReady>(text);
      setHealth(parsed.ok ? parsed.value : null);
    } catch {
      setHealth(null);
    } finally {
      setHealthLoading(false);
    }
    return () => controller.abort();
  }, []);

  useEffect(() => {
    let cleanup: void | (() => void);
    (async () => {
      cleanup = await refreshHealth();
    })();
    return () => {
      if (cleanup) cleanup();
    };
  }, [refreshHealth]);

  // ----------------------------------------------------------------------------
  // Runner (console + visualizer + cancel + last bundle)
  // ----------------------------------------------------------------------------
  const {
    consoleOutput,
    appendConsole,
    clear,
    cancelRun,
    runTool: runToolCore,
    activeToolId,
    lastStatus,
    lastResponseJson,
    visualData,
    setVisualData,
  } = useToolRunner({
    apiV1: API_V1,
    initialConsole:
      `// Tools Command Center\n` +
      `// Inventory v${INVENTORY.version} (generated ${INVENTORY.generated_on})\n` +
      `// API: ${API_V1}\n` +
      `// Normal mode shows only backend-wired runnable tools.\n` +
      `// Enable Power user (debug) to reveal the full inventory.\n`,
  });

  const runFromItem = useCallback(
    async (it: ToolItem) => {
      if (!it.wiredToolId) return;
      const toolId = String(it.wiredToolId);
      const argsStr = argsByToolId[toolId] || "";

      // If user typed --dry / --dry-run in args, treat it as dry-run too.
      const dryRunFromArgs = /(^|\s)--dry(?:-run)?(\s|$)/.test(argsStr);
      const effectiveDryRun = dryRun || dryRunFromArgs;

      const res = await runToolCore(
        { title: it.title, risk: it.risk, wiredToolId: toolId, kind: it.kind },
        argsStr,
        effectiveDryRun
      );

      if (!res && !toolId) {
        appendConsole([`[ERROR] "${it.title}" is not wired.`], true);
      }
    },
    [appendConsole, argsByToolId, dryRun, runToolCore]
  );

  // ----------------------------------------------------------------------------
  // Render
  // ----------------------------------------------------------------------------
  const visibleCount = filteredItems.length;

  return (
    <div className="container mx-auto p-6 max-w-7xl space-y-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-3">
          <Terminal className="w-8 h-8 text-slate-700 dark:text-slate-300" />
          Tools Command Center
        </h1>
        <p className="text-slate-500 dark:text-slate-400">
          Inventory-driven tools browser (v{INVENTORY.version},{" "}
          {INVENTORY.generated_on}).{" "}
          {!powerUser ? (
            <>Normal mode shows only backend-wired runnable tools.</>
          ) : (
            <>
              Power user mode reveals the full inventory (including non-wired,
              tests, internal, legacy).
            </>
          )}
        </p>
      </div>

      {/* Controls */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <PlugZap className="w-4 h-4 text-slate-500" />
            Interface
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            <div className="lg:col-span-2">
              <div className="text-xs text-slate-500 mb-1">Search</div>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by name, path, category, tool_id…"
                className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-200"
              />
            </div>

            <div className="flex items-end gap-3 flex-wrap">
              <label className="flex items-center gap-2 text-sm text-slate-700 font-medium">
                <input
                  type="checkbox"
                  checked={powerUser}
                  onChange={(e) => setPref("powerUser", e.target.checked)}
                />
                Power user (debug)
              </label>

              <label className="flex items-center gap-2 text-sm text-slate-700 font-medium">
                <input
                  type="checkbox"
                  checked={dryRun}
                  onChange={(e) => setPref("dryRun", e.target.checked)}
                />
                Dry run
              </label>

              {powerUser ? (
                <div className="flex items-center gap-3 flex-wrap">
                  <label className="flex items-center gap-2 text-sm text-slate-600">
                    <input
                      type="checkbox"
                      checked={wiredOnly}
                      onChange={(e) => setPref("wiredOnly", e.target.checked)}
                    />
                    Wired only
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-600">
                    <input
                      type="checkbox"
                      checked={showLegacy}
                      onChange={(e) => setPref("showLegacy", e.target.checked)}
                    />
                    Show legacy
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-600">
                    <input
                      type="checkbox"
                      checked={showTests}
                      onChange={(e) => setPref("showTests", e.target.checked)}
                    />
                    Show tests
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-600">
                    <input
                      type="checkbox"
                      checked={showInternal}
                      onChange={(e) => setPref("showInternal", e.target.checked)}
                    />
                    Show internal
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-600">
                    <input
                      type="checkbox"
                      checked={showHeavy}
                      onChange={(e) => setPref("showHeavy", e.target.checked)}
                    />
                    Show heavy
                  </label>
                </div>
              ) : (
                <span className="text-xs text-slate-400">
                  (advanced filters hidden)
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="text-xs text-slate-500">
              API: <span className="font-mono">{API_V1}</span> • Visible:{" "}
              <span className="font-mono">{visibleCount}</span> /{" "}
              <span className="font-mono">{items.length}</span> • Wired tools:{" "}
              <span className="font-mono">{wiredCount}</span>
              {REPO_URL ? (
                <>
                  {" "}
                  • Repo: <span className="font-mono">{REPO_URL}</span>
                </>
              ) : (
                <>
                  {" "}
                  • Set <span className="font-mono">NEXT_PUBLIC_REPO_URL</span>{" "}
                  to enable file links.
                </>
              )}
              {" "}
              • Mode: <span className="font-mono">{dryRun ? "dry-run" : "live"}</span>
            </div>

            <div className="flex items-center gap-3">
              <span className="inline-flex items-center gap-2 text-xs">
                {healthBadge("broker", health?.broker)}
                {healthBadge("storage", health?.storage)}
                {healthBadge("engine", health?.engine)}
              </span>
              <Button
                variant="outline"
                size="sm"
                className="h-8"
                onClick={refreshHealth}
                disabled={healthLoading}
              >
                {healthLoading ? (
                  <span className="inline-flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" /> Checking
                  </span>
                ) : (
                  "Refresh health"
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-280px)]">
        {/* LEFT: Tool list */}
        <div
          className={`${
            leftCollapsed ? "lg:col-span-0 lg:hidden" : "lg:col-span-1"
          } overflow-y-auto pr-2 pb-10`}
        >
          <ToolListPanel
            grouped={grouped}
            selectedKey={selectedKey}
            activeToolId={activeToolId}
            powerUser={powerUser}
            onSelect={setSelectedKey}
            onRun={runFromItem}
          />
        </div>

        {/* RIGHT: Details + Console */}
        <div
          className={`${
            leftCollapsed ? "lg:col-span-3" : "lg:col-span-2"
          } flex flex-col h-full gap-4`}
        >
          <ToolDetailsCard
            selected={selected}
            powerUser={powerUser}
            leftCollapsed={leftCollapsed}
            onToggleLeftCollapsed={() =>
              setPref("leftCollapsed", !leftCollapsed)
            }
            activeToolId={activeToolId}
            runTool={runFromItem}
            argsByToolId={argsByToolId}
            setArgsByToolId={setArgsByToolId}
            repoUrl={REPO_URL}
          />

          {/* Console */}
          <ConsoleCard
            consoleOutput={consoleOutput}
            lastStatus={lastStatus}
            lastResponseJson={lastResponseJson}
            activeToolId={activeToolId}
            selectedToolId={selectedToolId ?? undefined}
            autoScroll={autoScrollConsole}
            onAutoScrollChange={(next) => setPref("autoScrollConsole", next)}
            onCancel={cancelRun}
            onClear={clear}
            visualData={visualData}
            onCloseVisualizer={() => setVisualData(null)}
            visualizerHeight={500}
          />
        </div>
      </div>
    </div>
  );
}

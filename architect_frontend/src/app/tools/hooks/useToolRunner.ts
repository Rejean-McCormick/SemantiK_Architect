// architect_frontend/src/app/tools/hooks/useToolRunner.ts
"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { parseCliArgs } from "../utils";
import { extractJsonFromRun, formatRunForConsole, runToolOnce } from "../lib/toolRun";
import type { ToolRisk, ToolRunResponse } from "../types";

// ----------------------------------------------------------------------------
// Types
// ----------------------------------------------------------------------------
export type RunnableTool = {
  title: string;
  risk: ToolRisk;
  wiredToolId?: string | null;

  // Optional: hook can auto-detect visualizer output
  kind?: string;
};

export type ToolRunnerStatus = "success" | "error" | null;

export type UseToolRunnerOptions = {
  apiV1: string;

  parseArgs?: (argsStr: string) => string[];
  confirmRisk?: boolean;

  visualizerToolId?: string;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  pickVisualizerTree?: (json: any) => any | null;

  initialConsole?: string;
  defaultDryRun?: boolean;

  /**
   * Client-side timeout (ms) passed through to runToolOnce (if supported).
   * If your lib/toolRun.ts ignores it, it’s harmless.
   */
  timeoutMs?: number;

  /**
   * Prevent unbounded console growth. When exceeded, trims the oldest content.
   * Default: 750k chars (roughly ~0.75MB in ASCII-ish output).
   */
  maxConsoleChars?: number;
};

// ----------------------------------------------------------------------------
// Small local helpers
// ----------------------------------------------------------------------------
function safeJsonParse<T>(s: string): { ok: true; value: T } | { ok: false; error: unknown } {
  try {
    return { ok: true, value: JSON.parse(s) as T };
  } catch (e) {
    return { ok: false, error: e };
  }
}

function tryParseJsonFromText(text: string) {
  const t = (text ?? "").trim();
  if (!t) return { ok: false as const, value: null };

  const candidates: string[] = [t];

  const firstObj = t.indexOf("{");
  const lastObj = t.lastIndexOf("}");
  if (firstObj >= 0 && lastObj > firstObj) candidates.push(t.slice(firstObj, lastObj + 1));

  const firstArr = t.indexOf("[");
  const lastArr = t.lastIndexOf("]");
  if (firstArr >= 0 && lastArr > firstArr) candidates.push(t.slice(firstArr, lastArr + 1));

  for (const c of candidates) {
    const parsed = safeJsonParse<unknown>(c);
    if (parsed.ok) return { ok: true as const, value: parsed.value };
  }
  return { ok: false as const, value: null };
}

function isAbortError(e: unknown) {
  const err = e as { name?: string; message?: string };
  return err?.name === "AbortError" || /aborted/i.test(err?.message || "");
}

function parseBoolValueFromFlagToken(token: string): boolean | null {
  // supports: --dry=true, --dry=false, --dry-run=1, etc.
  const eq = token.indexOf("=");
  if (eq < 0) return null;
  const v = token.slice(eq + 1).trim().toLowerCase();
  if (["1", "true", "yes", "y", "on"].includes(v)) return true;
  if (["0", "false", "no", "n", "off"].includes(v)) return false;
  return null;
}

function extractDryRunFromArgs(argsIn: string[]): { args: string[]; dryFromArgs: boolean | null } {
  // Allow selecting dry-run via args string even if caller doesn’t pass dryRun param.
  // Recognizes: --dry, --dry-run, --dry=true/false, --dry-run=true/false, --no-dry, --no-dry-run
  let dryFromArgs: boolean | null = null;
  const out: string[] = [];

  for (const tok of argsIn) {
    const t = tok.trim();
    if (!t) continue;

    const lower = t.toLowerCase();

    const isDry =
      lower === "--dry" ||
      lower === "--dry-run" ||
      lower.startsWith("--dry=") ||
      lower.startsWith("--dry-run=");
    const isNoDry =
      lower === "--no-dry" ||
      lower === "--no-dry-run" ||
      lower.startsWith("--no-dry=") ||
      lower.startsWith("--no-dry-run=");

    if (isDry) {
      const v = parseBoolValueFromFlagToken(lower);
      dryFromArgs = v ?? true; // bare --dry => true
      continue; // strip from args; we’ll send dry_run via request body
    }

    if (isNoDry) {
      const v = parseBoolValueFromFlagToken(lower);
      dryFromArgs = v ?? false; // bare --no-dry => false
      continue; // strip
    }

    out.push(tok);
  }

  return { args: out, dryFromArgs };
}

// ----------------------------------------------------------------------------
// Hook
// ----------------------------------------------------------------------------
export function useToolRunner(opts: UseToolRunnerOptions) {
  const {
    apiV1,
    parseArgs: parseArgsOpt,
    confirmRisk = true,
    visualizerToolId = "visualize_ast",
    pickVisualizerTree = (j) => (j as any)?.tree ?? (j as any)?.ast ?? null,
    initialConsole = "// Console ready.\n",
    defaultDryRun = false,
    timeoutMs,
    maxConsoleChars = 750_000,
  } = opts;

  const parseArgs = parseArgsOpt ?? parseCliArgs;

  // Console buffering in a ref avoids React holding multiple big string copies.
  const consoleTextRef = useRef<string>(initialConsole);
  const [consoleVersion, setConsoleVersion] = useState(0);

  const bumpConsole = useCallback(() => setConsoleVersion((v) => v + 1), []);

  const appendConsole = useCallback(
    (lines: string | string[], leadingBlank = true) => {
      const arr = Array.isArray(lines) ? lines : [lines];
      const prefix = leadingBlank ? "\n" : "";
      let next = consoleTextRef.current + prefix + arr.join("\n");

      if (maxConsoleChars > 0 && next.length > maxConsoleChars) {
        const keep = Math.max(0, maxConsoleChars - 120);
        next = "[… console trimmed …]\n" + next.slice(Math.max(0, next.length - keep));
      }

      consoleTextRef.current = next;
      bumpConsole();
    },
    [bumpConsole, maxConsoleChars]
  );

  const setConsole = useCallback(
    (text: string) => {
      consoleTextRef.current = text;
      bumpConsole();
    },
    [bumpConsole]
  );

  const consoleOutput = useMemo(() => consoleTextRef.current, [consoleVersion]);

  // Visualizer state
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [visualData, setVisualData] = useState<any>(null);

  // Runner state
  const [activeToolId, setActiveToolId] = useState<string | null>(null);
  const [lastStatus, setLastStatus] = useState<ToolRunnerStatus>(null);

  // Keep last response as object in a ref; stringify only when it changes.
  const lastResponseRef = useRef<ToolRunResponse | null>(null);
  const [lastResponseVersion, setLastResponseVersion] = useState(0);

  const lastResponseJson = useMemo(() => {
    if (!lastResponseRef.current) return null;
    try {
      return JSON.stringify(lastResponseRef.current, null, 2);
    } catch {
      return null;
    }
  }, [lastResponseVersion]);

  // Abort handling + concurrency guard
  const abortRef = useRef<AbortController | null>(null);
  const runSeqRef = useRef(0);

  // Prevent double “aborted” log lines (cancel button + catch block)
  const cancelledSeqRef = useRef<number | null>(null);

  const cancelRun = useCallback(() => {
    if (!abortRef.current) return;

    cancelledSeqRef.current = runSeqRef.current;

    abortRef.current.abort();
    abortRef.current = null;

    setActiveToolId(null);
    appendConsole(["[CANCEL] Abort requested by user."], true);
  }, [appendConsole]);

  const clear = useCallback(() => {
    runSeqRef.current += 1;

    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }

    cancelledSeqRef.current = null;

    setConsole("// Console cleared.\n");
    setVisualData(null);
    setLastStatus(null);
    setActiveToolId(null);

    lastResponseRef.current = null;
    setLastResponseVersion((v) => v + 1);
  }, [setConsole]);

  const runTool = useCallback(
    async (tool: RunnableTool, argsStr: string, dryRun?: boolean): Promise<ToolRunResponse | null> => {
      const toolId = tool.wiredToolId || null;
      if (!toolId) {
        appendConsole([`[ERROR] Tool "${tool.title}" has no wiredToolId.`], true);
        setLastStatus("error");
        return null;
      }

      setVisualData(null);

      let rawArgs: string[] = [];
      try {
        rawArgs = parseArgs(argsStr || "");
      } catch (e) {
        setLastStatus("error");
        appendConsole([`[ARGS ERROR] ${(e as Error)?.message || String(e)}`], true);
        return null;
      }

      // NEW: allow `--dry`/`--dry-run` in args string to control dry_run mode
      const { args, dryFromArgs } = extractDryRunFromArgs(rawArgs);

      // Precedence: explicit param > args flag > default
      const effectiveDryRun = Boolean(dryRun ?? dryFromArgs ?? defaultDryRun);

      if (confirmRisk && (tool.risk === "moderate" || tool.risk === "heavy")) {
        const ok = window.confirm(
          `Run "${tool.title}"?\n\nRisk: ${tool.risk.toUpperCase()}\nTool ID: ${toolId}\nArgs: ${args.join(" ")}${
            effectiveDryRun ? "\nMode: DRY RUN" : ""
          }\n\nProceed?`
        );
        if (!ok) return null;
      }

      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const runSeq = ++runSeqRef.current;
      cancelledSeqRef.current = null;

      setActiveToolId(toolId);
      setLastStatus(null);

      lastResponseRef.current = null;
      setLastResponseVersion((v) => v + 1);

      appendConsole(
        [
          `> Executing: ${tool.title}`,
          `  tool_id=${toolId}`,
          `  args=${args.join(" ")}`,
          `  dry_run=${effectiveDryRun ? "true" : "false"}`,
          `----------------------------------------`,
        ],
        true
      );

      // Inject dry_run=true into JSON body by wrapping fetchImpl.
      // (Also strips --dry/--dry-run tokens from args so the backend only sees one source of truth.)
      const fetchImpl =
        effectiveDryRun
          ? ((input: RequestInfo | URL, init?: RequestInit) => {
              try {
                const body = init?.body;
                if (typeof body === "string") {
                  const parsed = safeJsonParse<any>(body);
                  if (parsed.ok && parsed.value && typeof parsed.value === "object") {
                    const nextBody = JSON.stringify({ ...parsed.value, dry_run: true });
                    return fetch(input, { ...init, body: nextBody });
                  }
                }
              } catch {
                // fall through
              }
              return fetch(input, init);
            }) satisfies typeof fetch
          : undefined;

      try {
        const result = await runToolOnce({
          apiV1,
          toolId,
          args,
          signal: controller.signal,
          timeoutMs,
          fetchImpl,
        });

        if (runSeq !== runSeqRef.current) return null;

        lastResponseRef.current = result.normalized;
        setLastResponseVersion((v) => v + 1);

        setLastStatus(result.normalized.success ? "success" : "error");
        appendConsole(formatRunForConsole(result.normalized, result.clientDurationMs), true);

        const shouldVisualize = toolId === visualizerToolId || tool.kind === "visualizer";
        if (shouldVisualize) {
          const outputText = extractJsonFromRun(result.normalized) || "";
          const visTry = tryParseJsonFromText(outputText);

          if (visTry.ok) {
            const tree = pickVisualizerTree(visTry.value);
            if (tree) setVisualData(tree);
            else appendConsole(["[VISUALIZER] JSON parsed, but no tree found."], true);
          } else if (outputText) {
            appendConsole(["[VISUALIZER] Could not parse JSON output."], true);
          }
        }

        return result.normalized;
      } catch (e: unknown) {
        if (runSeq !== runSeqRef.current) return null;

        setLastStatus("error");

        if (isAbortError(e)) {
          if (cancelledSeqRef.current !== runSeq) {
            appendConsole(["[ABORTED] Request cancelled."], true);
          }
        } else {
          const err = e as { message?: string };
          appendConsole([`[NETWORK ERROR] ${err?.message || String(e)}`], true);
        }

        return null;
      } finally {
        if (runSeq === runSeqRef.current) {
          abortRef.current = null;
          setActiveToolId(null);
        }
      }
    },
    [
      apiV1,
      appendConsole,
      confirmRisk,
      defaultDryRun,
      parseArgs,
      pickVisualizerTree,
      visualizerToolId,
      timeoutMs,
    ]
  );

  return {
    consoleOutput,
    appendConsole,
    setConsole,
    clear,

    runTool,
    cancelRun,
    activeToolId,
    lastStatus,

    lastResponseJson,

    visualData,
    setVisualData,
  };
}

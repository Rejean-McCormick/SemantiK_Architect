// architect_frontend/src/app/tools/components/ToolDetailsCard.tsx
"use client";

import React, { memo, useCallback, useMemo } from "react";
import Link from "next/link";
import {
  ChevronRight,
  Copy,
  ExternalLink,
  Eye,
  EyeOff,
  Loader2,
  Play,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

import type { ToolItem } from "../lib/buildToolItems";
import { copyToClipboard, docsHref, parseCliArgs, repoFileUrl } from "../utils";
import { RiskBadge, StatusBadge, WiringBadge } from "./Badges";

type Props = {
  selected: ToolItem | null;

  powerUser: boolean;
  leftCollapsed: boolean;
  onToggleLeftCollapsed: () => void;

  activeToolId: string | null;
  runTool: (it: ToolItem) => void;

  argsByToolId: Record<string, string>;
  setArgsByToolId: React.Dispatch<React.SetStateAction<Record<string, string>>>;

  repoUrl: string;
};

const DRY_FLAG_RE = /(^|\s)--dry(?:-run)?(?=\s|$)/g;
function hasDryFlag(raw: string) {
  return DRY_FLAG_RE.test(raw || "");
}
function stripDryFlags(raw: string) {
  // reset regex state (global regex)
  DRY_FLAG_RE.lastIndex = 0;
  return (raw || "")
    .replace(DRY_FLAG_RE, " ")
    .replace(/\s+/g, " ")
    .trim();
}
function addDryFlag(raw: string) {
  const cleaned = stripDryFlags(raw);
  return cleaned ? `${cleaned} --dry` : "--dry";
}

// Helper to toggle flag existence in a string while preserving user edits
function toggleFlag(currentArgs: string, flag: string, isChecked: boolean) {
  const argsArray = (currentArgs || "").split(" ").filter(a => a.trim() !== "");
  if (isChecked && !argsArray.includes(flag)) {
      return [...argsArray, flag].join(" ");
  } else if (!isChecked) {
      return argsArray.filter(a => a !== flag).join(" ");
  }
  return currentArgs;
}

function ToolDetailsCardImpl({
  selected,
  powerUser,
  leftCollapsed,
  onToggleLeftCollapsed,
  activeToolId,
  runTool,
  argsByToolId,
  setArgsByToolId,
  repoUrl,
}: Props) {
  const selectedToolId = selected?.wiredToolId ?? null;
  const selectedToolIdStr = selectedToolId ? String(selectedToolId) : null;

  const repoHref = selected ? repoFileUrl(repoUrl, selected.path) || null : null;

  const argsValue = useMemo(() => {
    if (!selectedToolIdStr) return "";
    return argsByToolId[selectedToolIdStr] || "";
  }, [argsByToolId, selectedToolIdStr]);

  const parsedArgsState = useMemo(() => {
    if (!selectedToolIdStr)
      return { ok: true as const, args: [] as string[], error: null as unknown };
    try {
      const args = parseCliArgs(argsValue);
      return { ok: true as const, args, error: null as unknown };
    } catch (e) {
      return { ok: false as const, args: [] as string[], error: e };
    }
  }, [argsValue, selectedToolIdStr]);

  const dryRunOn = useMemo(() => {
    if (!selectedToolIdStr) return false;
    // Prefer raw string detection to avoid parse artifacts and preserve quoting.
    return hasDryFlag(argsValue);
  }, [argsValue, selectedToolIdStr]);

  const onToggleDryRun = useCallback(
    (nextOn: boolean) => {
      if (!selectedToolIdStr) return;
      setArgsByToolId((prev) => {
        const cur = prev[selectedToolIdStr] || "";
        const next = nextOn ? addDryFlag(cur) : stripDryFlags(cur);
        return { ...prev, [selectedToolIdStr]: next };
      });
    },
    [selectedToolIdStr, setArgsByToolId]
  );

  const onCopyPath = useCallback(() => {
    if (selected) copyToClipboard(selected.path);
  }, [selected]);

  const onCopyToolId = useCallback(() => {
    if (selectedToolIdStr) copyToClipboard(selectedToolIdStr);
  }, [selectedToolIdStr]);

  // Avoid per-row closures: use data-cmd on the button
  const onCopyCmd = useCallback((e: React.MouseEvent<HTMLButtonElement>) => {
    const cmd = (e.currentTarget.dataset.cmd || "").trim();
    if (cmd) copyToClipboard(cmd);
  }, []);

  const onCopyPayload = useCallback(() => {
    if (!selectedToolIdStr) return;

    // For debugging, prefer request-shape payload:
    // - dry_run is explicit (when enabled)
    // - args excludes --dry/--dry-run to avoid duplication
    const stripDryFromArgs = (args: string[]) =>
      args.filter((a) => a !== "--dry" && a !== "--dry-run");

    const payload = parsedArgsState.ok
      ? {
          tool_id: selectedToolIdStr,
          args: stripDryFromArgs(parsedArgsState.args),
          ...(dryRunOn ? { dry_run: true } : {}),
        }
      : {
          tool_id: selectedToolIdStr,
          args_raw: argsValue,
          args_error: "invalid_cli_args",
          ...(dryRunOn ? { dry_run: true } : {}),
        };

    copyToClipboard(JSON.stringify(payload, null, 2));
  }, [argsValue, parsedArgsState, selectedToolIdStr, dryRunOn]);

  const onChangeArgs = useCallback(
    (next: string) => {
      if (!selectedToolIdStr) return;
      setArgsByToolId((prev) => ({ ...prev, [selectedToolIdStr]: next }));
    },
    [selectedToolIdStr, setArgsByToolId]
  );

  const onRunSelected = useCallback(() => {
    if (selected) runTool(selected);
  }, [runTool, selected]);

  const isRunningSelected = Boolean(
    selectedToolIdStr && activeToolId === selectedToolIdStr
  );
  const canRun = Boolean(selectedToolIdStr) && activeToolId === null && parsedArgsState.ok;

  return (
    <Card className="border-slate-200">
      <CardHeader className="py-3 px-4 flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2">
          <button
            type="button"
            className="inline-flex items-center gap-1 text-slate-500 hover:text-slate-800"
            title={leftCollapsed ? "Show tool list" : "Hide tool list"}
            onClick={onToggleLeftCollapsed}
            aria-label={leftCollapsed ? "Show tool list" : "Hide tool list"}
          >
            {leftCollapsed ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
            <ChevronRight
              className={`w-4 h-4 transition-transform ${leftCollapsed ? "rotate-180" : ""}`}
            />
          </button>
          Selected Item
        </CardTitle>

        {selected ? (
          // prefetch=false reduces overhead on large lists/apps
          <Link
            prefetch={false}
            href={docsHref(selected.key)}
            className="text-xs text-slate-600 hover:text-slate-900 inline-flex items-center gap-1"
          >
            Jump to docs <ExternalLink className="w-3 h-3" />
          </Link>
        ) : (
          <span className="text-xs text-slate-400">None selected</span>
        )}
      </CardHeader>

      <CardContent className="px-4 pb-4 text-sm">
        {selected ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold">{selected.title}</span>
              <WiringBadge
                wired={Boolean(selected.wiredToolId)}
                hidden={!powerUser && Boolean(selected.hiddenInNormalMode)}
              />
              <RiskBadge risk={selected.risk} />
              <StatusBadge status={selected.status} />
              <span className="text-xs text-slate-500">
                {selected.category} / {selected.group} •{" "}
                <span className="font-mono">{selected.kind}</span>
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {/* Path */}
              <div className="rounded-md border border-slate-200 p-3 bg-white">
                <div className="text-xs text-slate-500 mb-1">Path</div>
                <div className="font-mono text-xs break-all">{selected.path}</div>

                <div className="mt-2 flex gap-2 flex-wrap">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 px-2 text-xs"
                    onClick={onCopyPath}
                  >
                    <Copy className="w-3 h-3 mr-1" /> Copy
                  </Button>

                  {repoHref ? (
                    <a
                      href={repoHref}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs rounded-md border border-slate-200 px-2 py-1 text-slate-600 hover:bg-slate-50"
                    >
                      Open in Repo <ExternalLink className="w-3 h-3" />
                    </a>
                  ) : null}
                </div>
              </div>

              {/* Run */}
              <div className="rounded-md border border-slate-200 p-3 bg-white">
                <div className="text-xs text-slate-500 mb-1">Run (backend tool_id)</div>

                <div className="font-mono text-xs flex items-center justify-between gap-2">
                  <span>{selectedToolIdStr ?? "—"}</span>
                  <button
                    type="button"
                    className="text-slate-500 hover:text-slate-800 disabled:opacity-50"
                    onClick={onCopyToolId}
                    disabled={!selectedToolIdStr}
                    title="Copy tool_id"
                    aria-label="Copy tool_id"
                  >
                    <Copy className="w-3 h-3" />
                  </button>
                </div>

                {!selectedToolIdStr ? (
                  <div className="mt-2 text-[11px] text-slate-500">
                    Not wired (not in backend allowlist). Enable <b>Power user (debug)</b> to browse
                    inventory and decide what to wire. (Guess:{" "}
                    <span className="font-mono">{selected.toolIdGuess}</span>)
                  </div>
                ) : (
                  <>
                    <div className="mt-2 text-[11px] text-slate-500">
                      Command preview:{" "}
                      <span className="font-mono">{selected.commandPreview || "(unknown)"}</span>
                    </div>

                    <div className="mt-3">
                      <div className="text-xs text-slate-500 mb-1">Args (optional)</div>
                      
                      {/* NEW: Dynamic Argument Checkboxes (Vertical Layout) */}
                      {selected.parameterDocs && selected.parameterDocs.length > 0 && (
                        <div className="mb-3 flex flex-col gap-3 p-3 bg-slate-50 border border-slate-200 rounded-md max-h-64 overflow-y-auto">
                          {selected.parameterDocs.map((param) => {
                            const isBooleanFlag = !param.example || param.example === param.flag;
                            const isActive = argsValue.includes(param.flag);

                            return (
                              <div key={param.flag} className="flex items-start gap-2">
                                {isBooleanFlag ? (
                                  <label className="flex items-start gap-2 text-xs text-slate-700 cursor-pointer select-none w-full">
                                    <input 
                                      type="checkbox" 
                                      className="mt-0.5 rounded border-slate-300 w-3.5 h-3.5 shrink-0"
                                      checked={isActive}
                                      onChange={(e) => onChangeArgs(toggleFlag(argsValue, param.flag, e.target.checked))}
                                      disabled={activeToolId !== null}
                                    />
                                    <div className="flex flex-col">
                                      <span className="font-mono font-medium text-slate-900">{param.flag}</span>
                                      <span className="text-slate-500 mt-0.5 leading-relaxed">{param.description}</span>
                                    </div>
                                  </label>
                                ) : (
                                  <div className="flex flex-col w-full pl-5">
                                    <span className="font-mono font-medium text-slate-900 text-xs">{param.flag}</span>
                                    <span className="text-slate-500 text-xs mt-0.5 leading-relaxed">{param.description}</span>
                                    {param.example && (
                                      <span className="text-[10px] text-slate-400 font-mono mt-1">
                                        e.g. {param.example}
                                      </span>
                                    )}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}

                      {/* Existing raw text input */}
                      <input
                        value={argsValue}
                        onChange={(e) => onChangeArgs(e.target.value)}
                        placeholder="e.g. --lang fr --dry (or --dry-run)"
                        className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm font-mono outline-none focus:ring-2 focus:ring-blue-200"
                        disabled={activeToolId !== null}
                        aria-label="Tool args"
                      />

                      <label className="mt-2 flex items-center gap-2 text-xs text-slate-600 select-none">
                        <input
                          type="checkbox"
                          className="h-3.5 w-3.5"
                          checked={dryRunOn}
                          onChange={(e) => onToggleDryRun(e.target.checked)}
                          disabled={activeToolId !== null}
                          aria-label="Dry run"
                        />
                        Dry run (no writes)
                      </label>

                      {!parsedArgsState.ok ? (
                        <div className="mt-2 text-[11px] text-amber-700">
                          Args look invalid (can’t parse). Fix args to enable “Run selected”. You can
                          still copy the payload for debugging.
                        </div>
                      ) : null}

                      <div className="mt-2 flex items-center gap-2 flex-wrap">
                        <Button
                          onClick={onRunSelected}
                          disabled={!canRun}
                          variant={selected.risk === "heavy" ? "destructive" : "default"}
                          size="sm"
                          className="h-8"
                        >
                          {isRunningSelected ? (
                            <span className="inline-flex items-center gap-2">
                              <Loader2 className="w-4 h-4 animate-spin" /> Running
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-2">
                              <Play className="w-4 h-4" /> Run selected
                            </span>
                          )}
                        </Button>

                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8"
                          onClick={onCopyPayload}
                          disabled={!selectedToolIdStr}
                        >
                          <Copy className="w-4 h-4 mr-1" /> Copy payload
                        </Button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>

            {selected.desc ? <div className="text-slate-700">{selected.desc}</div> : null}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="rounded-md border border-slate-200 p-3 bg-slate-50">
                <div className="text-xs text-slate-500 mb-2">CLI equivalents</div>
                <div className="space-y-1">
                  {selected.cli.length ? (
                    selected.cli.map((cmd) => (
                      <div
                        key={cmd}
                        className="font-mono text-xs flex items-center justify-between gap-2"
                      >
                        <span className="truncate">{cmd}</span>
                        <button
                          type="button"
                          className="text-slate-500 hover:text-slate-800"
                          data-cmd={cmd}
                          onClick={onCopyCmd}
                          title="Copy command"
                          aria-label="Copy command"
                        >
                          <Copy className="w-3 h-3" />
                        </button>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-500">—</div>
                  )}
                </div>
              </div>

              <div className="rounded-md border border-slate-200 p-3 bg-slate-50">
                <div className="text-xs text-slate-500 mb-2">Interface steps</div>
                <div className="space-y-1">
                  {selected.uiSteps.length ? (
                    selected.uiSteps.map((n) => (
                      <div key={n} className="text-xs text-slate-700">
                        • {n}
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-500">—</div>
                  )}
                </div>
              </div>
            </div>

            <div className="rounded-md border border-slate-200 p-3">
              <div className="text-xs text-slate-500 mb-2">Notes</div>
              <div className="space-y-1">
                {selected.notes.length ? (
                  selected.notes.map((n) => (
                    <div key={n} className="text-xs text-slate-700">
                      • {n}
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-slate-500">—</div>
                )}
              </div>
            </div>

            <div className="text-xs text-slate-500">
              tool_id (guess): <span className="font-mono">{selected.toolIdGuess}</span>
              {selectedToolIdStr ? (
                <>
                  {" "}
                  • wired tool_id: <span className="font-mono">{selectedToolIdStr}</span>
                </>
              ) : null}
            </div>
          </div>
        ) : (
          <div className="text-slate-500 text-sm">Select an item from the left to view details.</div>
        )}
      </CardContent>
    </Card>
  );
}

// Custom memo comparator: avoids rerenders when parent updates unrelated state.
const ToolDetailsCard = memo(ToolDetailsCardImpl, (prev, next) => {
  const aSel = prev.selected;
  const bSel = next.selected;

  const aId = aSel?.wiredToolId ? String(aSel.wiredToolId) : null;
  const bId = bSel?.wiredToolId ? String(bSel.wiredToolId) : null;

  const aArgs = aId ? prev.argsByToolId[aId] : "";
  const bArgs = bId ? next.argsByToolId[bId] : "";

  return (
    prev.powerUser === next.powerUser &&
    prev.leftCollapsed === next.leftCollapsed &&
    prev.activeToolId === next.activeToolId &&
    prev.repoUrl === next.repoUrl &&
    aArgs === bArgs &&
    (aSel?.key ?? null) === (bSel?.key ?? null)
  );
});

export default ToolDetailsCard;
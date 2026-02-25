// architect_frontend/src/app/tools/components/ToolDetailsPanel.tsx
"use client";

import React, { useMemo, useCallback } from "react";
import Link from "next/link";
import { ExternalLink, Copy, Loader2, Play, Info, X } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

import { RiskBadge, StatusBadge, WiringBadge } from "./Badges";
import type { ToolItem } from "../types";
import { copyToClipboard, docsHref, parseCliArgs, repoFileUrl } from "../utils";

interface ToolDetailsPanelProps {
  selected: ToolItem | null;
  repoUrl: string;
  activeToolId: string | null;
  argsByToolId: Record<string, string>;
  setArgsByToolId: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  runTool: (it: ToolItem) => void;
}

export function ToolDetailsPanel(props: ToolDetailsPanelProps) {
  const { selected, repoUrl, activeToolId, argsByToolId, setArgsByToolId, runTool } = props;

  if (!selected) {
    return (
      <Card className="border-slate-200 h-full flex flex-col justify-center items-center text-slate-400 p-8 text-center bg-slate-50/50">
        <Info className="w-10 h-10 mb-3 opacity-20" />
        <div className="text-sm font-medium">No tool selected</div>
        <div className="text-xs mt-1">Select an item from the sidebar to view details.</div>
      </Card>
    );
  }

  const wiredToolId = selected.wiredToolId || null;
  const isWired = Boolean(wiredToolId);
  const isRunning = Boolean(wiredToolId && activeToolId === wiredToolId);
  const isBusy = activeToolId !== null;

  const extraArgs = useMemo(() => {
    if (!wiredToolId) return "";
    return argsByToolId[wiredToolId] || "";
  }, [argsByToolId, wiredToolId]);

  const parsedArgs = useMemo(() => parseCliArgs(extraArgs), [extraArgs]);

  const repoHref = useMemo(() => repoFileUrl(repoUrl, selected.path), [repoUrl, selected.path]);

  const fullPreview = useMemo(() => {
    const base = (selected.commandPreview || selected.cli?.[0] || "").trim();
    const suffix = (extraArgs || "").trim();

    if (!base) return "...";
    if (!suffix) return base;

    // Avoid duplicating if preview already includes the args.
    return base.includes(suffix) ? base : `${base} ${suffix}`.trim();
  }, [selected.commandPreview, selected.cli, extraArgs]);

  const onChangeArgs = useCallback(
    (val: string) => {
      if (!wiredToolId) return;
      setArgsByToolId((prev) => ({ ...prev, [wiredToolId]: val }));
    },
    [setArgsByToolId, wiredToolId]
  );

  const clearArgs = useCallback(() => {
    if (!wiredToolId) return;
    setArgsByToolId((prev) => ({ ...prev, [wiredToolId]: "" }));
  }, [setArgsByToolId, wiredToolId]);

  const handleRun = useCallback(() => {
    if (!isWired) return;

    // Lightweight safety rail for heavy tools.
    if (selected.risk === "heavy") {
      const ok = window.confirm("This tool is marked HEAVY and may take a while or use significant resources. Run it?");
      if (!ok) return;
    }

    runTool(selected);
  }, [isWired, runTool, selected]);

  return (
    <Card className="border-slate-200 shadow-sm h-full overflow-hidden flex flex-col">
      <CardHeader className="py-3 px-4 flex flex-row items-center justify-between bg-slate-50/50 border-b border-slate-100 shrink-0">
        <CardTitle className="text-sm font-semibold text-slate-700">Tool Details</CardTitle>
        <Link
          href={docsHref(selected.key)}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-blue-600 hover:text-blue-800 hover:underline inline-flex items-center gap-1 transition-colors"
        >
          Documentation <ExternalLink className="w-3 h-3" />
        </Link>
      </CardHeader>

      <CardContent className="p-0 overflow-y-auto">
        <div className="p-4 space-y-5">
          {/* Header Section */}
          <div className="space-y-3">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1">
                <h3 className="text-lg font-bold text-slate-800 leading-tight">{selected.title}</h3>
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <span className="font-medium text-slate-600">{selected.category}</span>
                  <span>/</span>
                  <span>{selected.group}</span>
                  <span>•</span>
                  <span className="font-mono bg-slate-100 px-1 rounded">{selected.kind}</span>
                </div>
              </div>
              <div className="flex flex-col items-end gap-1.5 shrink-0">
                <div className="flex gap-1.5">
                  <StatusBadge status={selected.status} />
                  <RiskBadge risk={selected.risk} />
                </div>
                <WiringBadge wired={Boolean(selected.wiredToolId)} hidden={Boolean(selected.hidden)} />
              </div>
            </div>

            {selected.desc && (
              <div className="text-sm text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-md border border-slate-100">
                {selected.desc}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 gap-4">
            {/* Execution Panel */}
            <div
              className={`rounded-lg border p-4 ${
                isWired ? "bg-blue-50/30 border-blue-100" : "bg-slate-50 border-slate-200"
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  {isWired ? "Execution Control" : "Configuration"}
                </div>

                {isWired && wiredToolId && (
                  <div className="flex items-center gap-1 text-[10px] text-slate-400 font-mono">
                    ID: {wiredToolId}
                    <button
                      onClick={() => copyToClipboard(wiredToolId)}
                      className="hover:text-slate-700 p-0.5"
                      title="Copy Tool ID"
                      aria-label="Copy Tool ID"
                    >
                      <Copy className="w-3 h-3" />
                    </button>
                  </div>
                )}
              </div>

              {!isWired ? (
                <div className="text-sm text-slate-500 italic">
                  This tool is not wired to the backend (not in allowlist).
                  <div className="mt-1 text-xs">
                    Guessed ID: <span className="font-mono">{selected.toolIdGuess}</span>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  {/* Command Preview */}
                  <div className="space-y-1">
                    <label className="text-[10px] uppercase font-bold text-slate-400">Preview</label>
                    <div className="font-mono text-xs bg-white border border-slate-200 rounded px-2 py-1.5 text-slate-600 break-all">
                      {fullPreview}
                    </div>

                    <div className="flex flex-wrap gap-2 pt-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs px-2 text-slate-500 hover:text-slate-900"
                        onClick={() => copyToClipboard(fullPreview)}
                        disabled={!fullPreview || fullPreview === "..."}
                      >
                        <Copy className="w-3 h-3 mr-1.5" /> Copy Preview
                      </Button>
                    </div>
                  </div>

                  {/* Arguments Input */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="text-[10px] uppercase font-bold text-slate-400">Extra Arguments</label>
                      <button
                        onClick={clearArgs}
                        className="inline-flex items-center gap-1 text-[10px] text-slate-400 hover:text-slate-700"
                        title="Clear arguments"
                        aria-label="Clear arguments"
                        disabled={isBusy}
                      >
                        <X className="w-3 h-3" />
                        Clear
                      </button>
                    </div>

                    <input
                      value={extraArgs}
                      onChange={(e) => onChangeArgs(e.target.value)}
                      placeholder="e.g. --verbose --dry-run"
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm font-mono outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400 placeholder:text-slate-400"
                      disabled={isBusy}
                    />

                    {/* Parsed args chips */}
                    {Array.isArray(parsedArgs) && parsedArgs.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {parsedArgs.slice(0, 12).map((a: any, i: number) => (
                          <span
                            key={`${String(a)}-${i}`}
                            className="text-[10px] font-mono bg-white border border-slate-200 text-slate-600 px-1.5 py-0.5 rounded"
                          >
                            {String(a)}
                          </span>
                        ))}
                        {parsedArgs.length > 12 && (
                          <span className="text-[10px] text-slate-400">+{parsedArgs.length - 12} more</span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="pt-1 flex flex-wrap gap-2">
                    <Button
                      onClick={handleRun}
                      disabled={isBusy}
                      variant={selected.risk === "heavy" ? "destructive" : "default"}
                      className="flex-1 min-w-[120px]"
                    >
                      {isRunning ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Running...
                        </>
                      ) : (
                        <>
                          <Play className="w-4 h-4 mr-2" /> Run Tool
                        </>
                      )}
                    </Button>

                    <Button
                      variant="outline"
                      className="bg-white"
                      disabled={!wiredToolId}
                      onClick={() =>
                        copyToClipboard(
                          JSON.stringify(
                            {
                              tool_id: wiredToolId,
                              args: parsedArgs,
                            },
                            null,
                            2
                          )
                        )
                      }
                    >
                      <Copy className="w-4 h-4 mr-2" /> JSON Payload
                    </Button>
                  </div>
                </div>
              )}
            </div>

            {/* Path & Source Info */}
            <div className="rounded-lg border border-slate-200 bg-white p-3 space-y-2">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Source Definition</div>
              <div className="font-mono text-xs text-slate-600 break-all bg-slate-50 px-2 py-1.5 rounded border border-slate-100">
                {selected.path}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs px-2 text-slate-500 hover:text-slate-900"
                  onClick={() => copyToClipboard(selected.path)}
                >
                  <Copy className="w-3 h-3 mr-1.5" /> Copy Path
                </Button>

                {repoHref && (
                  <a
                    href={repoHref}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center justify-center h-7 px-2 text-xs font-medium text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
                  >
                    Open in Repo <ExternalLink className="w-3 h-3 ml-1.5" />
                  </a>
                )}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* CLI Commands */}
            {selected.cli && selected.cli.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">CLI Equivalents</h4>
                <div className="rounded-md border border-slate-200 bg-slate-50 divide-y divide-slate-200">
                  {selected.cli.map((cmd, i) => (
                    <div key={i} className="p-2 flex items-center justify-between gap-2 group">
                      <code className="text-xs font-mono text-slate-700 break-all">{cmd}</code>
                      <button
                        onClick={() => copyToClipboard(cmd)}
                        className="text-slate-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity p-1"
                        title="Copy command"
                        aria-label="Copy command"
                      >
                        <Copy className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* UI Steps */}
            {selected.uiSteps && selected.uiSteps.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Manual Steps</h4>
                <ul className="list-disc list-inside space-y-1 text-xs text-slate-600 bg-white p-2 rounded-md border border-slate-200">
                  {selected.uiSteps.map((step, i) => (
                    <li key={i} className="pl-1">
                      {step}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Notes */}
          {selected.notes && selected.notes.length > 0 && (
            <div className="space-y-2 pt-2 border-t border-slate-100">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Dev Notes</h4>
              <ul className="space-y-1 text-xs text-slate-600">
                {selected.notes.map((note, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-slate-400">•</span>
                    <span>{note}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="h-4" /> {/* Spacer */}
        </div>
      </CardContent>
    </Card>
  );
}

export default ToolDetailsPanel;

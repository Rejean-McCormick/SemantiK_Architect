// architect_frontend/src/app/tools/components/ConsoleCard.tsx
"use client";

import React, { memo, useCallback, useEffect, useRef } from "react";
import { Terminal, Loader2, CheckCircle2, XCircle, Ban } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import ASTViewer from "@/components/tools/ASTViewer";

import { copyToClipboard } from "../utils";

type Status = "success" | "error" | null;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ConsoleCardProps = {
  consoleOutput: string;
  lastStatus: Status;
  lastResponseJson?: string | null;

  activeToolId: string | null;
  selectedToolId?: string | null;

  autoScroll: boolean;
  onAutoScrollChange: (next: boolean) => void;

  onCancel?: () => void;
  onClear?: () => void;

  // Visualizer (optional)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  visualData?: any;
  onCloseVisualizer?: () => void;
  visualizerHeight?: number;
};

function ConsoleCardImpl({
  consoleOutput,
  lastStatus,
  lastResponseJson,

  activeToolId,
  selectedToolId,

  autoScroll,
  onAutoScrollChange,

  onCancel,
  onClear,

  visualData,
  onCloseVisualizer,
  visualizerHeight = 500,
}: ConsoleCardProps) {
  const consoleRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (!autoScroll) return;
    const el = consoleRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [consoleOutput, autoScroll]);

  const handleClear = useCallback(() => {
    onClear?.();
  }, [onClear]);

  const handleCopyText = useCallback(() => {
    copyToClipboard(consoleOutput);
  }, [consoleOutput]);

  const handleCopyJson = useCallback(() => {
    if (!lastResponseJson) return;
    copyToClipboard(lastResponseJson);
  }, [lastResponseJson]);

  const handleToggleAutoscroll = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => onAutoScrollChange(e.target.checked),
    [onAutoScrollChange]
  );

  return (
    <Card className="flex-1 flex flex-col bg-slate-950 border-slate-800 shadow-2xl overflow-hidden min-h-[400px]">
      <CardHeader className="py-3 px-4 border-b border-slate-800 bg-slate-900/60 flex flex-row items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-slate-200" />
          <CardTitle className="text-xs font-mono uppercase tracking-widest text-slate-100">
            Console Output
          </CardTitle>
        </div>

        <div className="flex items-center gap-3">
          {/* Higher contrast meta */}
          <span className="text-[10px] text-slate-100/80 font-mono">
            active_tool: {activeToolId ?? "—"}
            {` • selected: ${selectedToolId ?? "—"}`}
          </span>

          {/* Higher contrast label + nicer checkbox */}
          <label className="flex items-center gap-2 text-[10px] text-slate-100/80 font-mono">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={handleToggleAutoscroll}
              className="accent-sky-400"
            />
            autoscroll
          </label>

          {activeToolId && onCancel && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-[10px] text-amber-300 hover:text-amber-200 hover:bg-slate-800/60"
              onClick={onCancel}
              title="Cancel the in-flight run request"
            >
              <Ban className="w-3 h-3 mr-1" /> Cancel
            </Button>
          )}

          {lastStatus === "success" && (
            <span className="flex items-center gap-1 text-xs text-green-400">
              <CheckCircle2 className="w-3 h-3" /> Success
            </span>
          )}
          {lastStatus === "error" && (
            <span className="flex items-center gap-1 text-xs text-red-400">
              <XCircle className="w-3 h-3" /> Failed
            </span>
          )}

          {/* Higher contrast header buttons */}
          <Button
            variant="ghost"
            size="sm"
            className="h-6 text-[10px] text-slate-100/80 hover:text-white hover:bg-slate-800/60"
            onClick={handleClear}
          >
            Clear
          </Button>

          <Button
            variant="ghost"
            size="sm"
            className="h-6 text-[10px] text-slate-100/80 hover:text-white hover:bg-slate-800/60"
            onClick={handleCopyText}
            title="Copy console text"
          >
            Copy Text
          </Button>

          <Button
            variant="ghost"
            size="sm"
            className="h-6 text-[10px] text-sky-300 hover:text-sky-200 hover:bg-slate-800/60"
            onClick={handleCopyJson}
            disabled={!lastResponseJson}
            title="Copy full JSON response object for debugging"
          >
            {activeToolId ? (
              <span className="inline-flex items-center gap-2">
                <Loader2 className="w-3 h-3 animate-spin" />
                Copy JSON Bundle
              </span>
            ) : (
              "Copy JSON Bundle"
            )}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 p-0 relative flex flex-col min-h-0">
        {visualData && (
          <div className="border-b border-slate-800 bg-white relative shrink-0 overflow-hidden">
            <div className="absolute top-2 right-2 z-10 flex gap-2">
              <div className="bg-slate-800 text-white text-[10px] px-2 py-1 rounded opacity-80 pointer-events-none">
                Interactive Visualizer Active
              </div>
              {onCloseVisualizer && (
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs bg-white text-slate-800 border-slate-300 hover:bg-slate-100"
                  onClick={onCloseVisualizer}
                >
                  Close Visualizer
                </Button>
              )}
            </div>
            <ASTViewer data={visualData} height={visualizerHeight} />
          </div>
        )}

        <textarea
          ref={consoleRef}
          readOnly
          value={consoleOutput}
          className="w-full flex-1 bg-slate-950 text-slate-200 font-mono text-xs p-4 resize-none focus:outline-none min-h-[100px]"
        />
      </CardContent>
    </Card>
  );
}

export default memo(ConsoleCardImpl);
export type { ConsoleCardProps };

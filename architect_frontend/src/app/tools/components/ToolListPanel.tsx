// architect_frontend/src/app/tools/components/ToolListPanel.tsx
"use client";

import React, { memo, useCallback, useEffect, useLayoutEffect, useMemo, useRef } from "react";
import Link from "next/link";
import { ExternalLink, Loader2, Play } from "lucide-react";

import { Button } from "@/components/ui/button";
import { RiskBadge, StatusBadge, WiringBadge } from "./Badges";
import { iconForCategory } from "./icons";
import { docsHref } from "../utils";
import type { ToolItem } from "../lib/buildToolItems";

export type GroupedTools = Map<string, Map<string, ToolItem[]>>;

type Props = {
  grouped: GroupedTools;
  selectedKey: string | null;
  activeToolId: string | null;
  powerUser: boolean;

  disabled?: boolean;

  /** Optional dynamic description provider (cached by path). */
  getDescription?: (path: string) => string | undefined;

  onSelect: (key: string) => void;
  onRun: (it: ToolItem) => void;

  /** Scroll selected row into view. Default true. */
  autoScrollToSelected?: boolean;
};

const collator = new Intl.Collator(undefined, { sensitivity: "base", numeric: true });

type RenderModel = Array<{
  cat: string;
  count: number;
  groups: Array<{ groupName: string; items: ToolItem[] }>;
}>;

function cssEscapeSafe(v: string) {
  if (typeof CSS !== "undefined" && typeof (CSS as any).escape === "function") {
    return (CSS as any).escape(v);
  }
  // Fallback good enough for attribute selectors.
  return v.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

const ToolRow = memo(
  function ToolRow({
    it,
    isSelected,
    isRunning,
    powerUser,
    disabled,
    desc,
    onSelect,
    onRun,
  }: {
    it: ToolItem;
    isSelected: boolean;
    isRunning: boolean;
    powerUser: boolean;
    disabled: boolean;
    desc?: string;
    onSelect: (key: string) => void;
    onRun: (it: ToolItem) => void;
  }) {
    const handleSelect = useCallback(() => {
      if (disabled) return;
      onSelect(it.key);
    }, [disabled, onSelect, it.key]);

    const handleRun = useCallback(() => {
      if (disabled) return;
      onRun(it);
    }, [disabled, onRun, it]);

    const handleDocsClick = useCallback(() => {
      // Allow navigation always; only update selection when not disabled.
      if (disabled) return;
      onSelect(it.key);
    }, [disabled, onSelect, it.key]);

    return (
      <div
        data-tool-key={it.key}
        className={`rounded-lg border bg-white transition-all ${
          isSelected ? "border-blue-400 shadow-sm" : "border-slate-200"
        }`}
        style={{ contentVisibility: "auto", containIntrinsicSize: "72px" }}
        aria-current={isSelected ? "true" : undefined}
      >
        <div className="flex items-start justify-between gap-3 p-3">
          <button
            type="button"
            onClick={handleSelect}
            className="flex-1 text-left"
            disabled={disabled}
            aria-label={`Select ${it.title}`}
          >
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-slate-800 text-sm">{it.title}</span>
              <WiringBadge
                wired={Boolean(it.wiredToolId)}
                hidden={!powerUser && Boolean(it.hiddenInNormalMode)}
              />
              <RiskBadge risk={it.risk} />
              <StatusBadge status={it.status} />
            </div>

            <div className="text-[11px] text-slate-400 font-mono mt-1 truncate">{it.path}</div>

            {desc ? <div className="text-xs text-slate-500 mt-1 line-clamp-2">{desc}</div> : null}
          </button>

          <div className="flex flex-col gap-2 shrink-0">
            <Link
              prefetch={false}
              href={docsHref(it.key)}
              className="inline-flex items-center justify-center gap-1 text-xs rounded-md border border-slate-200 px-2 py-1 text-slate-600 hover:bg-slate-50"
              onClick={handleDocsClick}
              aria-label={`Open docs for ${it.title}`}
            >
              Docs <ExternalLink className="w-3 h-3" />
            </Link>

            <Button
              size="sm"
              className="h-8 px-3"
              onClick={handleRun}
              disabled={disabled || !it.wiredToolId}
              variant={it.risk === "heavy" ? "destructive" : "default"}
              title={it.wiredToolId ? "Run (backend-wired)" : "Run disabled (not in backend allowlist)"}
            >
              {isRunning ? (
                <span className="inline-flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" /> Running
                </span>
              ) : (
                <span className="inline-flex items-center gap-2">
                  <Play className="w-4 h-4" /> Run
                </span>
              )}
            </Button>
          </div>
        </div>
      </div>
    );
  },
  (prev, next) =>
    prev.it === next.it &&
    prev.isSelected === next.isSelected &&
    prev.isRunning === next.isRunning &&
    prev.powerUser === next.powerUser &&
    prev.disabled === next.disabled &&
    prev.desc === next.desc
);

export default function ToolListPanel({
  grouped,
  selectedKey,
  activeToolId,
  powerUser,
  disabled = false,
  getDescription,
  onSelect,
  onRun,
  autoScrollToSelected = true,
}: Props) {
  const listDisabled = disabled || activeToolId !== null;

  // Cache descriptions by path so we don’t recompute on every render.
  const descCacheRef = useRef<Map<string, string | undefined>>(new Map());

  useEffect(() => {
    descCacheRef.current = new Map();
  }, [getDescription]);

  const getDesc = useCallback(
    (path: string) => {
      if (!getDescription) return undefined;
      const cache = descCacheRef.current;
      if (cache.has(path)) return cache.get(path);
      const v = getDescription(path);
      cache.set(path, v);
      return v;
    },
    [getDescription]
  );

  const model: RenderModel = useMemo(() => {
    const cats = Array.from(grouped.entries()).map(([cat, byGroup]) => {
      const groups = Array.from(byGroup.entries())
        .sort((a, b) => collator.compare(a[0], b[0]))
        .map(([groupName, items]) => ({ groupName, items }));

      const count = groups.reduce((n, g) => n + g.items.length, 0);
      return { cat, groups, count };
    });

    cats.sort((a, b) => collator.compare(a.cat, b.cat));
    return cats;
  }, [grouped]);

  const containerRef = useRef<HTMLDivElement | null>(null);

  useLayoutEffect(() => {
    if (!autoScrollToSelected) return;
    if (!selectedKey) return;

    const root = containerRef.current;
    if (!root) return;

    const key = cssEscapeSafe(selectedKey);
    const el = root.querySelector<HTMLElement>(`[data-tool-key="${key}"]`);
    if (!el) return;

    const raf = requestAnimationFrame(() => {
      el.scrollIntoView({ block: "nearest" });
    });

    return () => cancelAnimationFrame(raf);
  }, [autoScrollToSelected, selectedKey, grouped]);

  const handleSelect = useCallback((key: string) => onSelect(key), [onSelect]);
  const handleRun = useCallback((it: ToolItem) => onRun(it), [onRun]);

  return (
    <div ref={containerRef} className="space-y-4 overflow-y-auto pr-2 pb-10">
      {model.map(({ cat, groups, count }) => (
        <div key={cat} className="space-y-2">
          <div className="flex items-center gap-2">
            {iconForCategory(cat)}
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500">{cat}</h2>
            <span className="text-xs text-slate-400">({count})</span>
          </div>

          {groups.map(({ groupName, items }) => (
            <div key={groupName} className="space-y-2">
              <div className="text-xs font-semibold text-slate-400 pl-1">{groupName}</div>

              <div className="grid gap-2">
                {items.map((it) => {
                  const isSelected = selectedKey === it.key;
                  const wiredId = it.wiredToolId ? String(it.wiredToolId) : null;
                  const isRunning = Boolean(wiredId && activeToolId && wiredId === activeToolId);
                  const desc = getDesc(it.path) ?? it.desc;

                  return (
                    <ToolRow
                      key={it.key}
                      it={it}
                      isSelected={isSelected}
                      isRunning={isRunning}
                      powerUser={powerUser}
                      disabled={listDisabled}
                      desc={desc}
                      onSelect={handleSelect}
                      onRun={handleRun}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

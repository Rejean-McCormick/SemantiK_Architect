// architect_frontend/src/components/everything-matrix/MatrixGrid.tsx
"use client";

import { useMemo, useState } from "react";
import type { EverythingMatrix } from "@/types/EverythingMatrix";
import LanguageRow from "./LanguageRow";

interface MatrixGridProps {
  matrix: EverythingMatrix;
}

type SortField = "iso" | "maturity" | "strategy";
type SortOrder = "asc" | "desc";

const ZONE_GROUPS: Array<{
  label: string;
  colSpan: number;
  className: string;
}> = [
  {
    label: "Zone A: Logic (RGL)",
    colSpan: 5,
    className:
      "border-b border-r border-slate-200 px-2 py-1 text-center font-bold text-blue-700 bg-blue-50/50",
  },
  {
    label: "Zone B: Data (Lexicon)",
    colSpan: 4,
    className:
      "border-b border-r border-slate-200 px-2 py-1 text-center font-bold text-amber-700 bg-amber-50/50",
  },
  {
    label: "Zone C: Apps",
    colSpan: 3,
    className:
      "border-b border-r border-slate-200 px-2 py-1 text-center font-bold text-purple-700 bg-purple-50/50",
  },
  {
    label: "Zone D: QA",
    colSpan: 2,
    className:
      "border-b border-slate-200 px-2 py-1 text-center font-bold text-emerald-700 bg-emerald-50/50",
  },
];

const ZONE_COLUMNS: Array<{
  key: string;
  label: string;
  title: string;
  className?: string;
}> = [
  // Zone A
  {
    key: "cat",
    label: "Cat",
    title: "Category Definitions",
    className: "border-b border-slate-200 px-2 py-2 text-center",
  },
  {
    key: "noun",
    label: "Noun",
    title: "Noun Morphology",
    className: "border-b border-slate-200 px-2 py-2 text-center",
  },
  {
    key: "para",
    label: "Para",
    title: "Paradigms",
    className: "border-b border-slate-200 px-2 py-2 text-center",
  },
  {
    key: "gram",
    label: "Gram",
    title: "Grammar Core",
    className: "border-b border-slate-200 px-2 py-2 text-center",
  },
  {
    key: "syn",
    label: "Syn",
    title: "Syntax API",
    className:
      "border-b border-r border-slate-200 px-2 py-2 text-center font-bold",
  },

  // Zone B
  {
    key: "seed",
    label: "Seed",
    title: "Core Seed (>150 words)",
    className: "border-b border-slate-200 px-2 py-2 text-center",
  },
  {
    key: "conc",
    label: "Conc",
    title: "Domain Concepts (>500)",
    className: "border-b border-slate-200 px-2 py-2 text-center",
  },
  {
    key: "wide",
    label: "Wide",
    title: "Wide Import (wide.json)",
    className: "border-b border-slate-200 px-2 py-2 text-center",
  },
  {
    key: "sem",
    label: "Sem",
    title: "Semantic Alignment (QIDs)",
    className:
      "border-b border-r border-slate-200 px-2 py-2 text-center",
  },

  // Zone C
  {
    key: "prof",
    label: "Prof",
    title: "Bio-Ready",
    className: "border-b border-slate-200 px-2 py-2 text-center",
  },
  {
    key: "asst",
    label: "Asst",
    title: "Assistant-Ready",
    className: "border-b border-slate-200 px-2 py-2 text-center",
  },
  {
    key: "rout",
    label: "Rout",
    title: "Topology Routing",
    className:
      "border-b border-r border-slate-200 px-2 py-2 text-center",
  },

  // Zone D
  {
    key: "bin",
    label: "Bin",
    title: "Binary Compilation",
    className: "border-b border-slate-200 px-2 py-2 text-center",
  },
  {
    key: "test",
    label: "Test",
    title: "Unit Tests",
    className: "border-b border-slate-200 px-2 py-2 text-center",
  },
];

function sortIndicator(active: boolean, order: SortOrder) {
  if (!active) return "";
  return order === "asc" ? " ↑" : " ↓";
}

function normalizeForSearch(s: string) {
  return s
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "");
}

function safeNum(n: unknown, fallback = 0) {
  const x = typeof n === "number" ? n : Number(n);
  return Number.isFinite(x) ? x : fallback;
}

/**
 * Normalize possibly-legacy metrics to 0..10 for consistent UI.
 * - Some older scanners emitted 0..1 for C_APP / D_QA. We upscale those.
 * - New scanners should emit 0..10 already.
 */
function normalizeMetric10(value: unknown): number {
  const v = safeNum(value, 0);
  if (v <= 1.000001) {
    // Legacy 0..1 range -> scale to 0..10
    return v * 10;
  }
  return v;
}

// Cell color mapping for 0..10 numeric metrics
function metricClass(value: number) {
  if (value >= 9) return "bg-emerald-50 text-emerald-800";
  if (value >= 7) return "bg-lime-50 text-lime-800";
  if (value >= 4) return "bg-amber-50 text-amber-800";
  if (value > 0) return "bg-rose-50 text-rose-800";
  return "bg-slate-50 text-slate-400";
}

function fmtMetric(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

export default function MatrixGrid({ matrix }: MatrixGridProps) {
  const [search, setSearch] = useState("");
  const [sortField, setSortField] = useState<SortField>("maturity");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  const languages = useMemo(
    () => Object.values(matrix.languages || {}),
    [matrix.languages]
  );

  // Precompute grid-level stats so UI can show "more data"
  const summary = useMemo(() => {
    const langs = languages;
    const total = langs.length;

    const runnable = langs.reduce(
      (acc, l) => acc + (l.verdict?.runnable ? 1 : 0),
      0
    );
    const highRoad = langs.reduce(
      (acc, l) =>
        acc + ((l.verdict?.build_strategy || "") === "HIGH_ROAD" ? 1 : 0),
      0
    );
    const safeMode = langs.reduce(
      (acc, l) =>
        acc + ((l.verdict?.build_strategy || "") === "SAFE_MODE" ? 1 : 0),
      0
    );

    const avgMaturity =
      total > 0
        ? langs.reduce(
            (acc, l) => acc + safeNum(l.verdict?.maturity_score, 0),
            0
          ) / total
        : 0;

    // Completion = avg of all 14 metrics per language, then averaged across languages (0..10)
    const completionAvg =
      total > 0
        ? langs.reduce((acc, l) => {
            const z = l.zones;
            const a = z?.A_RGL || ({} as any);
            const b = z?.B_LEX || ({} as any);
            const c = z?.C_APP || ({} as any);
            const d = z?.D_QA || ({} as any);

            const metrics = [
              normalizeMetric10(a.CAT),
              normalizeMetric10(a.NOUN),
              normalizeMetric10(a.PARA),
              normalizeMetric10(a.GRAM),
              normalizeMetric10(a.SYN),

              normalizeMetric10(b.SEED),
              normalizeMetric10(b.CONC),
              normalizeMetric10(b.WIDE),
              normalizeMetric10(b.SEM),

              normalizeMetric10(c.PROF),
              normalizeMetric10(c.ASST),
              normalizeMetric10(c.ROUT),

              normalizeMetric10(d.BIN),
              normalizeMetric10(d.TEST),
            ];

            const mean =
              metrics.reduce((x, y) => x + y, 0) / metrics.length;
            return acc + mean;
          }, 0) / total
        : 0;

    return {
      total,
      runnable,
      highRoad,
      safeMode,
      avgMaturity,
      completionAvg,
    };
  }, [languages]);

  const filteredLanguages = useMemo(() => {
    const q = normalizeForSearch(search.trim());
    let langs = languages;

    if (q) {
      langs = langs.filter((l) => {
        const name = normalizeForSearch(l.meta?.name || "");
        const iso = normalizeForSearch(l.meta?.iso || "");
        return name.includes(q) || iso.includes(q);
      });
    }

    const sorted = [...langs].sort((a, b) => {
      let valA: string | number = "";
      let valB: string | number = "";

      if (sortField === "iso") {
        valA = (a.meta?.iso || "").toLowerCase();
        valB = (b.meta?.iso || "").toLowerCase();
      } else if (sortField === "strategy") {
        valA = (a.verdict?.build_strategy || "").toLowerCase();
        valB = (b.verdict?.build_strategy || "").toLowerCase();
      } else {
        valA = safeNum(a.verdict?.maturity_score, 0);
        valB = safeNum(b.verdict?.maturity_score, 0);
      }

      if (valA < valB) return sortOrder === "asc" ? -1 : 1;
      if (valA > valB) return sortOrder === "asc" ? 1 : -1;

      const isoA = (a.meta?.iso || "").toLowerCase();
      const isoB = (b.meta?.iso || "").toLowerCase();
      if (isoA < isoB) return -1;
      if (isoA > isoB) return 1;

      const nameA = (a.meta?.name || "").toLowerCase();
      const nameB = (b.meta?.name || "").toLowerCase();
      if (nameA < nameB) return -1;
      if (nameA > nameB) return 1;

      return 0;
    });

    return sorted;
  }, [languages, search, sortField, sortOrder]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  const activeCount = filteredLanguages.length;
  const totalCount = languages.length;

  return (
    <div className="flex flex-col">
      {/* Controls Toolbar */}
      <div className="flex flex-col gap-4 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
          <input
            type="text"
            placeholder="Search ISO or name (e.g. 'fr', 'Zulu')..."
            className="w-full rounded-md border border-slate-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none sm:w-96"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

          <div className="text-xs text-slate-500">
            Showing <span className="font-mono">{activeCount}</span> /{" "}
            <span className="font-mono">{totalCount}</span>
          </div>

          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">
              Runnable: <span className="font-mono">{summary.runnable}</span>
            </span>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">
              HIGH_ROAD: <span className="font-mono">{summary.highRoad}</span>
            </span>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">
              SAFE_MODE: <span className="font-mono">{summary.safeMode}</span>
            </span>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">
              Avg maturity:{" "}
              <span className="font-mono">{summary.avgMaturity.toFixed(1)}</span>
            </span>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">
              Avg completion:{" "}
              <span className="font-mono">
                {summary.completionAvg.toFixed(1)}
              </span>
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
          <span>Sort by:</span>

          <button
            onClick={() => handleSort("maturity")}
            className={`font-medium hover:text-blue-600 ${
              sortField === "maturity" ? "text-blue-700 underline" : ""
            }`}
            title="Sort by maturity score"
          >
            Maturity{sortIndicator(sortField === "maturity", sortOrder)}
          </button>

          <button
            onClick={() => handleSort("iso")}
            className={`font-medium hover:text-blue-600 ${
              sortField === "iso" ? "text-blue-700 underline" : ""
            }`}
            title="Sort by ISO code"
          >
            ISO Code{sortIndicator(sortField === "iso", sortOrder)}
          </button>

          <button
            onClick={() => handleSort("strategy")}
            className={`font-medium hover:text-blue-600 ${
              sortField === "strategy" ? "text-blue-700 underline" : ""
            }`}
            title="Sort by build strategy"
          >
            Strategy{sortIndicator(sortField === "strategy", sortOrder)}
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="border-b border-slate-200 bg-white px-4 py-2 text-xs text-slate-600">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-slate-700">Legend:</span>
          <span className="inline-flex items-center gap-2 rounded-md bg-slate-50 px-2 py-1">
            <span className="h-3 w-3 rounded-sm bg-emerald-50 ring-1 ring-slate-200" />
            9–10
          </span>
          <span className="inline-flex items-center gap-2 rounded-md bg-slate-50 px-2 py-1">
            <span className="h-3 w-3 rounded-sm bg-lime-50 ring-1 ring-slate-200" />
            7–8.9
          </span>
          <span className="inline-flex items-center gap-2 rounded-md bg-slate-50 px-2 py-1">
            <span className="h-3 w-3 rounded-sm bg-amber-50 ring-1 ring-slate-200" />
            4–6.9
          </span>
          <span className="inline-flex items-center gap-2 rounded-md bg-slate-50 px-2 py-1">
            <span className="h-3 w-3 rounded-sm bg-rose-50 ring-1 ring-slate-200" />
            0.1–3.9
          </span>
          <span className="inline-flex items-center gap-2 rounded-md bg-slate-50 px-2 py-1">
            <span className="h-3 w-3 rounded-sm bg-slate-50 ring-1 ring-slate-200" />
            0
          </span>
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th
                className="sticky left-0 z-10 border-b border-r border-slate-200 bg-slate-50 px-4 py-2"
                rowSpan={2}
              >
                <button
                  onClick={() => handleSort("iso")}
                  className="text-left hover:text-blue-600"
                  title="Sort by ISO"
                >
                  Language{sortIndicator(sortField === "iso", sortOrder)}
                </button>
              </th>

              {ZONE_GROUPS.map((z) => (
                <th key={z.label} colSpan={z.colSpan} className={z.className}>
                  {z.label}
                </th>
              ))}
            </tr>

            <tr>
              {ZONE_COLUMNS.map((col) => (
                <th key={col.key} title={col.title} className={col.className}>
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100 bg-white">
            {filteredLanguages.length > 0 && (
              <tr className="bg-white">
                <td className="sticky left-0 z-10 border-r border-slate-200 bg-white px-4 py-2 text-xs text-slate-600">
                  Averages
                </td>

                {(() => {
                  const avg = (fn: (l: any) => number) =>
                    filteredLanguages.length
                      ? filteredLanguages.reduce((acc, l) => acc + fn(l), 0) /
                        filteredLanguages.length
                      : 0;

                  const aCAT = avg((l) => normalizeMetric10(l.zones?.A_RGL?.CAT));
                  const aNOUN = avg((l) => normalizeMetric10(l.zones?.A_RGL?.NOUN));
                  const aPARA = avg((l) => normalizeMetric10(l.zones?.A_RGL?.PARA));
                  const aGRAM = avg((l) => normalizeMetric10(l.zones?.A_RGL?.GRAM));
                  const aSYN = avg((l) => normalizeMetric10(l.zones?.A_RGL?.SYN));

                  const bSEED = avg((l) => normalizeMetric10(l.zones?.B_LEX?.SEED));
                  const bCONC = avg((l) => normalizeMetric10(l.zones?.B_LEX?.CONC));
                  const bWIDE = avg((l) => normalizeMetric10(l.zones?.B_LEX?.WIDE));
                  const bSEM = avg((l) => normalizeMetric10(l.zones?.B_LEX?.SEM));

                  const cPROF = avg((l) => normalizeMetric10(l.zones?.C_APP?.PROF));
                  const cASST = avg((l) => normalizeMetric10(l.zones?.C_APP?.ASST));
                  const cROUT = avg((l) => normalizeMetric10(l.zones?.C_APP?.ROUT));

                  const dBIN = avg((l) => normalizeMetric10(l.zones?.D_QA?.BIN));
                  const dTEST = avg((l) => normalizeMetric10(l.zones?.D_QA?.TEST));

                  const cells = [
                    { v: aCAT, cls: metricClass(aCAT) },
                    { v: aNOUN, cls: metricClass(aNOUN) },
                    { v: aPARA, cls: metricClass(aPARA) },
                    { v: aGRAM, cls: metricClass(aGRAM) },
                    { v: aSYN, cls: metricClass(aSYN), right: true },

                    { v: bSEED, cls: metricClass(bSEED) },
                    { v: bCONC, cls: metricClass(bCONC) },
                    { v: bWIDE, cls: metricClass(bWIDE) },
                    { v: bSEM, cls: metricClass(bSEM), right: true },

                    { v: cPROF, cls: metricClass(cPROF) },
                    { v: cASST, cls: metricClass(cASST) },
                    { v: cROUT, cls: metricClass(cROUT), right: true },

                    { v: dBIN, cls: metricClass(dBIN) },
                    { v: dTEST, cls: metricClass(dTEST) },
                  ];

                  return cells.map((c, i) => (
                    <td
                      key={`avg-${i}`}
                      className={[
                        "border-b border-slate-200 px-2 py-2 text-center text-xs font-mono",
                        c.cls,
                        c.right ? "border-r border-slate-200" : "",
                      ].join(" ")}
                      title="Average score across filtered languages (normalized to 0..10)"
                    >
                      {fmtMetric(c.v)}
                    </td>
                  ));
                })()}
              </tr>
            )}

            {filteredLanguages.length > 0 ? (
              filteredLanguages.map((lang) => (
                <LanguageRow
                  key={lang.meta?.iso || lang.meta?.name || Math.random()}
                  entry={lang}
                />
              ))
            ) : (
              <tr>
                <td colSpan={1 + ZONE_COLUMNS.length} className="py-8 text-center text-slate-400">
                  No languages found matching "{search}"
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

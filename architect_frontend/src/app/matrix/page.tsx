// architect_frontend/src/app/matrix/page.tsx
import path from "path";
import { existsSync } from "fs";
import { readFile, stat } from "fs/promises";
import type { Metadata } from "next";

import MatrixGrid from "@/components/everything-matrix/MatrixGrid";
import type { EverythingMatrix, LanguageEntry } from "@/types/EverythingMatrix";

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const fetchCache = "force-no-store";

export const metadata: Metadata = {
  title: "Everything Matrix | Semantik Architect",
  description:
    "Universal Language Maturity Index across RGL, Lexicon, Application, and QA layers.",
};

function formatTimestamp(ts: unknown): string {
  if (!ts) return "Never";

  if (typeof ts === "number") {
    const ms = ts < 1e12 ? ts * 1000 : ts;
    const d = new Date(ms);
    return Number.isNaN(d.getTime()) ? "Never" : d.toLocaleString();
  }

  if (typeof ts === "string") {
    const d = new Date(ts);
    return Number.isNaN(d.getTime()) ? "Never" : d.toLocaleString();
  }

  return "Never";
}

function formatDate(d?: Date | null): string {
  if (!d) return "Unknown";
  return Number.isNaN(d.getTime()) ? "Unknown" : d.toLocaleString();
}

type MatrixLoadResult = {
  matrix: EverythingMatrix | null;
  source: string;
  attempted: string[];
  mtime: Date | null;
  bytes: number | null;
  error: string | null;
};

/**
 * Server-side data fetch:
 * Prefer reading the generated artifact from disk.
 * We try a few candidate locations so it works whether Next is run from
 * repo root or from ./architect_frontend.
 *
 * Also surfaces file mtime + size to debug "timestamp didn't change" cases.
 */
async function getMatrixData(): Promise<MatrixLoadResult> {
  const cwd = process.cwd();

  const candidates = [
    // If Next runs from repo root
    path.resolve(cwd, "data/indices/everything_matrix.json"),
    // If Next runs from ./architect_frontend
    path.resolve(cwd, "..", "data/indices/everything_matrix.json"),
    // Extra safety if cwd is deeper than expected
    path.resolve(cwd, "..", "..", "data/indices/everything_matrix.json"),
    // Common Next build/server cwd edge case: ./architect_frontend/.next
    path.resolve(cwd, "..", "..", "..", "data/indices/everything_matrix.json"),
  ];

  let lastErr: unknown = null;

  for (const p of candidates) {
    try {
      if (!existsSync(p)) continue;

      const raw = await readFile(p, "utf-8");
      const parsed = JSON.parse(raw) as EverythingMatrix;

      // Optional safety check: matrix keys should be iso2 (2 letters).
      // We do not fail hard to keep UI resilient; we only surface a console hint.
      const keys = parsed?.languages ? Object.keys(parsed.languages) : [];
      const nonIso2 = keys.find((k) => (k ?? "").length !== 2);
      if (nonIso2) {
        // eslint-disable-next-line no-console
        console.warn(
          `[EverythingMatrix] Non-iso2 key detected ("${nonIso2}"). Expected iso2 keys (e.g. "en","fr").`
        );
      }

      const st = await stat(p);

      return {
        matrix: parsed,
        source: p,
        attempted: candidates,
        mtime: st.mtime ?? null,
        bytes: typeof st.size === "number" ? st.size : null,
        error: null,
      };
    } catch (e) {
      lastErr = e;
    }
  }

  return {
    matrix: null,
    source: candidates[0],
    attempted: candidates,
    mtime: null,
    bytes: null,
    error: lastErr ? String(lastErr) : null,
  };
}

// -----------------------------------------------------------------------------
// UI helpers: compute a "completion level" + a lightweight color label
// (kept here so we don't need to modify the backend artifact schema)
// -----------------------------------------------------------------------------
//
// Canonical assumptions for v2+:
// - matrix.languages keys are iso2
// - entry.meta.iso is also iso2
// -----------------------------------------------------------------------------

type CompletionLevel =
  | "complete"
  | "good"
  | "partial"
  | "seeded"
  | "missing"
  | "unrunnable";

function levelFromLanguage(entry: LanguageEntry): CompletionLevel {
  const maturity = entry?.verdict?.maturity_score ?? 0;
  const runnable = entry?.verdict?.runnable ?? false;

  if (!runnable) return "unrunnable";
  if (maturity >= 8.5) return "complete";
  if (maturity >= 7.0) return "good";
  if (maturity >= 4.0) return "partial";
  if (maturity >= 2.0) return "seeded";
  return "missing";
}

function levelBadgeClass(level: CompletionLevel): string {
  switch (level) {
    case "complete":
      return "bg-emerald-100 text-emerald-800 border-emerald-200";
    case "good":
      return "bg-green-100 text-green-800 border-green-200";
    case "partial":
      return "bg-amber-100 text-amber-800 border-amber-200";
    case "seeded":
      return "bg-blue-100 text-blue-800 border-blue-200";
    case "missing":
      return "bg-slate-100 text-slate-700 border-slate-200";
    case "unrunnable":
      return "bg-rose-100 text-rose-800 border-rose-200";
  }
}

function safeObjectKeys(obj: unknown): string[] {
  return obj && typeof obj === "object" ? Object.keys(obj as any) : [];
}

export default async function EverythingMatrixPage() {
  const { matrix: matrixData, source, attempted, mtime, bytes, error } =
    await getMatrixData();

  const fileTimestamp = formatDate(mtime);
  const timestamp = formatTimestamp((matrixData as any)?.timestamp);
  const timestampIso = formatTimestamp((matrixData as any)?.timestamp_iso);
  const scoringVersion =
    typeof (matrixData as any)?.scoring_version === "string"
      ? ((matrixData as any).scoring_version as string)
      : null;

  const languageKeys = safeObjectKeys(matrixData?.languages);
  const languageCount = languageKeys.length;

  const rollup = (() => {
    if (!matrixData?.languages) {
      return {
        complete: 0,
        good: 0,
        partial: 0,
        seeded: 0,
        missing: 0,
        unrunnable: 0,
      };
    }

    const counts = {
      complete: 0,
      good: 0,
      partial: 0,
      seeded: 0,
      missing: 0,
      unrunnable: 0,
    };

    for (const k of languageKeys) {
      const entry = (matrixData.languages as any)[k] as LanguageEntry | undefined;
      const lvl = entry ? levelFromLanguage(entry) : "missing";
      (counts as any)[lvl] += 1;
    }
    return counts;
  })();

  return (
    <main className="min-h-screen bg-slate-50 p-6 md:p-12">
      <div className="mx-auto max-w-[1600px] space-y-8">
        <header className="flex flex-col gap-4 border-b border-slate-200 pb-6 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">
              The Everything Matrix
            </h1>
            <p className="mt-2 text-slate-500">
              Centralized orchestration dashboard tracking language maturity from
              RGL to Production.
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Canonical keys: ISO-639-1 (iso2), lowercase (e.g. “en”, “fr”).
              {scoringVersion ? ` Scoring: ${scoringVersion}.` : null}
            </p>

            <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
              {(
                [
                  ["complete", rollup.complete],
                  ["good", rollup.good],
                  ["partial", rollup.partial],
                  ["seeded", rollup.seeded],
                  ["missing", rollup.missing],
                  ["unrunnable", rollup.unrunnable],
                ] as Array<[CompletionLevel, number]>
              ).map(([lvl, n]) => (
                <span
                  key={lvl}
                  className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 font-medium ${levelBadgeClass(
                    lvl
                  )}`}
                  title="Derived from maturity_score + runnable"
                >
                  <span className="capitalize">{lvl}</span>
                  <span className="font-mono">{n}</span>
                </span>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-6 text-sm">
            <div className="text-right">
              <p className="text-slate-500">Languages Tracked</p>
              <p className="font-mono text-lg font-semibold text-slate-900">
                {languageCount}
              </p>
            </div>
            <div className="text-right">
              <p className="text-slate-500">Last Audit (file timestamp)</p>
              <p className="font-mono font-medium text-slate-700">
                {fileTimestamp}
              </p>
            </div>
            <div className="text-right">
              <p className="text-slate-500">Last Audit (matrix.timestamp)</p>
              <p className="font-mono font-medium text-slate-700">{timestamp}</p>
              {timestampIso !== "Never" ? (
                <p className="font-mono text-[11px] text-slate-500">
                  {timestampIso}
                </p>
              ) : null}
            </div>
          </div>
        </header>

        {matrixData ? (
          <div className="space-y-4">
            <MatrixGrid matrix={matrixData} />

            <div className="rounded-lg border border-slate-200 bg-white p-4 text-xs text-slate-700">
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div className="min-w-0">
                  <span className="text-slate-500">Loaded from:</span>{" "}
                  <span className="font-mono break-all">{source}</span>
                </div>
                <div className="flex items-center gap-6">
                  <div>
                    <span className="text-slate-500">Bytes:</span>{" "}
                    <span className="font-mono">{bytes ?? "Unknown"}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Attempted:</span>{" "}
                    <span className="font-mono">{attempted.length}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-lg border border-slate-200 bg-white p-6">
            <h2 className="text-lg font-semibold text-slate-900">
              Matrix not found
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              Could not locate{" "}
              <span className="font-mono">
                data/indices/everything_matrix.json
              </span>
              .
            </p>
            <p className="mt-2 text-sm text-slate-600">
              Attempted (first existing wins):{" "}
              <span className="font-mono">{attempted.join(" | ")}</span>
            </p>
            {error ? (
              <p className="mt-2 text-sm text-slate-600">
                Last error: <span className="font-mono">{error}</span>
              </p>
            ) : null}
            <div className="mt-4 text-sm text-slate-700">
              To generate it, run:{" "}
              <span className="font-mono">
                python tools/everything_matrix/build_index.py
              </span>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

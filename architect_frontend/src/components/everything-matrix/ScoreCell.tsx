// architect_frontend/src/components/everything-matrix/ScoreCell.tsx
import React from "react";

type ScoreScale = "auto" | "0-10" | "0-1";

interface ScoreCellProps {
  score: number;
  isZoneEnd?: boolean;

  /**
   * Optional extra numeric detail (e.g., COUNT_CORE, COUNT_TOTAL, QID_RATIO*100).
   * If provided, it will be shown as a small sublabel and as a title tooltip.
   */
  detail?: number | string;

  /**
   * Optional label for the detail (used in tooltip only).
   * Example: "core", "total", "qid%"
   */
  detailLabel?: string;

  /**
   * If true, render 0 as "0" instead of "—".
   */
  showZero?: boolean;

  /**
   * Score scale:
   *  - "0-10": treat score as 0..10 (default intended)
   *  - "0-1" : treat score as 0..1 and render scaled to 0..10
   *  - "auto": if score is a non-integer in [0,1], assume 0..1; otherwise assume 0..10
   */
  scale?: ScoreScale;

  /**
   * Optional: override how many decimals to show for non-integers (default: 1).
   */
  decimals?: number;
}

function fmtDetail(v: number | string): string {
  if (typeof v === "number") {
    if (!Number.isFinite(v)) return "";
    if (Number.isInteger(v)) return String(v);
    return String(Math.round(v * 100) / 100);
  }
  return String(v);
}

function clamp(n: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, n));
}

function normalizeScore(raw: number, scale: ScoreScale): number {
  const s = Number.isFinite(raw) ? raw : 0;

  if (scale === "0-1") return clamp(s * 10, 0, 10);
  if (scale === "0-10") return clamp(s, 0, 10);

  // auto
  // If it's a non-integer in [0,1], it's almost certainly a pass-rate (0..1) => scale to 0..10.
  // Keep 0 and 1 unscaled to avoid turning "Planned=1" into "10" accidentally.
  if (s > 0 && s < 1 && !Number.isInteger(s)) return clamp(s * 10, 0, 10);
  return clamp(s, 0, 10);
}

function fmtScore(s: number, decimals: number): string {
  if (!Number.isFinite(s)) return "0";
  if (Number.isInteger(s)) return String(s);
  const d = Math.max(0, Math.min(3, decimals));
  const f = Number(s.toFixed(d));
  // avoid trailing ".0"
  return Number.isInteger(f) ? String(f) : String(f);
}

// Ladder-aligned bands (0 absent → 1 planned → 3 scaffolded → 5 draft → 7 beta → 8 pre-final → 10 final)
function scoreBand(s: number): { label: string; bg: string; text: string } {
  if (s === 0) {
    return {
      label: "Absent",
      bg: "bg-slate-50",
      text: "text-slate-300",
    };
  }

  // 1–2 planned
  if (s > 0 && s < 3) {
    return {
      label: "Planned",
      bg: "bg-slate-100",
      text: "text-slate-700 font-medium",
    };
  }

  // 3–4 scaffolded
  if (s >= 3 && s < 5) {
    return {
      label: "Scaffolded",
      bg: "bg-amber-50",
      text: "text-amber-800 font-medium",
    };
  }

  // 5–6 draft
  if (s >= 5 && s < 7) {
    return {
      label: "Draft",
      bg: "bg-orange-50",
      text: "text-orange-800 font-semibold",
    };
  }

  // 7 beta
  if (s >= 7 && s < 8) {
    return {
      label: "Beta",
      bg: "bg-blue-50",
      text: "text-blue-800 font-semibold",
    };
  }

  // 8 pre-final
  if (s >= 8 && s < 9) {
    return {
      label: "Pre-final",
      bg: "bg-sky-50",
      text: "text-sky-800 font-bold",
    };
  }

  // 9 near-final
  if (s >= 9 && s < 10) {
    return {
      label: "Near-final",
      bg: "bg-emerald-50",
      text: "text-emerald-800 font-bold",
    };
  }

  // 10 final
  return {
    label: "Final",
    bg: "bg-emerald-100",
    text: "text-emerald-900 font-extrabold",
  };
}

export default function ScoreCell({
  score,
  isZoneEnd = false,
  detail,
  detailLabel,
  showZero = false,
  scale = "auto",
  decimals = 1,
}: ScoreCellProps) {
  const normalized = normalizeScore(score, scale);
  const band = scoreBand(normalized);

  const hasDetail = detail !== undefined && detail !== null && fmtDetail(detail) !== "";
  const detailText = hasDetail ? fmtDetail(detail) : "";

  // Tooltip: always include band + numeric score; optionally include detail.
  const titleParts: string[] = [];
  titleParts.push(`${band.label} (${fmtScore(normalized, decimals)}/10)`);
  if (hasDetail) {
    titleParts.push(`${detailLabel ? `${detailLabel}: ` : ""}${detailText}`);
  }
  const title = titleParts.join(" • ");

  const mainText = normalized === 0 && !showZero ? "—" : fmtScore(normalized, decimals);

  return (
    <td
      title={title}
      className={`
        relative border-b border-slate-200 px-2 py-2 text-center text-sm align-middle
        transition-all duration-150 hover:brightness-95 cursor-default
        ${isZoneEnd ? "border-r-2 border-r-slate-200" : "border-r border-r-slate-100"}
        ${band.bg}
      `}
    >
      <div className="flex flex-col items-center justify-center leading-tight">
        <span className={band.text}>{mainText}</span>

        {/* Optional: small secondary line for counts/percentages */}
        {hasDetail && (
          <span
            className={`
              mt-0.5 text-[10px]
              ${normalized === 0 ? "text-slate-300" : "text-slate-500"}
            `}
          >
            {detailText}
          </span>
        )}
      </div>

      {/* Tiny visual indicator for perfect scores */}
      {normalized === 10 && (
        <span className="absolute top-1 right-1 h-1.5 w-1.5 rounded-full bg-emerald-600 opacity-60" />
      )}
    </td>
  );
}

// architect_frontend/src/app/tools/utils.ts

import type { ToolRunResponse } from "./types";

// ----------------------------------------------------------------------------
// Small helpers
// ----------------------------------------------------------------------------

export function docsHref(key: string) {
  return `#${key}`;
}

export function normalizeBaseUrl(raw: string) {
  return (raw || "").replace(/\/+$/, "");
}

export function normalizeApiV1(rawBase: string) {
  const base = normalizeBaseUrl(rawBase);
  return base.endsWith("/api/v1") ? base : `${base}/api/v1`;
}

export function normalizeRepoUrl(raw: string) {
  return normalizeBaseUrl(raw);
}

// Keep "main" as default branch (consistent with current UI),
// but allow override via NEXT_PUBLIC_REPO_BRANCH.
export function repoFileUrl(repoUrl: string, path: string) {
  const base = normalizeRepoUrl(repoUrl);
  if (!base) return "";
  const branch = (process.env.NEXT_PUBLIC_REPO_BRANCH || "main").trim() || "main";
  // Avoid accidental leading slash on path producing double slashes
  const cleanPath = (path || "").replace(/^\/+/, "");
  return `${base}/blob/${branch}/${cleanPath}`;
}

/**
 * Utility: small, safe classnames combiner (no dependency).
 */
export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function safeJsonParse<T>(
  s: string
): { ok: true; value: T } | { ok: false; error: unknown } {
  try {
    return { ok: true, value: JSON.parse(s) as T };
  } catch (e) {
    return { ok: false, error: e };
  }
}

// ----------------------------------------------------------------------------
// Minimal shell-ish parser (whitespace split + quotes + backslash escapes).
// Intentionally simple; backend still validates/allowlists flags.
// Improvements:
// - Handles trailing backslash gracefully
// - Backslash escapes in double-quotes (common shell behavior)
// - Unmatched quotes are treated as "consume until end"
// ----------------------------------------------------------------------------
export function parseCliArgs(input: string): string[] {
  const out: string[] = [];
  let buf = "";

  type Mode = "none" | "single" | "double";
  let mode: Mode = "none";

  const push = () => {
    if (buf.length) out.push(buf);
    buf = "";
  };

  for (let i = 0; i < input.length; i++) {
    const ch = input[i];

    // Whitespace splits only when not inside quotes
    if (mode === "none" && /\s/.test(ch)) {
      push();
      continue;
    }

    // Quote toggles (only if not in the other quote mode)
    if (ch === "'" && mode !== "double") {
      mode = mode === "single" ? "none" : "single";
      continue;
    }
    if (ch === `"` && mode !== "single") {
      mode = mode === "double" ? "none" : "double";
      continue;
    }

    // Backslash escaping:
    // - in single quotes: literal backslash (shell-like)
    // - otherwise: escapes next char if present; if not present keep backslash
    if (ch === "\\") {
      if (mode === "single") {
        buf += ch;
        continue;
      }
      if (i + 1 < input.length) {
        buf += input[i + 1];
        i++;
        continue;
      }
      buf += ch;
      continue;
    }

    buf += ch;
  }

  push();
  return out;
}

// ----------------------------------------------------------------------------
// Clipboard
// ----------------------------------------------------------------------------

/**
 * Best-effort clipboard helper.
 * Returns true if it likely succeeded, false otherwise.
 *
 * SSR-safe: returns false when window/navigator/document aren't available.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  if (typeof window === "undefined") return false;

  // Modern async clipboard API (secure contexts only)
  try {
    if (globalThis.isSecureContext && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // fall through to legacy path
  }

  // Legacy fallback: execCommand('copy')
  try {
    if (typeof document === "undefined") return false;

    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "true");

    // Keep off-screen but selectable
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    ta.style.top = "0";

    const active = document.activeElement as HTMLElement | null;

    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    ta.setSelectionRange(0, ta.value.length);

    const ok = document.execCommand("copy");

    document.body.removeChild(ta);
    active?.focus?.();

    return ok;
  } catch {
    return false;
  }
}

// ----------------------------------------------------------------------------
// Rich Response Normalization & Formatting
// ----------------------------------------------------------------------------

function asString(v: unknown, fallback = ""): string {
  if (typeof v === "string") return v;
  if (v == null) return fallback;
  // Try to preserve useful output (objects/arrays)
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

function asNumber(v: unknown, fallback = 0): number {
  return typeof v === "number" && Number.isFinite(v) ? v : fallback;
}

function asArray<T = unknown>(v: unknown): T[] {
  return Array.isArray(v) ? (v as T[]) : [];
}

/**
 * Ensures any API response (legacy or new) fits the ToolRunResponse shape.
 * Handles missing fields, legacy output/error keys, and defaults.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizeToolResponse(data: any): ToolRunResponse {
  const nowIso = new Date().toISOString();

  const success = Boolean(data?.success);

  // Prefer streams; fallback to legacy aliases
  const stdout = asString(data?.stdout ?? data?.output ?? "", "");
  const stderr = asString(data?.stderr ?? data?.error ?? "", "");

  const toolObj = data?.tool && typeof data.tool === "object" ? data.tool : null;

  return {
    trace_id: asString(data?.trace_id, `sim-${Date.now()}`),
    success,
    command: asString(data?.command, ""),

    // Streams
    stdout,
    stderr,
    stdout_chars: asNumber(data?.stdout_chars, stdout.length),
    stderr_chars: asNumber(data?.stderr_chars, stderr.length),

    // Legacy aliases
    output: stdout,
    error: stderr,

    // Lifecycle
    exit_code:
      typeof data?.exit_code === "number"
        ? data.exit_code
        : typeof data?.return_code === "number"
        ? data.return_code
        : success
        ? 0
        : 1,
    duration_ms: asNumber(data?.duration_ms, 0),
    started_at: asString(data?.started_at, nowIso),
    ended_at: asString(data?.ended_at, nowIso),

    // Metadata
    cwd: asString(data?.cwd, "~"),
    repo_root: asString(data?.repo_root, ""),
    tool: toolObj
      ? {
          id: asString(toolObj.id, "unknown"),
          label: asString(toolObj.label, "Unknown Tool"),
          description: asString(toolObj.description, ""),
          timeout_sec: asNumber(toolObj.timeout_sec, 0),
        }
      : {
          id: "unknown",
          label: "Unknown Tool",
          description: "",
          timeout_sec: 0,
        },

    // Arguments
    args_received: asArray<string>(data?.args_received),
    args_accepted: asArray<string>(data?.args_accepted),
    args_rejected: asArray(data?.args_rejected),

    // Telemetry
    truncation:
      data?.truncation && typeof data.truncation === "object"
        ? {
            stdout: Boolean(data.truncation.stdout),
            stderr: Boolean(data.truncation.stderr),
            limit_chars: asNumber(data.truncation.limit_chars, 0),
          }
        : { stdout: false, stderr: false, limit_chars: 0 },
    events: asArray(data?.events),
  };
}

export function formatBytes(bytes: number, decimals = 1): string {
  const b = typeof bytes === "number" && Number.isFinite(bytes) ? bytes : 0;
  if (b <= 0) return "0 B";

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(sizes.length - 1, Math.floor(Math.log(b) / Math.log(k)));

  const value = b / Math.pow(k, i);
  return `${parseFloat(value.toFixed(dm))} ${sizes[i]}`;
}

export function formatDuration(ms: number): string {
  const n = typeof ms === "number" && Number.isFinite(ms) ? ms : 0;
  if (n < 1000) return `${Math.round(n)}ms`;

  const s = n / 1000;
  if (s < 60) return `${s.toFixed(2)}s`;

  const m = Math.floor(s / 60);
  const rem = s - m * 60;
  if (m < 60) return `${m}m ${rem.toFixed(1)}s`;

  const h = Math.floor(m / 60);
  const remM = m - h * 60;
  return `${h}h ${remM}m`;
}

const _timeFmt =
  typeof Intl !== "undefined"
    ? new Intl.DateTimeFormat(undefined, {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        fractionalSecondDigits: 3,
      })
    : null;

export function formatTime(isoString: string): string {
  if (!isoString) return "";
  try {
    const d = new Date(isoString);
    if (Number.isNaN(d.getTime())) return isoString;
    return _timeFmt ? _timeFmt.format(d) : d.toISOString();
  } catch {
    return isoString;
  }
}

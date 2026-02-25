// architect_frontend/src/app/tools/hooks/useToolsArgs.ts
"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Dispatch, SetStateAction } from "react";

export type ArgsByToolId = Record<string, string>;

type UseToolsArgsOptions = {
  storageKey?: string;
  /** Debounce localStorage writes (typing-friendly). Default: 250ms */
  debounceMs?: number;
  /** Turn persistence on/off (still keeps in-memory state). Default: true */
  enabled?: boolean;
  /** Optional initial seed merged under persisted values. */
  initial?: ArgsByToolId;
};

type UseToolsArgsReturn = {
  argsByToolId: ArgsByToolId;
  getArgs: (toolId: string) => string;
  setArgs: (toolId: string, value: string) => void;
  removeArgs: (toolId: string) => void;
  clearArgs: () => void;

  /** For advanced usage (bulk edits). */
  setArgsByToolId: Dispatch<SetStateAction<ArgsByToolId>>;

  /** Force a write to localStorage immediately (bypasses debounce). */
  persistNow: () => void;
};

const DEFAULT_STORAGE_KEY = "tools_dashboard_args_v1";

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function safeParseArgsMap(raw: string | null | undefined): ArgsByToolId {
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!isPlainObject(parsed)) return {};
    const out: ArgsByToolId = {};
    for (const [k, v] of Object.entries(parsed)) {
      if (typeof v === "string") out[k] = v;
    }
    return out;
  } catch {
    return {};
  }
}

function shallowEqualRecord(a: ArgsByToolId, b: ArgsByToolId): boolean {
  if (a === b) return true;
  const ak = Object.keys(a);
  const bk = Object.keys(b);
  if (ak.length !== bk.length) return false;
  for (const k of ak) {
    if (a[k] !== b[k]) return false;
  }
  return true;
}

function canUseStorage(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const k = "__storage_test__";
    window.localStorage.setItem(k, "1");
    window.localStorage.removeItem(k);
    return true;
  } catch {
    return false;
  }
}

// ----------------------------------------------------------------------------
// Secret hygiene: never persist secrets to localStorage.
// Best-effort redaction for common CLI patterns: --flag VALUE and --flag=VALUE.
// ----------------------------------------------------------------------------
const SENSITIVE_FLAGS = [
  "--api-key",
  "--api_key",
  "--apikey",
  "--token",
  "--access-token",
  "--auth-token",
  "--password",
  "--pass",
  "--secret",
  "--client-secret",
] as const;

function redactSensitiveArgsString(input: string): string {
  if (!input) return input;

  // 1) --flag=value  (preserve flag, redact value)
  // 2) --flag value  (preserve flag, redact following token)
  //
  // Note: args strings may not be strictly tokenized; this is best-effort.
  const flagsAlt = SENSITIVE_FLAGS.map((f) => f.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");

  // --flag=VALUE
  const eqRe = new RegExp(`\\b(${flagsAlt})=([^\\s]+)`, "gi");

  // --flag VALUE (VALUE may be quoted or unquoted)
  // captures:
  //   group2 = quoted "..."/'...' OR unquoted token
  const wsRe = new RegExp(`\\b(${flagsAlt})\\s+(".*?"|'.*?'|[^\\s]+)`, "gi");

  let out = input.replace(eqRe, (_m, flag) => `${flag}=***`);
  out = out.replace(wsRe, (_m, flag) => `${flag} ***`);
  return out;
}

function sanitizeArgsMapForStorage(map: ArgsByToolId): ArgsByToolId {
  // Only sanitize on persistence; keep in-memory state untouched.
  const out: ArgsByToolId = {};
  for (const [toolId, argsStr] of Object.entries(map)) {
    if (typeof argsStr !== "string") continue;
    out[toolId] = redactSensitiveArgsString(argsStr);
  }
  return out;
}

export function useToolsArgs(options: UseToolsArgsOptions = {}): UseToolsArgsReturn {
  const { storageKey = DEFAULT_STORAGE_KEY, debounceMs = 250, enabled = true, initial = {} } = options;

  const storageOk = enabled && canUseStorage();

  // Lazy init: read localStorage once (sanitize anything old that may contain secrets).
  const [argsByToolId, setArgsByToolId] = useState<ArgsByToolId>(() => {
    if (!storageOk) return { ...initial };
    const persistedRaw = safeParseArgsMap(window.localStorage.getItem(storageKey));
    const persisted = sanitizeArgsMapForStorage(persistedRaw);
    // Persisted wins (so user doesn't lose last typed values)
    return { ...initial, ...persisted };
  });

  // Keep latest state in a ref for debounced persistence.
  const stateRef = useRef(argsByToolId);
  useEffect(() => {
    stateRef.current = argsByToolId;
  }, [argsByToolId]);

  // Debounced persistence (avoids JSON.stringify on every keystroke write).
  const writeTimer = useRef<number | null>(null);
  const lastWritten = useRef<string>("");

  const persistNow = useCallback(() => {
    if (!storageOk) return;
    try {
      const safeState = sanitizeArgsMapForStorage(stateRef.current);
      const json = JSON.stringify(safeState);
      if (json !== lastWritten.current) {
        window.localStorage.setItem(storageKey, json);
        lastWritten.current = json;
      }
    } catch {
      // ignore
    }
  }, [storageKey, storageOk]);

  useEffect(() => {
    if (!storageOk) return;

    if (writeTimer.current) window.clearTimeout(writeTimer.current);
    writeTimer.current = window.setTimeout(() => {
      persistNow();
    }, debounceMs);

    return () => {
      if (writeTimer.current) {
        window.clearTimeout(writeTimer.current);
        writeTimer.current = null;
      }
    };
  }, [argsByToolId, debounceMs, persistNow, storageOk]);

  // Cross-tab sync: update state if another tab writes the same key.
  useEffect(() => {
    if (!storageOk) return;

    const onStorage = (e: StorageEvent) => {
      if (e.storageArea !== window.localStorage) return;
      if (e.key !== storageKey) return;

      const nextRaw = safeParseArgsMap(e.newValue);
      const next = sanitizeArgsMapForStorage(nextRaw);
      setArgsByToolId((prev) => (shallowEqualRecord(prev, next) ? prev : next));
    };

    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [storageKey, storageOk]);

  const getArgs = useCallback((toolId: string) => argsByToolId[toolId] ?? "", [argsByToolId]);

  const setArgs = useCallback((toolId: string, value: string) => {
    setArgsByToolId((prev) => {
      if (prev[toolId] === value) return prev; // tiny optimization
      return { ...prev, [toolId]: value };
    });
  }, []);

  const removeArgs = useCallback((toolId: string) => {
    setArgsByToolId((prev) => {
      if (!(toolId in prev)) return prev;
      const next = { ...prev };
      delete next[toolId];
      return next;
    });
  }, []);

  const clearArgs = useCallback(() => {
    setArgsByToolId({});
  }, []);

  // Stable API object (nice for prop drilling, avoids re-renders)
  return useMemo(
    () => ({
      argsByToolId,
      getArgs,
      setArgs,
      removeArgs,
      clearArgs,
      setArgsByToolId,
      persistNow,
    }),
    [argsByToolId, getArgs, setArgs, removeArgs, clearArgs, persistNow]
  );
}
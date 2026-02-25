// architect_frontend/src/app/tools/hooks/useHealthReady.ts
"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export type HealthReady = {
  broker?: string;
  storage?: string;
  engine?: string;
};

export type UseHealthReadyOptions = {
  /**
   * If false, the hook will not fetch automatically and refresh() becomes a no-op.
   */
  enabled?: boolean;
  /**
   * If true, fetch once on mount (default true).
   */
  initialFetch?: boolean;
  /**
   * If set (ms), auto-refresh on an interval. Set to null/0 to disable.
   */
  pollIntervalMs?: number | null;
  /**
   * Optional extra fetch init (headers, credentials, etc). `signal` will be overridden.
   */
  fetchInit?: RequestInit;
};

type UseHealthReadyResult = {
  health: HealthReady | null;
  loading: boolean;
  error: Error | null;
  lastUpdatedAt: number | null;
  refresh: () => Promise<HealthReady | null>;
  cancel: () => void;
};

function toError(e: unknown): Error {
  if (e instanceof Error) return e;
  return new Error(typeof e === "string" ? e : JSON.stringify(e));
}

async function safeReadJson(res: Response): Promise<unknown | null> {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Fetches /health/ready and exposes loading/error + refresh/cancel.
 * Designed to be stable under rapid refresh clicks and component unmounts.
 */
export function useHealthReady(apiV1: string, opts?: UseHealthReadyOptions): UseHealthReadyResult {
  const options = useMemo(
    () => ({
      enabled: true,
      initialFetch: true,
      pollIntervalMs: null as number | null,
      fetchInit: undefined as RequestInit | undefined,
      ...(opts ?? {}),
    }),
    [opts]
  );

  const [health, setHealth] = useState<HealthReady | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<number | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const inflightRef = useRef<Promise<HealthReady | null> | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      abortRef.current?.abort();
      abortRef.current = null;
      inflightRef.current = null;
    };
  }, []);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    inflightRef.current = null;
    // Best-effort UI reset; no harm if already false.
    setLoading(false);
  }, []);

  const refresh = useCallback(async (): Promise<HealthReady | null> => {
    if (!options.enabled) return null;

    // Deduplicate concurrent refresh calls
    if (inflightRef.current) return inflightRef.current;

    // Abort any previous request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);

    const p = (async () => {
      try {
        const init: RequestInit = {
          cache: "no-store",
          ...(options.fetchInit ?? {}),
          signal: controller.signal, // ensure ours wins
        };

        const res = await fetch(`${apiV1}/health/ready`, init);
        const body = await safeReadJson(res);

        if (!res.ok) {
          const msg =
            body && typeof body === "object"
              ? JSON.stringify(body)
              : `${res.status} ${res.statusText}`.trim();
          throw new Error(`Health check failed: ${msg}`);
        }

        const next: HealthReady =
          body && typeof body === "object" ? (body as HealthReady) : {};

        if (mountedRef.current) {
          setHealth(next);
          setLastUpdatedAt(Date.now());
        }

        return next;
      } catch (e: any) {
        // Abort is not an error state; treat as null result.
        if (e?.name === "AbortError") return null;

        if (mountedRef.current) {
          setHealth(null);
          setError(toError(e));
        }
        return null;
      } finally {
        if (mountedRef.current) setLoading(false);
        inflightRef.current = null;
      }
    })();

    inflightRef.current = p;
    return p;
  }, [apiV1, options.enabled, options.fetchInit]);

  useEffect(() => {
    if (!options.enabled) return;
    if (options.initialFetch) void refresh();
  }, [options.enabled, options.initialFetch, refresh]);

  useEffect(() => {
    if (!options.enabled) return;
    const ms = options.pollIntervalMs;
    if (!ms || ms <= 0) return;

    const id = window.setInterval(() => void refresh(), ms);
    return () => window.clearInterval(id);
  }, [options.enabled, options.pollIntervalMs, refresh]);

  return { health, loading, error, lastUpdatedAt, refresh, cancel };
}

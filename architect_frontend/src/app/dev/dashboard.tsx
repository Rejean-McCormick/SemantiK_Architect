"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Activity,
  Database,
  Server,
  RefreshCw,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import type { TestDefinition } from "@/types/test-runner";

interface SystemHealth {
  broker: "up" | "down";
  storage: "up" | "down";
  engine: "up" | "down";
}

// Some deployments return { components: { broker, storage, engine } }
type SystemHealthResponse = SystemHealth | { components: SystemHealth };

interface DevDashboardProps {
  availableTests: TestDefinition[];
}

const ENV_API_BASE = process.env.NEXT_PUBLIC_ARCHITECT_API_BASE_URL || "";
const DEFAULT_BACKEND_ORIGIN = "http://localhost:8000";

function stripTrailingSlash(s: string) {
  return (s || "").replace(/\/+$/, "");
}

function dedupe(list: string[]) {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const x of list) {
    const v = (x || "").trim();
    if (!v) continue;
    if (!seen.has(v)) {
      seen.add(v);
      out.push(v);
    }
  }
  return out;
}

function buildCandidateApiBases(envBaseRaw: string): string[] {
  const envBase = stripTrailingSlash(envBaseRaw);

  const candidates: string[] = [];

  // 1) If user configured an API base, try it first.
  if (envBase) candidates.push(envBase);

  // 2) If envBase is absolute URL, also probe common layouts on that origin.
  try {
    const u = new URL(envBase);
    const origin = u.origin;

    // If they provided a versioned base (/api/v1...), also try origin defaults.
    candidates.push(`${origin}/api/v1`);
    candidates.push(`${origin}/abstract_wiki_architect/api/v1`);

    // If they provided a mounted prefix (/abstract_wiki_architect/...), also try adding /api/v1.
    if (u.pathname.replace(/\/+$/, "").endsWith("/abstract_wiki_architect")) {
      candidates.push(`${origin}/abstract_wiki_architect/api/v1`);
    }
  } catch {
    // envBase might be relative (e.g. "/abstract_wiki_architect/api/v1") — that's fine.
    // Also probe both common relative prefixes for same-origin deployments.
    candidates.push("/api/v1");
    candidates.push("/abstract_wiki_architect/api/v1");
  }

  // 3) Always include localhost dev defaults (Next:3000 + API:8000).
  candidates.push(`${DEFAULT_BACKEND_ORIGIN}/api/v1`);
  candidates.push(`${DEFAULT_BACKEND_ORIGIN}/abstract_wiki_architect/api/v1`);

  return dedupe(candidates.map(stripTrailingSlash));
}

function buildUrl(apiBase: string, endpoint: string) {
  const raw = (endpoint || "").trim();

  // Full URL in the test definition (rare, but allow it)
  if (/^https?:\/\//i.test(raw)) return raw;

  const base = stripTrailingSlash(apiBase);

  // If endpoint is absolute path, treat it as absolute-from-origin if apiBase is absolute.
  if (raw.startsWith("/")) {
    try {
      const u = new URL(base);
      return `${u.origin}${raw}`;
    } catch {
      // apiBase might be relative; return absolute-from-current-origin
      return raw;
    }
  }

  // Relative endpoint => append to apiBase.
  return `${base}/${raw.replace(/^\//, "")}`;
}

async function probeReady(apiBase: string, timeoutMs = 2500): Promise<boolean> {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(buildUrl(apiBase, "health/ready"), {
      method: "GET",
      signal: controller.signal,
    });
    return res.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(t);
  }
}

async function resolveApiBase(envBaseRaw: string): Promise<string | null> {
  const cands = buildCandidateApiBases(envBaseRaw);
  for (const c of cands) {
    // Only accept bases that actually respond on /health/ready.
    // (This auto-fixes the "/api/v1" vs "/abstract_wiki_architect/api/v1" mismatch.)
    // eslint-disable-next-line no-await-in-loop
    if (await probeReady(c)) return c;
  }
  return null;
}

export default function DevDashboard({ availableTests = [] }: DevDashboardProps) {
  const [status, setStatus] = useState<"CONNECTING" | "ONLINE" | "OFFLINE">(
    "CONNECTING"
  );
  const [healthDetails, setHealthDetails] = useState<SystemHealth | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isDiagnosing, setIsDiagnosing] = useState(false);

  // Keep the resolved API base visible/usable for both diagnosis + tests.
  const [apiBase, setApiBase] = useState<string>(stripTrailingSlash(ENV_API_BASE));

  // Test Runner State
  const [selectedTestId, setSelectedTestId] = useState<string>(
    availableTests.length > 0 ? availableTests[0].id : ""
  );
  const [testResult, setTestResult] = useState<string | null>(null);
  const [isRunningTest, setIsRunningTest] = useState(false);

  // Update selectedTestId if availableTests loads later or changes
  useEffect(() => {
    if (availableTests.length > 0 && !selectedTestId) {
      setSelectedTestId(availableTests[0].id);
    }
  }, [availableTests, selectedTestId]);

  const activeTest = availableTests.find((t) => t.id === selectedTestId);

  const ensureApiBase = useCallback(async () => {
    const resolved = await resolveApiBase(ENV_API_BASE);
    if (resolved) {
      setApiBase(resolved);
      return resolved;
    }
    return null;
  }, []);

  // --- 1. DIAGNOSIS SYSTEM ---
  const runDiagnosis = useCallback(async () => {
    setIsDiagnosing(true);
    setStatus("CONNECTING");

    try {
      const resolved = await ensureApiBase();
      if (!resolved) {
        setStatus("OFFLINE");
        setHealthDetails(null);
        return;
      }

      const res = await fetch(buildUrl(resolved, "health/ready"));
      if (res.ok) {
        const data: SystemHealthResponse = await res.json();
        const details = "components" in data ? data.components : data;
        setHealthDetails(details);
        setStatus("ONLINE");
      } else {
        setStatus("OFFLINE");
        setHealthDetails(null);
      }
    } catch {
      setStatus("OFFLINE");
      setHealthDetails(null);
    } finally {
      setLastUpdated(new Date());
      setIsDiagnosing(false);
    }
  }, [ensureApiBase]);

  useEffect(() => {
    runDiagnosis();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- 2. TEST RUNNER ---
  const runTest = async () => {
    if (!activeTest) return;

    setIsRunningTest(true);
    setTestResult(null);

    try {
      const resolved = apiBase || (await ensureApiBase());
      if (!resolved) {
        setTestResult("Error: API base could not be resolved.");
        return;
      }

      const url = buildUrl(resolved, activeTest.endpoint);

      const res = await fetch(url, {
        method: activeTest.method,
        headers: {
          "Content-Type": "application/json",
          ...(activeTest.headers || {}),
        },
        body:
          activeTest.method !== "GET" && activeTest.payload
            ? JSON.stringify(activeTest.payload)
            : undefined,
      });

      const ct = res.headers.get("content-type") || "";
      const data = ct.includes("application/json")
        ? await res.json()
        : await res.text();

      setTestResult(
        typeof data === "string" ? data : JSON.stringify(data, null, 2)
      );
    } catch (e: any) {
      setTestResult("Error: " + (e?.message || String(e)));
    } finally {
      setIsRunningTest(false);
    }
  };

  return (
    <div className="container mx-auto p-8 space-y-8 max-w-5xl text-slate-900 dark:text-slate-50">
      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            🎛️ Architect Control Panel
          </h1>
          <p className="text-slate-500 dark:text-slate-400">
            System Diagnostics & Test Bench
          </p>
          {apiBase && (
            <p className="mt-1 text-xs text-slate-400 font-mono break-all">
              API: {apiBase}
            </p>
          )}
        </div>

        <div className="flex items-center gap-4 bg-slate-100 dark:bg-slate-900 p-2 rounded-lg border">
          <div className="flex flex-col items-end mr-2">
            <span className="text-[10px] uppercase font-bold text-slate-400">
              System Status
            </span>
            <Badge
              variant={status === "ONLINE" ? "default" : "destructive"}
              className="px-3"
            >
              {status}
            </Badge>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={runDiagnosis}
            disabled={isDiagnosing}
            className="gap-2"
          >
            <RefreshCw
              className={`w-4 h-4 ${isDiagnosing ? "animate-spin" : ""}`}
            />
            {isDiagnosing ? "Checking..." : "Refresh Diagnosis"}
          </Button>
        </div>
      </div>

      {/* TIMESTAMP */}
      {lastUpdated && (
        <div className="text-right text-xs text-slate-400 font-mono">
          Last Check: {lastUpdated.toLocaleTimeString()}
        </div>
      )}

      {/* --- SECTION 1: DETAILED HEALTH --- */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <HealthCard
          title="Broker (Redis)"
          status={healthDetails?.broker}
          icon={<Activity className="w-5 h-5" />}
          desc="Async Job Queue"
        />
        <HealthCard
          title="Storage (Lexicon)"
          status={healthDetails?.storage}
          icon={<Database className="w-5 h-5" />}
          desc="JSON Data Shards"
        />
        <HealthCard
          title="Engine (GF)"
          status={healthDetails?.engine}
          icon={<Server className="w-5 h-5" />}
          desc="PGF Runtime & C-Bindings"
        />
      </div>

      {status === "OFFLINE" && (
        <Alert variant="destructive">
          <AlertTitle>System Unreachable</AlertTitle>
          <AlertDescription>
            The API is not responding. Ensure <b>Terminal 3 (Uvicorn)</b> is
            running.
          </AlertDescription>
        </Alert>
      )}

      {/* --- SECTION 2: COMMANDS --- */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <CommandCard
          title="Terminal 3: API Server"
          desc="Restarts the HTTP interface. Required after Python changes."
          cmd="uvicorn app.main:app --reload"
        />
        <CommandCard
          title="Terminal 2: Worker"
          desc="Restarts the Job Queue. Required after PGF compilation."
          cmd="source venv/bin/activate && arq app.workers.worker.WorkerSettings --watch app"
        />
      </div>

      {/* --- SECTION 3: SMOKE TEST --- */}
      <Card className="border-t-4 border-t-blue-500">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            🧪 Dynamic Test Bench
          </CardTitle>
          <CardDescription>
            Select a scenario to verify system behavior. Loaded{" "}
            {availableTests.length} definitions.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {availableTests.length === 0 ? (
            <Alert variant="destructive">
              <AlertTitle>No Tests Found</AlertTitle>
              <AlertDescription>
                Add .json files to the src/data/requests folder to enable testing
                scenarios.
              </AlertDescription>
            </Alert>
          ) : (
            <>
              <div className="flex flex-col md:flex-row gap-4">
                <div className="w-full md:w-1/2 space-y-2">
                  <label className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
                    Select Scenario
                  </label>
                  <Select value={selectedTestId} onValueChange={setSelectedTestId}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {availableTests.map((test) => (
                        <SelectItem key={test.id} value={test.id}>
                          {test.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-slate-500 dark:text-slate-400 italic mt-1 pl-1">
                    {activeTest?.description}
                  </p>
                </div>

                <div className="w-full md:w-1/2 space-y-2">
                  <label className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
                    Target Endpoint
                  </label>
                  <div className="p-2 bg-slate-100 dark:bg-slate-900 rounded border text-xs font-mono break-all text-slate-600 dark:text-slate-300 flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className="border-blue-500 text-blue-500 shrink-0"
                    >
                      {activeTest?.method}
                    </Badge>
                    <span>{activeTest?.endpoint}</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <h3 className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
                  Payload Preview
                </h3>
                <pre className="bg-slate-50 dark:bg-slate-950 p-3 rounded text-xs font-mono text-slate-700 dark:text-slate-300 overflow-auto max-h-40 border">
                  {activeTest?.payload
                    ? JSON.stringify(activeTest.payload, null, 2)
                    : "// No Payload"}
                </pre>
              </div>

              <Button
                onClick={runTest}
                disabled={status !== "ONLINE" || isRunningTest}
                className="w-full md:w-auto min-w-[150px]"
              >
                {isRunningTest ? "Running..." : "▶ Execute Request"}
              </Button>

              {testResult && (
                <div className="mt-4 p-4 bg-slate-950 rounded-lg overflow-x-auto border border-slate-800 shadow-inner">
                  <h3 className="text-xs font-bold text-slate-500 mb-2 uppercase tracking-wider">
                    API Response
                  </h3>
                  <pre className="text-xs font-mono text-green-400">{testResult}</pre>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// --- HELPER COMPONENTS ---

function HealthCard({
  title,
  status,
  icon,
  desc,
}: {
  title: string;
  status?: "up" | "down";
  icon: any;
  desc: string;
}) {
  const isUp = status === "up";
  return (
    <Card className={`border-l-4 ${isUp ? "border-l-green-500" : "border-l-gray-300"}`}>
      <div className="p-4 flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            {title}
          </p>
          <div className="flex items-center gap-2">
            {isUp ? (
              <CheckCircle2 className="w-4 h-4 text-green-500" />
            ) : (
              <XCircle className="w-4 h-4 text-slate-400" />
            )}
            <span className={`font-bold ${isUp ? "text-green-600" : "text-slate-400"}`}>
              {status ? status.toUpperCase() : "UNKNOWN"}
            </span>
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-300">{desc}</p>
        </div>
        <div className={`p-2 rounded-full ${isUp ? "bg-green-100 text-green-600" : "bg-slate-100 text-slate-400"}`}>
          {icon}
        </div>
      </div>
    </Card>
  );
}

function CommandCard({ title, desc, cmd }: { title: string; desc: string; cmd: string }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">{title}</CardTitle>
        <CardDescription>{desc}</CardDescription>
      </CardHeader>
      <CardContent>
        <div
          className="bg-slate-100 dark:bg-slate-900 p-3 rounded-md font-mono text-xs cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors break-all border group relative"
          onClick={() => navigator.clipboard.writeText(cmd)}
          title="Click to Copy"
        >
          <span className="mr-2 text-slate-400">$</span>
          {cmd}
          <span className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 text-[10px] bg-black text-white px-1 rounded">
            COPY
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
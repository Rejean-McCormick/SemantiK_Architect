"use client";

import { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SMOKE_TESTS } from "@/lib/test-payloads";
import { Activity, Database, Server, RefreshCw, CheckCircle2, XCircle } from "lucide-react"; 

// Interface matching your API response from docs/04-API_REFERENCE.md
interface SystemHealth {
  broker: "up" | "down";
  storage: "up" | "down";
  engine: "up" | "down";
}

export default function DevDashboard() {
  const [status, setStatus] = useState<"CONNECTING" | "ONLINE" | "OFFLINE">("CONNECTING");
  const [healthDetails, setHealthDetails] = useState<SystemHealth | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isDiagnosing, setIsDiagnosing] = useState(false);

  // Test Runner State
  const [selectedTestId, setSelectedTestId] = useState<string>(SMOKE_TESTS[0].id);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [isRunningTest, setIsRunningTest] = useState(false);

  const activeTest = SMOKE_TESTS.find(t => t.id === selectedTestId) || SMOKE_TESTS[0];

  // --- 1. DIAGNOSIS SYSTEM ---
  const runDiagnosis = async () => {
    setIsDiagnosing(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/health/ready");
      if (res.ok) {
        const data: SystemHealth = await res.json();
        setHealthDetails(data);
        setStatus("ONLINE");
      } else {
        setStatus("OFFLINE");
        setHealthDetails(null);
      }
    } catch (e) {
      setStatus("OFFLINE");
      setHealthDetails(null);
    } finally {
      setLastUpdated(new Date());
      setIsDiagnosing(false);
    }
  };

  // Auto-run once on mount
  useEffect(() => {
    runDiagnosis();
  }, []);

  // --- 2. TEST RUNNER ---
  const runTest = async () => {
    setIsRunningTest(true);
    setTestResult(null);
    try {
      const res = await fetch(activeTest.endpoint, {
        method: "POST",
        headers: activeTest.headers,
        body: JSON.stringify(activeTest.payload)
      });
      const data = await res.json();
      setTestResult(JSON.stringify(data, null, 2));
    } catch (e: any) {
      setTestResult("Error: " + e.message);
    } finally {
      setIsRunningTest(false);
    }
  };

  return (
    <div className="container mx-auto p-8 space-y-8 max-w-5xl text-slate-900 dark:text-slate-50">
      
      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">🎛️ Architect Control Panel</h1>
          <p className="text-slate-500 dark:text-slate-400">System Diagnostics & Test Bench</p>
        </div>
        
        <div className="flex items-center gap-4 bg-slate-100 dark:bg-slate-900 p-2 rounded-lg border">
          <div className="flex flex-col items-end mr-2">
            <span className="text-[10px] uppercase font-bold text-slate-400">System Status</span>
            <Badge variant={status === "ONLINE" ? "default" : "destructive"} className="px-3">
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
            <RefreshCw className={`w-4 h-4 ${isDiagnosing ? "animate-spin" : ""}`} />
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
            The API is not responding. Ensure <b>Terminal 3 (Uvicorn)</b> is running.
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
            🧪 Smoke Test Bench
          </CardTitle>
          <CardDescription>Select a scenario to verify system behavior.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          
          <div className="flex flex-col md:flex-row gap-4">
            <div className="w-full md:w-1/2 space-y-2">
                <label className="text-xs font-semibold uppercase text-slate-500">Select Scenario</label>
                <Select value={selectedTestId} onValueChange={setSelectedTestId}>
                  <SelectTrigger>
                      <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                      {SMOKE_TESTS.map((test) => (
                      <SelectItem key={test.id} value={test.id}>
                          {test.label}
                      </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-slate-500 italic mt-1 pl-1">
                  {activeTest.description}
                </p>
            </div>
            
            <div className="w-full md:w-1/2 space-y-2">
               <label className="text-xs font-semibold uppercase text-slate-500">Target Endpoint</label>
               <div className="p-2 bg-slate-100 dark:bg-slate-900 rounded border text-xs font-mono break-all text-slate-600 dark:text-slate-300">
                 POST {activeTest.endpoint}
               </div>
            </div>
          </div>

          <div className="space-y-2">
            <h3 className="text-xs font-semibold uppercase text-slate-500">Payload Preview</h3>
            <pre className="bg-slate-50 dark:bg-slate-950 p-3 rounded text-xs font-mono text-slate-700 dark:text-slate-300 overflow-auto max-h-40 border">
                {JSON.stringify(activeTest.payload, null, 2)}
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
              <h3 className="text-xs font-bold text-slate-500 mb-2 uppercase tracking-wider">API Response</h3>
              <pre className="text-xs font-mono text-green-400">
                {testResult}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// --- HELPER COMPONENTS ---

function HealthCard({ title, status, icon, desc }: { title: string, status?: "up" | "down", icon: any, desc: string }) {
  const isUp = status === "up";
  return (
    <Card className={`border-l-4 ${isUp ? "border-l-green-500" : "border-l-gray-300"}`}>
      <div className="p-4 flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-sm font-medium text-slate-500 uppercase tracking-wider">{title}</p>
          <div className="flex items-center gap-2">
            {isUp ? <CheckCircle2 className="w-4 h-4 text-green-500" /> : <XCircle className="w-4 h-4 text-slate-400" />}
            <span className={`font-bold ${isUp ? "text-green-600" : "text-slate-400"}`}>
              {status ? status.toUpperCase() : "UNKNOWN"}
            </span>
          </div>
          <p className="text-xs text-slate-400">{desc}</p>
        </div>
        <div className={`p-2 rounded-full ${isUp ? "bg-green-100 text-green-600" : "bg-slate-100 text-slate-400"}`}>
          {icon}
        </div>
      </div>
    </Card>
  )
}

function CommandCard({ title, desc, cmd }: { title: string, desc: string, cmd: string }) {
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
          <span className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 text-[10px] bg-black text-white px-1 rounded">COPY</span>
        </div>
      </CardContent>
    </Card>
  );
}
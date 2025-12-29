// architect_frontend/src/app/tools/page.tsx
"use client";

import React, { useState } from "react";
import { 
  Terminal, 
  Database, 
  Cpu, 
  ShieldCheck, 
  Wrench, 
  Play, 
  Loader2, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle,
  FlaskConical,
  Bot
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

// --- CONFIGURATION ---
const TOOL_CATEGORIES = [
  {
    id: "maintenance",
    title: "Diagnostics & Health",
    description: "System integrity checks and cleanup operations.",
    icon: <Wrench className="w-5 h-5 text-blue-500" />,
    tools: [
      { id: "audit_languages", name: "Audit Languages", risk: "safe", desc: "Rapidly scans RGL folders to report Valid/Broken/Skipped." },
      { id: "check_all_languages", name: "Deep Verification", risk: "moderate", desc: "Sends test payloads to the API for every language." },
      { id: "diagnostic_audit", name: "Forensics Audit", risk: "safe", desc: "Identifies 'Zombie' files or old builds causing issues." },
      { id: "cleanup_root", name: "Cleanup Root", risk: "safe", desc: "Moves loose .gf files to gf/ and deletes .gfo artifacts." },
    ]
  },
  {
    id: "build",
    title: "Build & Compile",
    description: "Core compiler and registry operations.",
    icon: <Cpu className="w-5 h-5 text-purple-500" />,
    tools: [
      { id: "build_index", name: "Rebuild Matrix", risk: "safe", desc: "Rescans filesystem to update everything_matrix.json." },
      { id: "compile_pgf", name: "Compile Grammar", risk: "heavy", desc: "Runs the Full Build (Phase 1 & 2) to create AbstractWiki.pgf." },
      { id: "bootstrap_tier1", name: "Bootstrap Tier 1", risk: "moderate", desc: "Generates Wiki*.gf wrappers for RGL languages." },
    ]
  },
  {
    id: "data",
    title: "Data Refinery",
    description: "Lexicon mining and schema management.",
    icon: <Database className="w-5 h-5 text-amber-500" />,
    tools: [
      { id: "harvest_lexicon", name: "Harvest Lexicon", risk: "safe", desc: "Mines local WordNet/RGL files for vocabulary." },
      { id: "build_lexicon_wikidata", name: "Mine Wikidata", risk: "moderate", desc: "Fetches QIDs for People/Science domains from Wikidata." },
      { id: "refresh_index", name: "Refresh Index", risk: "safe", desc: "Rebuilds the fast lookup index for the API." },
      { id: "migrate_schema", name: "Migrate Schema", risk: "moderate", desc: "Upgrades lexicon JSON files to the latest v2.1 schema." },
      { id: "dump_stats", name: "Dump Statistics", risk: "safe", desc: "Outputs raw lexicon coverage stats." },
    ]
  },
  {
    id: "qa",
    title: "QA & Testing",
    description: "Automated test suites and validators.",
    icon: <ShieldCheck className="w-5 h-5 text-green-500" />,
    tools: [
      { id: "run_smoke_tests", name: "Lexicon Smoke Tests", risk: "safe", desc: "Validates syntax and structure of all lexicon files." },
      { id: "eval_bios", name: "Evaluate Biographies", risk: "safe", desc: "Compares generated bios against Wikidata facts." },
      { id: "lexicon_coverage", name: "Coverage Report", risk: "safe", desc: "Generates a report on missing vs implemented words." },
      { id: "test_runner", name: "Run CSV Suite", risk: "moderate", desc: "Executes the standard CSV-based linguistic test suite." },
    ]
  },
  {
    id: "ai",
    title: "AI Services",
    description: "Autonomous agents.",
    icon: <Bot className="w-5 h-5 text-pink-500" />,
    tools: [
      { id: "seed_lexicon", name: "Seed Lexicon AI", risk: "heavy", desc: "Uses LLM to generate core vocabulary for new languages." },
      { id: "ai_refiner", name: "AI Refiner", risk: "heavy", desc: "Attempts to upgrade Pidgin grammars to full RGL." },
    ]
  }
];

export default function ToolsDashboard() {
  const [activeToolId, setActiveToolId] = useState<string | null>(null);
  const [consoleOutput, setConsoleOutput] = useState<string>("// System Ready. Select a tool to begin.");
  const [lastStatus, setLastStatus] = useState<"success" | "error" | null>(null);

  const runTool = async (toolId: string) => {
    setActiveToolId(toolId);
    setLastStatus(null);
    setConsoleOutput((prev) => prev + `\n\n> Executing tool: ${toolId}...\n----------------------------------------`);

    try {
      const res = await fetch("http://localhost:8000/api/v1/tools/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool_id: toolId })
      });

      const data = await res.json();

      if (data.success) {
        setLastStatus("success");
        setConsoleOutput((prev) => prev + `\n${data.output}\n\n[SUCCESS] Process exited with code 0.`);
      } else {
        setLastStatus("error");
        setConsoleOutput((prev) => prev + `\n${data.output}\n${data.error}\n\n[ERROR] Process failed.`);
      }
    } catch (e: any) {
      setLastStatus("error");
      setConsoleOutput((prev) => prev + `\n[NETWORK ERROR]: ${e.message}`);
    } finally {
      setActiveToolId(null);
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-7xl space-y-6">
      
      {/* HEADER */}
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-3">
          <Terminal className="w-8 h-8 text-slate-700 dark:text-slate-300" />
          Tools Command Center
        </h1>
        <p className="text-slate-500 dark:text-slate-400">
          Execute backend maintenance scripts and build tasks directly from the interface.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-200px)]">
        
        {/* LEFT COLUMN: Tool Menu */}
        <div className="lg:col-span-1 space-y-6 overflow-y-auto pr-2 pb-10">
          {TOOL_CATEGORIES.map((cat) => (
            <div key={cat.id} className="space-y-3">
              <div className="flex items-center gap-2 mb-2">
                {cat.icon}
                <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500">
                  {cat.title}
                </h2>
              </div>
              
              <div className="grid gap-3">
                {cat.tools.map((tool) => (
                  <button
                    key={tool.id}
                    onClick={() => runTool(tool.id)}
                    disabled={activeToolId !== null}
                    className="group relative flex flex-col items-start p-3 rounded-lg border border-slate-200 bg-white hover:border-blue-400 hover:shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed text-left"
                  >
                    <div className="flex w-full justify-between items-center mb-1">
                      <span className="font-semibold text-slate-800 text-sm group-hover:text-blue-700">
                        {tool.name}
                      </span>
                      {activeToolId === tool.id ? (
                        <Loader2 className="w-3 h-3 animate-spin text-blue-600" />
                      ) : (
                        <Play className="w-3 h-3 text-slate-300 group-hover:text-blue-500" />
                      )}
                    </div>
                    <p className="text-xs text-slate-500 leading-snug">
                      {tool.desc}
                    </p>
                    
                    {/* Risk Badge */}
                    <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                       {tool.risk === "heavy" && <Badge variant="destructive" className="text-[9px] px-1 py-0 h-4">Heavy</Badge>}
                       {tool.risk === "moderate" && <Badge variant="outline" className="text-[9px] px-1 py-0 h-4 border-amber-500 text-amber-600 bg-amber-50">Wait</Badge>}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* RIGHT COLUMN: Terminal Output */}
        <div className="lg:col-span-2 flex flex-col h-full">
          <Card className="flex-1 flex flex-col bg-slate-950 border-slate-800 shadow-2xl overflow-hidden">
            <CardHeader className="py-3 px-4 border-b border-slate-800 bg-slate-900/50 flex flex-row items-center justify-between">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-slate-400" />
                <CardTitle className="text-xs font-mono uppercase tracking-widest text-slate-400">
                  Console Output
                </CardTitle>
              </div>
              <div className="flex items-center gap-3">
                {lastStatus === "success" && <span className="flex items-center gap-1 text-xs text-green-500"><CheckCircle2 className="w-3 h-3"/> Success</span>}
                {lastStatus === "error" && <span className="flex items-center gap-1 text-xs text-red-500"><XCircle className="w-3 h-3"/> Failed</span>}
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-6 text-[10px] text-slate-500 hover:text-slate-300"
                  onClick={() => setConsoleOutput("// Console cleared.")}
                >
                  Clear
                </Button>
              </div>
            </CardHeader>
            <CardContent className="flex-1 p-0 relative group">
              <textarea 
                readOnly 
                value={consoleOutput}
                className="w-full h-full bg-slate-950 text-slate-300 font-mono text-xs p-4 resize-none focus:outline-none scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent"
              />
            </CardContent>
          </Card>
        </div>

      </div>
    </div>
  );
}
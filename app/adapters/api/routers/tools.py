# app/adapters/api/routers/tools.py
import subprocess
import os
import sys
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# --- 1. Configuration ---
# Use the currently running Python interpreter (venv) to avoid system/path issues
PYTHON_EXE = sys.executable 

# --- 2. The Allowlist (Security Layer) ---
# Maps Frontend IDs -> Physical Script Paths
# This matches the IDs defined in architect_frontend/src/app/tools/page.tsx
TOOL_REGISTRY = {
    # --- MAINTENANCE ---
    "audit_languages": [PYTHON_EXE, "tools/audit_languages.py"],
    "check_all_languages": [PYTHON_EXE, "tools/check_all_languages.py"],
    "diagnostic_audit": [PYTHON_EXE, "tools/diagnostic_audit.py"],
    "cleanup_root": [PYTHON_EXE, "tools/cleanup_root.py"],
    
    # --- BUILD ---
    "build_index": [PYTHON_EXE, "tools/everything_matrix/build_index.py"],
    # Pointing to the actual orchestrator now
    "compile_pgf": [PYTHON_EXE, "gf/build_orchestrator.py"], 
    "bootstrap_tier1": [PYTHON_EXE, "tools/bootstrap_tier1.py"],
    
    # --- DATA REFINERY ---
    "harvest_lexicon": [PYTHON_EXE, "tools/harvest_lexicon.py"], # Arguments handled dynamically below
    "build_lexicon_wikidata": [PYTHON_EXE, "tools/build_lexicon_from_wikidata.py"],
    "refresh_index": [PYTHON_EXE, "utils/refresh_lexicon_index.py"],
    "migrate_schema": [PYTHON_EXE, "utils/migrate_lexicon_schema.py"],
    "dump_stats": [PYTHON_EXE, "utils/dump_lexicon_stats.py"],
    
    # --- QA & TESTING ---
    # We run pytest as a module to capture output correctly
    "run_smoke_tests": [PYTHON_EXE, "-m", "pytest", "tests/test_lexicon_smoke.py"],
    "eval_bios": [PYTHON_EXE, "tools/qa/eval_bios.py"],
    "lexicon_coverage": [PYTHON_EXE, "tools/qa/lexicon_coverage_report.py"],
    "test_runner": [PYTHON_EXE, "tools/qa/test_runner.py"],
    
    # --- AI SERVICES ---
    "seed_lexicon": [PYTHON_EXE, "utils/seed_lexicon_ai.py"],
    "ai_refiner": [PYTHON_EXE, "tools/ai_refiner.py"],
}

# --- 3. Request Schema ---
class ToolRunRequest(BaseModel):
    tool_id: str
    args: Optional[List[str]] = []

class ToolRunResponse(BaseModel):
    success: bool
    command: str
    output: str
    error: str

# --- 4. The Endpoint ---
@router.post("/run", response_model=ToolRunResponse)
async def run_tool(payload: ToolRunRequest):
    """
    Executes a predefined maintenance script from the backend root.
    """
    cmd_template = TOOL_REGISTRY.get(payload.tool_id)
    
    if not cmd_template:
        raise HTTPException(status_code=404, detail=f"Tool '{payload.tool_id}' not found in registry.")

    # Construct command (Script + Args)
    # Security Note: In a production environment, you should strictly validate `payload.args` 
    # to prevent flag injection (e.g. preventing users from passing --dangerous-flags).
    command = cmd_template + (payload.args or [])
    
    try:
        # Run process from project root
        # We assume the API runs from 'abstract-wiki-architect/' root
        process = subprocess.run(
            command,
            cwd=os.getcwd(), 
            capture_output=True,
            text=True,
            timeout=300 # 5 minute timeout for long tasks like harvesting
        )
        
        return ToolRunResponse(
            success=process.returncode == 0,
            command=" ".join(command),
            output=process.stdout,
            error=process.stderr
        )
        
    except subprocess.TimeoutExpired:
        return ToolRunResponse(
            success=False,
            command=" ".join(command),
            output="",
            error="Process timed out (Limit: 300s)."
        )
    except Exception as e:
        return ToolRunResponse(
            success=False,
            command=" ".join(command),
            output="",
            error=str(e)
        )
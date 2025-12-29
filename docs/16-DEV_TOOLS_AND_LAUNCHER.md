

# 🛠️ Developer Tools & Unified Launch System

**Abstract Wiki Architect v2.1**

## 1. The "God Mode" Launcher (`Run-Architect.ps1`)

The **Unified Orchestrator** is a PowerShell script that manages the complex hybrid environment (Windows Frontend + Linux Backend) automatically.

**Location:** `Run-Architect.ps1` (Root)

### Why it exists

1. **Zombie killing:** It forcefully kills lingering `uvicorn` (Linux) or `node` (Windows) processes holding ports 8000 or 3000 to prevent address errors.
2. **Window Management:** It spawns **3 separate visible windows** for simultaneous monitoring of API, Worker, and Frontend logs.
3. **Consistency:** It delegates startup arguments to `manage.py`, ensuring the environment matches the Single Source of Truth.

### Usage

Right-click the file and select **"Run with PowerShell"**, or run from the terminal:

```powershell
.\Run-Architect.ps1

```

### Process Flow

* **Host (PowerShell):** Performs cleanup, verifies Docker/Redis, and spawns child windows.
* **Terminal 1 (WSL):** API Backend via `python3 manage.py start-api`.
* **Terminal 2 (WSL):** Background Worker via `python3 manage.py start-worker`.
* **Terminal 3 (Windows Native):** Frontend via `npm run dev`.

---

## 2. The Developer Console (`/dev`)

A dedicated dashboard for immediate system health verification and "Smoke Testing."

**URL:** `http://localhost:3000/dev`

### Features

* **System Heartbeat:** Real-time component status from the `/health/ready` endpoint:
* **Broker:** Redis connection status.
* **Storage:** Lexicon file accessibility.
* **Engine:** PGF Binary loading status.


* **One-Click Smoke Test:** Instantly sends a standard "Marie Curie" BioFrame to the engine to verify rendering without manual `curl` commands.
* **Command Cheat Sheet:** Quick-reference for manual service restart commands.

---

## 3. The System Tools Dashboard (`/tools`)

A GUI wrapper for backend maintenance scripts, allowing tasks to be performed without a WSL terminal.

**URL:** `http://localhost:3000/tools`

### How it works

1. **Request:** The Frontend sends a JSON tool ID (e.g., `audit_languages`) to `POST /api/v1/tools/run`.
2. **Validation:** The Backend checks the ID against a strict **Allowlist Registry** for security.
3. **Execution:** The system spawns a subprocess to run the script in the Linux environment.
4. **Streaming:** Standard output (`stdout`) is streamed directly back to the browser console window.

### Available DashBoard Tool Mappings

| Tool ID | Action Taken |
| --- | --- |
| `audit_languages` | Scans the Matrix for broken languages. |
| `compile_pgf` | Triggers the Build Orchestrator to recompile the grammar binary. |
| `harvest_lexicon` | Fetches new words from Wikidata/WordNet. |
| `run_judge` | Executes the Golden Standard regression tests via the AI Judge. |

---

## 4. Backend Orchestration Details

To support these developer interfaces, the following infrastructure is utilized:

* **Secure Router:** `app/adapters/api/routers/tools.py` handles execution logic and security gating.
* **Tool Registry:** The `TOOL_REGISTRY` dictionary maps safe IDs to specific physical file paths to prevent arbitrary code execution.
* **Unified Commander:** `manage.py` provides standardized sub-commands so external launchers do not need to manage environment-specific flags.
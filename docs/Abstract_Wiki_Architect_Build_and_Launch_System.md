
# 🏛️ Abstract Wiki Architect: Build & Launch System

## 1. High-Level Architecture

The system follows a **"check, build, serve"** pipeline. It does not simply start the API; it first performs a deep census of your data (The Matrix), compiles the grammar binary (The PGF), and only then launches the runtime services.

---

## 2. Level 1: The Commander 🚀

**Script:** `launch.ps1`
**Role:** The Orchestrator
**Location:** Root

This is the entry point. It contains no application logic; its job is **environment management** and **sequencing**.

* **Pre-Flight:** Kills stale processes (`uvicorn`, `arq`) and verifies Docker/Redis.
* **Step 1:** Calls **Level 2 (Indexer)** to update the knowledge base.
* **Step 2:** Calls **Level 2 (Builder)** to compile the binary.
* **Step 3:** Spawns **Level 4 (Services)** in visible windows.

---

## 3. Level 2: The Builders 🏗️

These scripts run sequentially. If one fails, the launch aborts (unless "Resilience Mode" is active).

### A. The Census Taker (Indexer)

* **Script:** `tools/everything_matrix/build_index.py`
* **Input:** Raw Lexicon Data (`data/lexicon/`) and RGL Source (`gf-rgl/src/`).
* **Output:** `data/indices/everything_matrix.json`
* **Logic:**
* It scans the file system to find every supported language.
* It imports **Level 3 Specialists** (`rgl_auditor`, `lexicon_scanner`) to grade the quality of each language.
* It saves a JSON "Matrix" that acts as the source of truth for the Compiler.



### B. The Compiler (Orchestrator)

* **Script:** `gf/build_orchestrator.py`
* **Input:** `everything_matrix.json`
* **Output:** `gf/AbstractWiki.pgf` (The binary).
* **Logic:**
* **Zombie Cleanup:** Deletes broken/stale generated files.
* **Generation:** Creates `AbstractWiki.gf` and `WikiI.gf` dynamically.
* **Resolution:** Finds the best source for each language (Is it in RGL? Is it generated? Is it in Contrib?).
* **AI Intervention:** If a language is missing, it calls **Level 3 (The Architect)** to generate it.
* **Compilation:** Calls the external `gf` binary to link everything into a `.pgf`.



---

## 4. Level 3: The Specialists (Hidden Dependencies) 🧠

These scripts are not run directly by you. They are libraries imported by Level 2 to perform complex analysis or AI generation.

### A. The RGL Auditor

* **Script:** `tools/everything_matrix/rgl_auditor.py`
* **Caller:** `build_index.py`
* **Function:** `audit_language(iso, path)`
* **Logic:**
* Checks for the existence of the "Big 5" GF modules: `Cat`, `Noun`, `Grammar`, `Paradigms`, `Syntax`.
* Calculates a **Maturity Score (0-10)**.
* If key files are missing, it flags the language as "SAFE_MODE" so the build doesn't crash.



### B. The Lexicon Scanner

* **Script:** `tools/everything_matrix/lexicon_scanner.py`
* **Caller:** `build_index.py`
* **Function:** `audit_lexicon(iso, path)`
* **Logic:**
* Audits semantic domains (`core`, `people`, `science`).
* Counts total word depth.
* Determines if the language has enough data to be "Production Ready" (Score > 8).



### C. The AI Agent (Architect & Surgeon)

* **Script:** `ai_services/architect.py`
* **Caller:** `build_orchestrator.py`
* **Logic:**
* **The Architect:** If `resolve_language_path` fails, this sends a prompt to Google Gemini: *"Write the concrete grammar for Zulu."*
* **The Surgeon:** If compilation fails, it takes the error log and the broken code, sends it to Gemini, and asks for a patched version.
* **Sanitization:** Strips Markdown (````gf`) from the LLM output to ensure clean compilation.



---

## 5. Level 4: The Runtime Services 🔌

Once Level 2 finishes successfully, Level 1 spawns these persistent processes.

### A. The API (Brain)

* **Script:** `app/adapters/api/main.py`
* **Framework:** FastAPI + Uvicorn
* **Role:** Handles HTTP requests, manages the Dependency Injection Container, and serves the Swagger UI.

### B. The Worker (Muscle)

* **Script:** `app/workers/worker.py`
* **Framework:** ARQ (Redis)
* **Role:**
* Loads the `AbstractWiki.pgf` binary into memory.
* Watches the file system; if `build_orchestrator.py` updates the binary, the Worker **hot-reloads** it without restarting.



---

## Data Flow Summary

1. **Lexicon/RGL** (Files) ➔ **Scanners** (Level 3) ➔ **Indexer** (Level 2) ➔ **Matrix JSON**.
2. **Matrix JSON** ➔ **Orchestrator** (Level 2) ➔ **Architect** (Level 3, optional) ➔ **GF Compiler** ➔ **PGF Binary**.
3. **PGF Binary** ➔ **Worker** (Level 4, Memory) ➔ **API** (Level 4, User).
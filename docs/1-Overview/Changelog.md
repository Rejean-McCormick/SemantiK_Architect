Updated to reflect the current repo direction, the public API shape, the planner-first target, the still-observed legacy compatibility path, and the need for explicit EN/FR validation.

## 22. Changelog

### Unreleased (SemantiK Architect)

* Project renamed from **“Abstract Wiki Architect” → “SemantiK Architect”** (independent project; no WMF/Abstract Wiki affiliation).
* Documentation realigned around the current platform identity, production contracts, and architecture terminology.
* Clarified the distinction between the **target runtime** (planner-first, construction-centered) and the **current live compatibility path** still observed in generation.
* Public generation docs updated to reflect the current response contract (`text`, `lang_code`, `construction_id`, `renderer_backend`, `fallback_used`, `tokens`, `debug_info`) rather than older `surface_text/meta` examples.
* Added explicit status tracking for **EN/FR bio generation**, separating target-state examples from validated runtime behavior.
* Tightened the definition of language “done” to require real runtime validation, not only successful compilation or any non-empty generation output.

### v2.5 (Docs baseline: setup/deploy + operator workflow)

* Documented the **Windows + WSL2 hybrid** dev model (Windows for editing/frontend, Linux/WSL for backend + GF), driven by the GF `libpgf` Linux dependency.
* Standardized prerequisites (WSL2, Ubuntu, Docker Desktop, VS Code WSL extension, Node 18+).
* Clarified **deployment via docker-compose**, including base-path conventions for UI and versioned API prefix.
* Formalized config/ops knobs in `.env`, including explicit **AI tool gating**.
* Established the operator-facing setup and deployment baseline for local development and service bring-up.

### v2.1 (Architecture and build system clarified/expanded)

* Consolidated the system model as a **4-layer architecture**: Lexicon, Grammar, Renderer, Context.
* Defined the **dual-path input** story (Strict Frames vs Prototype Ninai/UniversalNode) for the earlier architecture phase.
* Codified the **3-tier language strategy** (Tier 1 “High Road”, Tier 2 overrides, Tier 3 weighted-topology factory) for long-tail coverage.
* Made the build “self-aware” via the **Everything Matrix** (filesystem scanning → maturity scoring → build strategy).
* Expanded architectural docs for language coverage, renderer boundaries, and build orchestration.

### v2.0 (Omni-upgrade milestone: expansion beyond sentence-level generation)

* Stated the core shift: from a **sentence-level rule-based engine** to a **context-aware, interoperable, AI-augmented platform**.
* Introduced the “7 pillars” roadmap: Ninai bridge, UD exporter, discourse planner, automation agent, interactive QA, weighted topology factory, learned micro-planning.
* Introduced a unified **“Check, Build, Serve”** pipeline and a single operational entry point for developers (`manage.py`).
* Established the **Everything Matrix** as a dynamic registry replacing static language lists/config.
* Marked the beginning of the transition toward a construction-aware runtime and richer end-to-end generation contracts.

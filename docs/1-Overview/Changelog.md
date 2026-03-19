## 22. Changelog

### Unreleased (SemantiK Architect)

* Documentation fully realigned around **SemantiK Architect** as an independent project and around the final multilingual runtime direction.
* Established the **planner-first multilingual runtime** as the single target architecture, with the canonical runtime boundary explicitly defined as:

  `ConstructionPlan -> SurfaceResult`

* Clarified the authoritative runtime flow across docs as:

  `HTTP payload -> frame normalization -> frame-to-construction bridge -> planner -> PlannedSentence -> construction-plan builder -> ConstructionPlan -> lexical resolution -> renderer dispatch -> renderer backend -> SurfaceResult -> public response mapping`

* Locked the rule that **public response mapping happens only after `SurfaceResult`** and that the API mapper must serialize canonical runtime truth rather than invent it.
* Standardized the distinction between:
  * **internal runtime objects** (`PlannedSentence`, `ConstructionPlan`, `SurfaceResult`),
  * **public HTTP response objects**, and
  * **frontend/client convenience objects**.
* Public generation docs updated to reflect the canonical success envelope:

  * `text`
  * `lang_code`
  * `construction_id`
  * `renderer_backend`
  * `fallback_used`
  * `tokens`
  * `debug_info`
  * `generation_time_ms`

  rather than older `surface_text/meta` examples.

* Clarified that on the nominal planner-first path:
  * `construction_id` must be explicit,
  * `renderer_backend` must be explicit,
  * `fallback_used` must be explicit,
  * `generation_time_ms` is top-level and authoritative,
  * and `debug_info` must not contradict top-level fields.

* Tightened the architectural rule that the **shared core must remain language-neutral**:
  * shared GF layers must not encode English or French surface strings,
  * runtime bridges must not fake language-correct output in shared layers,
  * and concrete language modules must own final surface realization.

* Explicitly defined EN/FR as the **first full vertical slice** of the multilingual runtime rather than the final scope of the system.
* Added and synchronized the normative documentation stack for the final cutover:
  * multilingual runtime target,
  * EN/FR final parallel lockdown,
  * EN/FR cutover plan,
  * EN/FR acceptance,
  * multilingual readiness,
  * construction runtime contract,
  * public generation response contract,
  * planner/realizer interfaces,
  * runtime/public/frontend boundaries,
  * and construction runtime test plan.

* Clarified that **legacy direct generation is not part of the final architecture**.
* Clarified that any remaining compatibility behavior is compatibility-only, explicitly marked, and must not count as nominal planner-first success.
* Tightened the definition of language “done” to require:
  * correct routing,
  * correct runtime path,
  * correct surface language,
  * valid public contract,
  * structured metadata,
  * and acceptance/evaluator success.

* Added the multilingual **language capability model** and readiness tiers, separating:
  * declared,
  * compile-capable,
  * runtime-loadable,
  * routable,
  * generates,
  * construction-correct,
  * acceptance-ready,
  * and release-ready.

* Added explicit EN/FR validation guidance so that:
  * EN must resolve to `WikiEng` and surface English,
  * FR must resolve to `WikiFre` and surface French,
  * and **FR routed-correctly but surfaced-in-English is a hard failure**.

* Expanded the test strategy around the aligned runtime to require verification of:
  * planner authority,
  * contract stability,
  * renderer substitutability,
  * lexical resolution correctness,
  * fallback transparency,
  * public-contract preservation,
  * runtime/public/frontend boundary correctness,
  * and regression protection against multiple centers of truth.

* Clarified that architecture, contracts, migration docs, testing docs, and status docs must not contradict one another, and that status documentation cannot overrule architecture or acceptance truth.

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
* Made the build “self-aware” via the **Everything Matrix** (filesystem scanning -> maturity scoring -> build strategy).
* Expanded architectural docs for language coverage, renderer boundaries, and build orchestration.

### v2.0 (Omni-upgrade milestone: expansion beyond sentence-level generation)

* Stated the core shift: from a **sentence-level rule-based engine** to a **context-aware, interoperable, AI-augmented platform**.
* Introduced the “7 pillars” roadmap: Ninai bridge, UD exporter, discourse planner, automation agent, interactive QA, weighted topology factory, learned micro-planning.
* Introduced a unified **“Check, Build, Serve”** pipeline and a single operational entry point for developers (`manage.py`).
* Established the **Everything Matrix** as a dynamic registry replacing static language lists/config.
* Marked the beginning of the transition toward a construction-aware runtime and richer end-to-end generation contracts.
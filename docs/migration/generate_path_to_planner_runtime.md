# Migration: `/generate` Path to Planner-First Runtime

Status: normative migration and runtime-alignment document
Owner: Runtime / Grammar / API / QA
Scope: migration of the public `/generate` path to the planner-first multilingual runtime
Immediate implementation scope: EN + FR bio/person generation
Architectural scope: generic planner-first runtime designed to scale across construction families and languages
Last updated: 2026-03-19

---

## 1. Purpose

This document defines the migration of the live `/generate` path from a hybrid direct-generation model to the planner-first runtime model.

It exists to ensure that the public generation path converges on one runtime truth instead of continuing to split sentence generation across:

* API-facing normalization,
* direct frame-to-engine generation,
* planner/construction abstractions,
* lexical behavior hidden in backends,
* and backend-local realization behavior.

This is a migration and runtime-alignment document.
It does not replace the target architecture document, the EN/FR cutover plan, the EN/FR acceptance gate, or the public response contract.
It defines how the live `/generate` path must be brought into alignment with them.

This document is intentionally deeper than a short cutover note.
Its job is to preserve operational clarity during implementation while keeping one architectural truth across runtime, contracts, tests, and documentation.

---

## 2. Document role and precedence

This document is normative for migration and runtime alignment, but it is not the highest-precedence source for every question.

If the issue is:

* target architecture, `multilingual_runtime_target.md` wins,
* EN/FR cutover sequencing, `en_fr_cutover_plan.md` wins,
* EN/FR bio/person acceptance, `EN_FR_bio_acceptance.md` wins,
* public success envelope semantics, `public_generation_response_contract.md` wins,
* planner/runtime/API/document precedence, `EN_FR_FINAL_PARALLEL_LOCKDOWN.md` wins.

This document must remain consistent with all of those sources.

This document therefore has a specific role:

* it defines the runtime migration path,
* it fixes the migration vocabulary,
* it stabilizes object and boundary ownership during implementation,
* and it prevents the `/generate` path from continuing to drift away from the documented planner-first architecture.

---

## 3. Migration statement

The live `/generate` path must become a planner-first runtime path.

The target nominal path is:

`API payload -> frame normalization -> frame-to-plan bridge -> planner -> PlannedSentence -> ConstructionPlan -> lexical resolution -> realizer dispatch -> SurfaceResult -> API response mapping`

For the immediate implementation scope, this migration must make EN and FR bio/person generation planner-first on the nominal path.

For the broader architectural scope, the migration must establish one generic runtime model that can later support additional construction families and many more languages without changing the core boundary contracts.

Legacy direct frame-to-engine generation may remain only as explicit compatibility fallback during migration.
It must not remain a competing authoritative runtime.

---

## 4. Why this migration is necessary

The repository already defines a planner/construction-oriented architecture and already contains planning, construction, renderer, and multilingual abstractions.

However, the live `/generate` path has historically allowed normalized frames to flow too directly into backend generation behavior.

That creates runtime drift between:

1. the documented architecture,
2. the planner/construction runtime model,
3. the live generation path,
4. the public contract expectations,
5. and backend-local behavior.

As long as those remain peer sources of runtime truth, the system stays unstable.

This migration resolves that drift by making the planner-first path authoritative and by demoting direct generation to explicit compatibility behavior only.

---

## 5. Current state

### 5.1 Current live generation path

Historically, generation has effectively been:

1. the API router receives a payload,
2. the router normalizes the payload into a `Frame` or related domain shape,
3. `GenerateText.execute(...)` validates the normalized input,
4. backend generation is invoked too directly,
5. the backend converts the frame into its own realization shape,
6. text is returned.

This path is operational, but it keeps sentence-design logic too close to the API/domain boundary and lets backend-local behavior appear as architecture.

### 5.2 Existing planner path

The repository already includes planner/construction concepts such as:

* generic planning,
* biography planning,
* `PlannedSentence`,
* `construction_id`,
* discourse-related packaging metadata,
* topic/focus-oriented planning behavior.

This proves the repository already has the right abstraction family for a planner-first runtime.

### 5.3 Existing construction layer

The repository already contains multiple construction modules beyond biography, including classes such as:

* equative/classification constructions,
* attributive/copular constructions,
* locative constructions,
* existential constructions,
* possession constructions,
* eventive constructions,
* relative-clause constructions,
* topic-comment structures.

This means the runtime migration must stay generic across construction families rather than collapsing into a bio-only design.

### 5.4 Existing backend diversity

The repository already supports or anticipates multiple realization backends, including:

* GF / PGF,
* family renderers,
* safe-mode or compatibility-style rendering.

The migration must preserve backend flexibility while forcing all backends behind one runtime contract.

### 5.5 Existing drift pattern

The current state has historically allowed a mismatch between:

* what the docs say the architecture is,
* what the planner layer implies the architecture is,
* what the live path actually does,
* and what the public response suggests happened.

That drift is the core migration problem.

---

## 6. Current-state problem summary

The migration addresses the following current-state problems:

1. the public `/generate` path has historically allowed direct engine generation to act as live runtime ownership,
2. planner/construction abstractions exist but have not consistently been the live source of truth,
3. backend-local generation behavior can still appear as architecture,
4. compatibility behavior can still be mistaken for nominal behavior,
5. lexical behavior can remain too hidden inside realization layers,
6. and runtime/public-contract/documentation drift can survive because the live path is not fully aligned with the documented model.

For the immediate EN/FR cutover, additional requirements apply:

* planner-first must be the nominal path for EN and FR bio/person generation,
* FR must not appear successful while surfacing English,
* and compatibility fallback must not count as accepted nominal success.

---

## 7. Migration decision

### 7.1 Authoritative runtime center

After migration, the authoritative runtime center is:

`frame normalization -> frame-to-plan bridge -> planner -> PlannedSentence -> ConstructionPlan -> lexical resolution -> realizer dispatch -> SurfaceResult`

The planner-first construction layer becomes the source of truth for:

* sentence type,
* information packaging,
* construction choice,
* topic/focus metadata,
* slot layout,
* realization options,
* lexical requirements.

Backends become realization layers only.

### 7.2 What is not changing

This migration does not change the following commitments:

* the system remains semantics-first,
* the system remains NLG-first,
* GF remains a realization backend rather than the architecture itself,
* family renderers remain valid realization backends,
* public request compatibility may be preserved at the HTTP boundary during migration,
* immediate implementation scope remains EN + FR bio/person,
* broader runtime design must still remain generic and multilingual.

---

## 8. Core migration goals

The migration has the following goals:

1. make planner-first the nominal `/generate` runtime,
2. make `ConstructionPlan -> SurfaceResult` the authoritative live runtime contract,
3. preserve `PlannedSentence` as the planner-owned sentence-level planning object,
4. remove sentence-logic duplication across router, use case, planner, and renderer adapters,
5. keep GF, family, and safe-mode style realization behind one runtime boundary,
6. preserve current public request compatibility at the normalization boundary where needed,
7. make legacy fallback explicit and machine-readable,
8. standardize renderer-agnostic runtime contracts,
9. support broader construction-family migration without changing the core runtime model,
10. prevent future drift between docs, planner/runtime code, tests, QA, schemas, and public response shaping.

---

## 9. Non-goals

This migration does not aim to:

* redesign semantics from scratch,
* replace GF,
* eliminate family renderers,
* require uniform realization depth across all languages immediately,
* force immediate public payload redesign,
* declare all languages accepted,
* or claim that all construction families are fully migrated now.

Immediate runtime cutover scope is EN + FR bio/person only.
Broader construction-family migration remains part of the architectural target, not proof that every family is complete today.

---

## 10. Target runtime model

### 10.1 Canonical runtime flow

```text
HTTP payload
  -> frame normalization
  -> frame-to-plan bridge
  -> planner
  -> PlannedSentence
  -> ConstructionPlan
  -> lexical resolution
  -> realizer dispatch
       -> gf
       -> family
       -> safe_mode
  -> SurfaceResult
  -> API response mapping
```

### 10.2 Immediate nominal-path rule

For EN and FR bio/person generation, the nominal runtime path must be planner-first.

That means:

* planner-first is the default and intended live path,
* `runtime_path = "planner_first"` on nominal success,
* `fallback_used = false` on nominal success,
* and the public response must serialize a coherent success envelope from that runtime result.

### 10.3 Compatibility rule

If a compatibility fallback still exists during migration, it must satisfy all of the following:

* it is explicit,
* it is machine-readable,
* it is represented in runtime/debug metadata,
* it does not count as nominal planner-first success,
* and it is treated as temporary migration compatibility, not final runtime truth.

---

## 11. Canonical runtime objects

### 11.1 `PlannedSentence`

`PlannedSentence` is the sentence-level planning object.

It carries planner-owned decisions such as:

* `construction_id`,
* sentence packaging intent,
* topic/focus decisions where used,
* discourse-mode or packaging diagnostics where used,
* planner-local provenance,
* and the planner-facing representation of what sentence is being planned.

It is authoritative for what sentence the planner has decided to express.

`PlannedSentence` is upstream of renderer handoff.
It is not the final backend-facing realization contract.

### 11.2 `ConstructionPlan`

`ConstructionPlan` is the canonical planner-to-realizer handoff contract.

It is authoritative for what the runtime is asking the realizer to realize.

It carries, conceptually:

* `construction_id`
* `lang_code`
* `slot_map`
* `generation_options`
* optional `lexical_bindings`
* optional `entity_ref`
* optional `lexeme_ref`
* optional lexical or provenance information
* any other runtime metadata needed by the realizer boundary

No alternate backend-local object may replace `ConstructionPlan` as the authoritative cross-boundary runtime handoff.

### 11.3 `SurfaceResult`

`SurfaceResult` is the canonical realizer output before API serialization.

It is authoritative for what the runtime produced.

It carries, conceptually:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `tokens`
* `debug_info`
* `generation_time_ms`

The mapper may serialize this into the public response envelope, but it must not become the place where planner-first truth first appears.

### 11.4 Why `PlannedSentence` is not the public handoff

Planner-local sentence abstractions may still exist and may remain useful upstream of realization.

However:

* the canonical live runtime handoff for planner-to-realizer is `ConstructionPlan`,
* the canonical realizer-to-API handoff is `SurfaceResult`,
* and the runtime must not leave those boundaries ambiguous.

---

## 12. Authority boundaries

### 12.1 API/router owns

The API/router layer owns:

* transport,
* request validation,
* compatibility normalization,
* HTTP-facing language code handling,
* request metadata.

It does not own:

* sentence design,
* construction choice,
* lexical realization,
* backend-specific syntax,
* or public-contract repair of incomplete nominal runtime results.

### 12.2 Frame-to-plan bridge owns

The frame-to-plan bridge owns:

* mapping normalized frames into planner-ready requests,
* preserving semantic content needed for planning,
* identifying candidate construction families,
* identifying the planner-facing construction problem.

It does not own:

* realization,
* morphology,
* string assembly,
* or backend-local syntax.

### 12.3 Planner owns

The planner owns:

* construction selection,
* sentence packaging,
* slot layout,
* discourse-sensitive decisions,
* planner-facing generation defaults,
* construction-level runtime intent.

The planner does not own:

* backend-specific syntax,
* morphology,
* word-order realization,
* or renderer-local string templating.

### 12.4 Lexical resolution owns

The lexical resolution layer owns:

* lexical binding resolution,
* mapping semantic slots to lexical material,
* lexical fallback behavior where required,
* lexical metadata and provenance where exposed,
* controlled raw-string fallback where required.

It does not own:

* construction choice,
* discourse packaging,
* or silent rewriting of meaning.

### 12.5 Realizer owns

The realizer owns:

* backend-specific realization,
* agreement,
* morphology,
* word order,
* AST construction where relevant,
* surface string assembly,
* and `SurfaceResult`.

The realizer does not own:

* choosing what sentence to say,
* redefining construction semantics,
* inventing alternate runtime meaning,
* or silently replacing the selected construction.

---

## 13. Canonical runtime contracts

### 13.1 Required generic contracts

The migration stabilizes the following generic runtime contracts:

* `planned_sentence`
* `construction_plan`
* `construction_id`
* `slot_map`
* `entity_ref`
* `lexeme_ref`
* `lexical_bindings`
* `generation_options`
* `renderer_backend`
* `surface_result`
* `debug_info`
* `fallback_used`

These contracts must remain generic rather than bio-specific.

### 13.2 Why these contracts must be generic

The repository already contains multiple sentence structures and construction families, not just biography.

Therefore, runtime contracts must not be shaped around one construction family.

Biography lead is one migrated construction family, not the runtime model itself.

### 13.3 Construction ID rule

`construction_id` values must be canonical runtime identifiers shared across:

* docs,
* code,
* tests,
* QA,
* schemas,
* and public-contract expectations.

Do not introduce alternate dotted, renderer-local, or backend-only identifiers as the authoritative runtime name at the shared boundary.

### 13.4 Nominal-path completeness rule

On the nominal planner-first path, required runtime truth must already exist before public mapping.

That means, on nominal success, `construction_id`, `renderer_backend`, `fallback_used`, `lang_code`, `tokens`, and `generation_time_ms` must not exist only as incidental repair data reconstructed later by the API mapper.

### 13.5 Boundary rule

`ConstructionPlan` is the only authoritative planner-to-realizer handoff contract.
`SurfaceResult` is the only authoritative realizer-to-API handoff contract.

No construction family, backend, or compatibility layer may introduce a second private runtime contract and still count as conforming to the planner-first runtime.

---

## 14. Public response relationship

The runtime migration must remain aligned with the canonical public success envelope.

For nominal planner-first success, the public response must serialize:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `tokens`
* `debug_info`
* `generation_time_ms`

The public contract may preserve compatibility behavior where explicitly documented, but the final intended nominal path is one in which the runtime already returns the truth that the mapper serializes.

The mapper is a serialization boundary, not the source of nominal planner-first truth.

---

## 15. Compatibility policy

### 15.1 External API compatibility

Existing `/generate` callers may continue sending current payload shapes during migration.

Compatibility belongs at the normalization boundary.

### 15.2 Internal compatibility rule

Internal runtime code must converge on planner-first contracts.

Downstream of normalization, runtime ownership must shift to:

* frame-to-plan bridging,
* planning,
* lexical resolution,
* realization,
* `SurfaceResult`,
* public mapping.

Compatibility for old input shapes must not leak into downstream runtime contracts.

### 15.3 Temporary fallback rule

Direct frame-to-engine generation may remain only as temporary compatibility fallback during migration.

If present, it must satisfy all of the following:

* it is explicitly invoked,
* it sets machine-readable fallback metadata,
* it never masquerades as nominal planner-first success,
* and it is removed or permanently demoted once the cutover conditions are satisfied.

### 15.4 No compatibility-derived success rule

A legacy-compatible success path does not count as target-state completion merely because it returns usable text.

Compatibility behavior may help preserve service continuity during migration, but it does not redefine the architecture or the nominal runtime.

### 15.5 Boundary rule for legacy payloads

Legacy input-shape compatibility ends at normalization.

Downstream runtime code must consume planner/runtime contracts, not raw payload quirks.

---

## 16. Immediate EN/FR cutover rule

For the immediate implementation scope, this migration must produce all of the following:

1. EN bio/person generation runs planner-first on the nominal path,
2. FR bio/person generation runs planner-first on the nominal path,
3. EN resolves to `WikiEng`,
4. FR resolves to `WikiFre`,
5. FR outputs actually French surface text,
6. the public success envelope is coherent at top level,
7. `fallback_used = false` on nominal EN/FR success,
8. compatibility fallback does not count as EN/FR acceptance.

This migration document does not replace the EN/FR acceptance gate.
It defines the runtime migration conditions that make that gate achievable and meaningful.

---

## 17. Scope of the final version

The final runtime model is not bio-only.

The runtime contracts must remain generic enough to support broader construction families over time, including classes such as:

* equative/classification constructions,
* attributive copular constructions,
* locative constructions,
* existential constructions,
* possession constructions,
* topic-comment constructions,
* eventive clause constructions,
* relative clause constructions,
* biography lead as one specialized construction family among others.

This is an architectural scalability rule, not a claim that all such families are already complete in the immediate EN/FR cutover.

---

## 18. Migration strategy

### 18.1 Strategy summary

This migration is implemented in batches, but the target is the final planner-first runtime model, not a temporary alternative design.

The migration sequence is:

1. document the target runtime fully,
2. define and stabilize the generic runtime contract,
3. wire planner-first orchestration into the live path,
4. migrate construction modules onto the shared contract,
5. externalize lexical resolution,
6. migrate renderers onto the shared contract,
7. retire direct frame-to-engine runtime ownership.

### 18.2 Why documentation comes first

Documentation is first because it prevents further drift in:

* naming,
* interface boundaries,
* object ownership,
* construction coverage,
* migration sequencing,
* and completion criteria.

Without documentation first, code changes will reintroduce local architectural decisions.

---

## 19. Batch plan

### Batch 1 — Documentation alignment

Deliver:

* aligned architecture docs,
* aligned migration docs,
* aligned contract docs,
* aligned testing/acceptance docs,
* aligned API/overview docs,
* one agreed runtime vocabulary.

Exit criteria:

* one authoritative migration story,
* one authoritative runtime vocabulary,
* no contradictory document-level runtime truth.

### Batch 2 — Generic runtime contracts and planning core

Deliver:

* `PlannedSentence`
* `ConstructionPlan`
* slot-map normalization
* shared planning/runtime classes
* planner / realizer / lexical-resolver ports
* frame-to-plan bridge
* construction selector

Exit criteria:

* one backend-agnostic runtime contract in code,
* one authoritative planning path,
* one stable planner-facing vocabulary.

### Batch 3 — API and dependency-injection realignment

Deliver:

* router and dependency updates,
* container wiring,
* `GenerateText` orchestration changes,
* API request/response mapper alignment.

Exit criteria:

* `/generate` runs planner-first for migrated constructions,
* nominal-path truth reaches the mapper in canonical runtime form.

### Batch 4 — Construction module migration

Deliver:

* existing construction modules aligned to the shared slot/spec contract,
* construction registry alignment,
* shared slot-model alignment.

Exit criteria:

* construction logic uses one runtime shape across modules,
* no construction family introduces a second private runtime contract.

### Batch 5 — Lexical resolution layer

Deliver:

* generic lexical resolution adapters,
* entity and predicate resolution helpers,
* controlled raw-string fallback,
* lexical bindings output for realizers.

Exit criteria:

* realizers do not own lexical resolution logic,
* lexical fallback is explicit and traceable.

### Batch 6 — Renderer alignment

Deliver:

* generic realizer adapter boundary,
* GF alignment,
* family-renderer alignment,
* safe-mode or compatibility-renderer alignment.

Exit criteria:

* all active realization backends consume the same `ConstructionPlan` contract,
* all active realization backends return `SurfaceResult`.

### Batch 7 — Family-engine migration

Deliver:

* family backends converted from ad hoc construction entrypoints to shared-contract realization.

Exit criteria:

* language-family engines become realization-only layers.

### Batch 8 — GF grammar/runtime migration

Deliver:

* GF abstract/concrete/runtime surface aligned to construction runtime,
* direct ad hoc bio/event wrappers reduced, isolated, or removed where required.

Exit criteria:

* GF functions as one backend under the same runtime contract,
* GF no longer acts as implicit runtime ownership.

### Batch 9 — Schema alignment

Deliver:

* contract schemas for runtime planning objects,
* frame-schema updates where needed for migrated construction mapping,
* schema names aligned to shared runtime vocabulary.

Exit criteria:

* schemas support the planner-first runtime without forcing backend-shaped payloads.

### Batch 10 — Tests and cutover

Deliver:

* unit, integration, evaluator, and API regression coverage,
* direct-path demotion and/or removal for the cutover scope,
* acceptance alignment,
* cutover completion validation.

Exit criteria:

* planner-first runtime is the only authoritative generation path for the immediate cutover scope.

---

## 20. Migration invariants

The following rules must remain true throughout migration:

1. the planner decides what sentence is being asked for,
2. the realizer decides how the selected backend realizes it,
3. lexical resolution is not hidden inside realizers,
4. API compatibility ends at normalization,
5. `ConstructionPlan` is the only authoritative planner-to-realizer handoff contract,
6. `SurfaceResult` is the only authoritative realizer-to-API handoff contract,
7. nominal planner-first success must expose enough runtime truth for the public contract,
8. no construction may introduce a second hidden runtime contract,
9. no backend may silently replace planner-selected semantics,
10. compatibility fallback must be explicit and machine-readable,
11. routed-but-wrong-language output is not success,
12. public serialization must not contradict runtime truth.

---

## 21. Naming rules

To prevent drift, use these canonical shared runtime names:

* `lang_code`
* `planned_sentence`
* `construction_plan`
* `construction_id`
* `slot_map`
* `entity_ref`
* `lexeme_ref`
* `lexical_bindings`
* `generation_options`
* `renderer_backend`
* `surface_result`
* `debug_info`
* `fallback_used`

Use these runtime/public result names where relevant:

* `text`
* `tokens`
* `generation_time_ms`

### 21.1 Reserved usage rule

* `generation_options` is the canonical cross-boundary options object passed into realization.
* `debug_info` is the canonical structured runtime trace object returned from realization.
* planner-local provenance or internal notes may exist, but they must not replace the canonical runtime names above.

### 21.2 Avoided drift names

Avoid using these as authoritative shared runtime names:

* `surface_text` as the canonical result field name,
* `metadata` as a replacement for `generation_options`,
* `engine_payload`,
* `gf_payload`,
* `template_payload`,
* `render_input`,
* `sentence_spec` as a generic replacement for `construction_plan`.

### 21.3 Generic vs specialized names

Specialized names may still exist locally inside specialized modules, but they must not replace the canonical cross-boundary vocabulary.

Examples of names that remain specialized rather than generic:

* `bio_lead_spec`
* `eventive_clause_spec`

Examples of names that remain generic:

* `planned_sentence`
* `construction_plan`
* `realizer`
* `lexical_resolver`

---

## 22. Risk analysis

### 22.1 Risk: planner/runtime drift survives

If planner-first exists in principle but the live path still derives truth mainly from direct backend generation or mapper repair logic, migration is incomplete.

Mitigation:

* enforce canonical runtime boundaries,
* require nominal-path metadata completeness,
* and keep mapper behavior aligned with serialization rather than repair.

### 22.2 Risk: duplication between planner and realizers

If the planner and realizers both encode sentence packaging logic, the migration fails.

Mitigation:

* construction selection and packaging live only in planner/construction code,
* realizers only realize the given contract.

### 22.3 Risk: bio-specific architecture leak

If runtime contracts are designed around biography, the migration will not scale to the broader construction inventory.

Mitigation:

* keep contracts generic,
* keep construction-specific specs local,
* keep biography as one migrated construction family rather than the runtime model.

### 22.4 Risk: compatibility path becomes permanent runtime ownership

If legacy direct generation remains indefinitely as an unstated co-equal path, drift continues.

Mitigation:

* keep fallback explicit,
* keep fallback machine-readable,
* do not count fallback as target-state success,
* remove or permanently demote direct fallback once the cutover completes.

### 22.5 Risk: backend-local semantics become architecture

If GF or family realizers become implicit owners of construction semantics, the runtime model breaks.

Mitigation:

* keep planner/runtime contracts backend-agnostic,
* treat all realizers as realization layers only.

### 22.6 Risk: lexical fallback stays hidden inside realizers

If lexical fallback remains renderer-local, multilingual behavior remains brittle and hard to reason about.

Mitigation:

* centralize lexical resolution,
* keep lexical fallback explicit,
* expose enough lexical/runtime metadata where required.

### 22.7 Risk: EN/FR appear complete while FR still surfaces English

If FR routes correctly but still surfaces English literals, the migration has failed for the immediate cutover scope.

Mitigation:

* hard evaluator failure,
* acceptance rejection,
* and no routed-but-wrong-language false positives.

### 22.8 Risk: object-boundary ambiguity reappears

If runtime code uses multiple competing objects or silently mixes planner truth, realizer truth, and public truth, ambiguity returns.

Mitigation:

* planner-to-realizer handoff is `ConstructionPlan`,
* realizer-to-API handoff is `SurfaceResult`,
* planner-local sentence planning remains upstream in `PlannedSentence`,
* and public mapping occurs only after the runtime result is complete.

---

## 23. Testing and cutover expectations

### 23.1 Migration completion conditions

For the immediate cutover scope, migration is complete only when:

1. `/generate` uses planner-first orchestration for EN and FR bio/person generation,
2. nominal success exposes runtime truth required by the public contract,
3. EN resolves correctly and surfaces English,
4. FR resolves correctly and surfaces French,
5. FR fails hard if it still looks English,
6. compatibility fallback is explicit where still present,
7. direct frame-to-engine generation is no longer an authoritative EN/FR runtime path,
8. public responses originate from the canonical runtime result.

### 23.2 Minimum regression coverage

Coverage must include at minimum:

* unit tests for planning objects and slot maps,
* unit tests for frame-to-plan mapping,
* unit tests for lexical resolution,
* unit tests for GF and family realizer adapters,
* core use-case tests for planner-first nominal success,
* tests for explicit fallback behavior if fallback still exists,
* tests that fail on missing nominal-path metadata,
* tests for deterministic repeated planner-first behavior,
* evaluator checks for language plausibility and contract shape,
* integration tests for EN planner-first generation,
* integration tests for FR planner-first generation,
* API tests preserving documented request compatibility.

### 23.3 Acceptance relationship

This migration document does not itself replace the EN/FR acceptance gate.

A migrated runtime path is not complete merely because it works operationally.
It must also satisfy the acceptance and evaluator conditions defined elsewhere for the cutover scope.

---

## 24. Operational guidance

### During migration

* prefer explicit compatibility behavior over hidden parallel paths,
* keep `debug_info` structured and machine-readable,
* do not let compatibility normalization leak into downstream runtime contracts,
* do not let public mapping become the source of runtime truth,
* keep backend-local naming out of the shared runtime surface,
* avoid premature grammar rewrites before the runtime contract is fixed.

### After each migration step

* refresh codedump and inventory views,
* verify runtime object names,
* verify that no new parallel runtime path has appeared,
* verify that docs, tests, and code still describe the same runtime model,
* confirm that construction/runtime/public naming still matches the canonical vocabulary.

---

## 25. Definition of done

This migration is done only when all of the following are true:

* planner-first is the authoritative live `/generate` runtime for the immediate cutover scope,
* `PlannedSentence` has stable planner-owned sentence-planning semantics upstream of realization,
* `ConstructionPlan` has stable planner-to-realizer ownership,
* `SurfaceResult` has stable realizer-to-API ownership,
* the mapper serializes canonical runtime truth rather than inventing it,
* compatibility fallback is explicit and non-authoritative,
* EN/FR bio/person generation no longer depends on direct generation as the nominal path,
* the broader runtime model remains generic rather than bio-specific,
* and docs, runtime code, tests, QA, schemas, and public contract all describe the same live model.

---

## 26. Final statement

This migration does not invent a new architecture.

It restores alignment between:

* the documented multilingual runtime architecture,
* the live `/generate` path,
* the planner-first construction runtime,
* the public success contract,
* and the EN/FR cutover truth.

The final live runtime model is therefore:

**planner-first orchestration, planner-owned sentence design, canonical `ConstructionPlan -> SurfaceResult` runtime boundaries, explicit lexical resolution, backend-specific realization behind one shared interface, and explicit compatibility fallback only where still temporarily required.**

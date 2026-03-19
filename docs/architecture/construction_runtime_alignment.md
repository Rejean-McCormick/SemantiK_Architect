# Construction Runtime Alignment

Status: normative alignment document  
Owner: Architecture / Runtime / Grammar / API  
Scope: authoritative runtime alignment for sentence generation in SemantiK Architect  
Immediate implementation scope: EN + FR bio/person cutover as first full vertical slice  
Architectural scope: construction-generic multilingual runtime for future expansion beyond EN/FR

---

## 1. Purpose

This document defines the authoritative runtime alignment for sentence generation in SemantiK Architect (SKA).

Its goal is to eliminate architectural drift between:

- target architecture,
- planner/runtime contracts,
- construction modules,
- lexical resolution,
- renderer backends,
- GF/PGF realization,
- family realization,
- public response mapping,
- and the live `/generate` execution path.

The central decision is:

> **All runtime generation must flow through one shared construction runtime contract.**

No renderer, router, engine, mapper, or compatibility shim may remain an independent source of sentence-planning truth.

This document is not an acceptance report and not an execution checklist.  
It defines the structure that generation code must converge toward.

---

## 2. Architectural statement

The authoritative runtime architecture for sentence generation in SKA is:

```text
external request
  -> request normalization
  -> normalized frame/domain object
  -> frame-to-plan bridge
  -> planner
  -> PlannedSentence
  -> ConstructionPlan
  -> lexical resolution
  -> renderer backend
  -> SurfaceResult
  -> public response mapping
````

This means:

* planning owns sentence intent,
* `ConstructionPlan` is the canonical planner-to-renderer contract,
* lexical resolution is an explicit runtime layer,
* renderers realize rather than plan,
* `SurfaceResult` is the canonical runtime output,
* public HTTP responses are derived from `SurfaceResult`,
* and direct frame-to-renderer generation is not part of the final nominal architecture.

---

## 3. Problem statement

The repository already contains most of the ingredients required for scalable multilingual generation:

* semantic frames,
* discourse/planning structures,
* construction modules,
* family-oriented realization,
* morphology,
* lexicon,
* GF integration,
* runtime metadata,
* and public response shaping.

However, historical evolution has left overlapping centers of truth.

### 3.1 Competing runtime centers

At various points, the system has allowed sentence-generation truth to exist in more than one place:

1. **Documented architecture**

   * semantics
   * constructions
   * family renderers / morphosyntax
   * lexicon
   * planner-first runtime

2. **Planner/runtime model**

   * `PlannedSentence`
   * `construction_id`
   * discourse-aware packaging
   * renderer-neutral planning intent

3. **Direct generation behavior**

   * request payload normalization
   * direct backend invocation
   * backend-owned sentence formation
   * compatibility-driven surface generation

4. **Boundary repair behavior**

   * mappers or wrappers inferring data that should already exist in the canonical runtime result

This document resolves that tension by making the planner-centered construction runtime authoritative and by forcing all public generation behavior to descend from that runtime.

---

## 4. Scope

This alignment applies to:

* API generation,
* internal text-generation use cases,
* planner/runtime orchestration,
* `ConstructionPlan` assembly,
* lexical resolution,
* family-renderer realization,
* GF realization,
* safe-mode realization,
* runtime/debug tracing,
* and public response mapping.

This alignment does **not** require immediate migration of every construction family in one step.

It does require that all migrated generation paths conform to the same final runtime model.

---

## 5. Design principles

### 5.1 One source of runtime truth

The planner and the shared construction runtime contract define **what sentence is being generated**.

Renderers define **how that sentence is realized** in a backend/language/family.

### 5.2 Construction-first, not bio-first

Biography is one migrated construction family.
It is not the architecture.

### 5.3 Backend independence

The same `ConstructionPlan` must be realizable by:

* family renderer,
* GF renderer,
* safe-mode renderer,
* and future renderer backends.

### 5.4 Language-neutral shared runtime

Shared runtime layers must not encode natural-language surface strings.

Language-specific realization belongs to concrete language modules and/or realization backends, not to shared runtime orchestration.

### 5.5 Explicit lexical resolution

Lexical resolution is an explicit layer between planning and realization.
It must not be hidden inside renderers.

### 5.6 Explicit fallback

Capability gaps, compatibility paths, and backend/language downgrades must be explicit and machine-readable.
They must never be hidden as if they were nominal success.

### 5.7 Boundary clarity

Runtime contracts, public HTTP contracts, and frontend/client convenience layers are distinct.
They must remain distinct.

### 5.8 No duplicated planning logic

Planning truth must not be duplicated across:

* routers,
* use cases,
* GF wrappers,
* family renderers,
* construction modules,
* or response mappers.

---

## 6. Target runtime architecture

## Layer 1 — Request normalization

### Responsibility

Convert external payloads into normalized internal frame/domain objects.

### Rules

* tolerate external payload variations only here,
* normalize frame family and fields once,
* do not perform realization here,
* do not construct backend-specific ASTs here,
* do not select backend-owned sentence templates here.

### Output

A normalized internal frame/domain object.

---

## Layer 2 — Frame-to-plan bridge

### Responsibility

Map normalized semantic input to planner-ready sentence design input.

### This layer may do things like

* choose classification vs locative vs possession vs eventive,
* select one-sentence vs multi-sentence candidates,
* assign canonical `construction_id`,
* preserve provenance,
* attach fallback justification where appropriate.

### This layer must not do

* backend-specific AST creation,
* morphology,
* final wording,
* direct GF or family surface building.

### Output

A planner-ready sentence design request.

---

## Layer 3 — Planner

### Responsibility

Produce sentence-level planning objects that are backend-neutral and semantically authoritative.

### Planner owns

* sentence intent,
* construction selection finalization,
* sentence packaging,
* topic/focus choices,
* discourse-sensitive organization,
* sentence-level ordering decisions at the semantic/planning level,
* fallback construction selection where required,
* default `generation_options`.

### Planner does not own

* inflection,
* morphology,
* surface string concatenation,
* backend-specific AST creation,
* direct language templates.

### Output

One or more `PlannedSentence` objects.

---

## Layer 4 — ConstructionPlan assembly

### Responsibility

Convert planner output into the canonical renderer-facing runtime contract.

### This layer owns

* transforming `PlannedSentence` into `ConstructionPlan`,
* constructing canonical `slot_map`,
* validating required and optional roles,
* attaching `generation_options`,
* preserving lexical requirements,
* preserving planner-owned intent fields where needed,
* ensuring construction completeness before realization.

### This layer does not own

* backend-specific realization,
* morphology,
* final wording,
* renderer-owned fallback formatting.

### Output

A validated `ConstructionPlan`.

---

## Layer 5 — Lexical resolution

### Responsibility

Resolve semantic roles into lexicalized units usable by renderers.

### Examples

* entity naming strategy,
* profession lemma lookup,
* nationality/adjectival form lookup,
* predicate lexical features,
* language-specific lemma selection,
* controlled lexical fallback.

### Rule

Lexical resolution is not realization.

It prepares lexical material for realization while preserving semantic identity.

### Output

A lexicalized `ConstructionPlan` with stable runtime references in `slot_map` and optional `lexical_bindings`.

---

## Layer 6 — Renderer backend

### Responsibility

Consume the canonical construction runtime contract and produce a realized surface result.

### Backends

* family renderer,
* GF renderer,
* safe-mode renderer,
* future renderers that implement the same boundary.

### Renderer owns

* backend-specific realization refinements that are strictly realization-local,
* morphology invocation,
* idiomatic linearization choices within backend limits,
* AST construction for GF,
* controlled explicit fallback formatting where authorized.

### Renderer does not own

* frame normalization,
* construction selection,
* semantic role discovery,
* discourse truth,
* hidden construction substitution,
* hidden planner replacement.

### Output

A canonical `SurfaceResult`.

---

## Layer 7 — SurfaceResult and public response mapping

### Responsibility

Return a canonical runtime result and map it to the public response contract.

### Canonical runtime result

Runtime generation returns `SurfaceResult`.

### Public response mapping

Public HTTP success mapping is derived from `SurfaceResult`.

The public mapper may serialize and enforce public shape consistency, but it must not become the hidden source of planner-first truth.

---

## 7. Authoritative runtime contract

The runtime must converge on one shared construction contract for all migrated constructions.

## 7.1 Required runtime objects

### `PlannedSentence`

Planner-facing sentence-level object representing one sentence candidate.

### `ConstructionPlan`

Canonical planner-to-renderer contract for one construction.

### `SlotMap`

Canonical mapping of semantic roles to runtime slot payloads.

### `EntityRef`

Normalized entity reference used in slots.

### `LexemeRef`

Normalized lexical reference used in slots.

### `SurfaceResult`

Canonical renderer result before public HTTP serialization.

### `generation_options`

Canonical cross-boundary realization-options object.

### `debug_info`

Canonical structured runtime tracing object.

### `fallback_used`

Canonical machine-readable indicator that compatibility or capability fallback occurred.

---

## 7.2 Canonical flow contract

The canonical migrated runtime flow is:

`normalized input -> PlannedSentence -> ConstructionPlan -> lexical resolution -> SurfaceResult`

The public HTTP layer exists after `SurfaceResult`, not in place of it.

---

## 7.3 Canonical `SurfaceResult`

`SurfaceResult` is the canonical runtime result object.

At minimum it must support:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `tokens`
* `debug_info`
* `generation_time_ms`

A renderer/backend may produce additional runtime-local diagnostic information, but it must not replace these canonical fields.

---

## 8. Canonical naming rules

The following names are canonical across planner and renderer boundaries.

### 8.1 Required shared names

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
* `generation_time_ms`

### 8.2 Planner-local names allowed where relevant

* `normalized_frame`
* `topic_entity_id`
* `focus_role`
* `discourse_mode`

### 8.3 Naming style

* construction IDs use stable backend-independent `snake_case`,
* slot names use stable semantic `snake_case`,
* backend-specific names must not cross the runtime contract boundary.

### 8.4 Avoided drift names

The following must not replace canonical runtime names:

* `metadata` as a replacement for `generation_options`
* `surface_text` as a replacement for `SurfaceResult`
* backend-private construction IDs
* backend-private payload names such as `gf_payload` or `engine_payload`

Compatibility shims may temporarily recognize drift names at explicit boundaries, but those names are not canonical.

---

## 9. Construction contract rules

Every construction must define:

* its `construction_id`,
* required roles,
* optional roles,
* validation rules,
* sentence-kind expectations,
* lexical requirements,
* renderer capability expectations,
* and fallback behavior.

### Example construction families

* `copula_equative_simple`
* `copula_equative_classification`
* `copula_attributive_adj`
* `copula_attributive_np`
* `copula_locative`
* `copula_existential`
* `possession_have`
* `possession_existential`
* `topic_comment_copular`
* `topic_comment_eventive`
* `intransitive_event`
* `transitive_event`
* `ditransitive_event`
* `relative_clause_subject_gap`
* `relative_clause_object_gap`

Biography lead behavior may be a migrated specialization, but it must still conform to the same generic construction runtime contract.

---

## 10. Boundary rules

## 10.1 Planner boundary

### Planner input

The planner consumes normalized frames and planning metadata.

### Planner output

The planner emits backend-neutral `PlannedSentence` objects.

### Rule

No planner output may embed GF-only, family-only, or backend-private structures as its primary representation.

---

## 10.2 ConstructionPlan boundary

### Input

This layer consumes `PlannedSentence`.

### Output

It emits `ConstructionPlan` with at least:

* `construction_id`
* `lang_code`
* `slot_map`
* `generation_options`

It may also preserve:

* `topic_entity_id`
* `focus_role`
* `discourse_mode`
* `lexical_bindings`
* provenance data

### Rule

All semantic content required for realization must be present in `slot_map` before rendering begins.

---

## 10.3 Renderer boundary

### Input

Each renderer consumes the same logical input:

* `construction_plan`

Optional renderer-specific context may be passed only through controlled fields on the shared contract, never through ad hoc payload shape changes.

### Output

Each renderer returns canonical `SurfaceResult`.

### Allowed

* GF AST creation
* family morphology invocation
* safe-mode formatting
* explicit backend fallback behavior

### Not allowed

* changing construction semantics
* redefining slot meanings
* selecting a different construction without planner approval

---

## 10.4 Public response boundary

### Input

Public mapping consumes `SurfaceResult`.

### Output

Public mapping emits the canonical public success envelope.

### Rule

The public layer may serialize, normalize, and preserve explicit compatibility behavior where intentionally allowed.

It must not be the place where nominal planner-first truth first appears.

In particular, the nominal planner-first path must not rely on the public mapper to invent missing `construction_id`, `renderer_backend`, `fallback_used`, or equivalent canonical fields.

---

## 10.5 Frontend/client boundary

Frontend/client layers may provide convenience views or type wrappers.

They must not redefine:

* runtime contracts,
* public HTTP contracts,
* or planner-to-renderer semantics.

---

## 11. GF in the aligned architecture

GF remains valuable, but its role is constrained.

### GF is

* a realization backend,
* a typed grammar backend,
* a high-fidelity renderer for supported constructions and languages.

### GF is not

* the source of semantic truth,
* the construction selector,
* the only runtime architecture,
* the only multilingual strategy.

### Required GF alignment

GF adapters must consume `ConstructionPlan` and `slot_map`.

This implies:

* no permanent direct `frame -> GF AST` runtime path,
* grammar functions must align with construction contracts,
* GF wrappers are renderer adapters, not sentence planners.

---

## 12. Family renderers in the aligned architecture

Family renderers remain central for scale.

### Why

For large multilingual support, family-level sharing is mandatory.
The architecture must avoid bespoke per-language business logic as the default scaling model.

### Family renderers should own

* family-level morphosyntactic strategies,
* agreement policies,
* article and word-order behaviors where shared,
* fallback realization for languages without full GF support.

### Family renderers should not own

* API payload parsing,
* semantic role discovery,
* frame normalization,
* construction selection,
* hidden planner replacement.

---

## 13. Lexicon in the aligned architecture

Lexicon is a shared subsystem, not a renderer detail.

### Lexicon responsibilities

* canonical code normalization,
* lemma lookup,
* feature lookup,
* entity naming support,
* lexical fallback selection.

### Lexicon must be reusable by

* GF renderer,
* family renderer,
* safe-mode renderer,
* planner support code where explicitly allowed.

### Rule

Lexicon prepares lexical material.
It does not replace planning and it does not replace realization.

---

## 14. Public HTTP relationship

This document defines the runtime contract, not the public HTTP contract.

### Rule

Runtime and public contracts are related but distinct.

* `SurfaceResult` is the canonical runtime output.
* Public HTTP success responses are derived from `SurfaceResult`.
* Frontend/client convenience fields are downstream concerns.

### Consequence

A runtime field is not automatically a public field unless the public response contract defines it.

A public field must not contradict the runtime truth it descends from.

---

## 15. Debug and provenance model

All runtime generation must return structured machine-readable debug metadata.

### 15.1 Minimum shared debug expectations

* `construction_id`
* `renderer_backend`
* `fallback_used`

### 15.2 Recommended shared diagnostics

* planning metadata
* lexical-resolution metadata
* backend realization metadata
* timing metadata
* warnings/errors where relevant

### 15.3 Rule

Fallbacks, downgrades, and compatibility shims must be visible in runtime metadata.

`debug_info` must support diagnosis, but it must not serve as a hidden replacement for canonical top-level runtime fields on the nominal planner-first path.

---

## 16. Compatibility model

## 16.1 Short-term compatibility

External API shape stability may be preserved while internals are migrated.

Allowed temporary shape:

```text
request
  -> normalize input
  -> planner-centered runtime
  -> SurfaceResult
  -> public response
```

with explicit compatibility handling at the request/response boundary where intentionally allowed.

## 16.2 Forbidden long-term shape

```text
request
  -> normalize input
  -> direct backend generation
  -> response
```

except as a temporary compatibility shim.

## 16.3 Compatibility boundary rule

Compatibility handling belongs at explicit boundaries.

It must not become the hidden runtime architecture.

---

## 17. Migration intent

This architecture must be implemented to the final target shape, not as a permanent partial fork.

### Final migration goal

All generation code paths converge on:

* one planning contract,
* one construction runtime contract,
* one lexical-resolution layer,
* one renderer boundary,
* multiple renderer implementations.

### First migrated constructions

Initial migration may begin with biography-oriented behavior or other high-value constructions, but each migrated path must be implemented as part of the generic runtime architecture, not as a special architecture of its own.

---

## 18. Invariants

The following invariants are mandatory.

### Invariant 1 — Construction identity is explicit

Every realized sentence must have a `construction_id`.

### Invariant 2 — Planner output is backend-neutral

No planner output may embed GF-only or family-only logic as its primary representation.

### Invariant 3 — Renderer behavior is substitutable

Any renderer must be able to consume the same `ConstructionPlan` for a supported construction.

### Invariant 4 — No hidden semantic reinterpretation

Renderers may refine realization, but they may not reinterpret slot semantics.

### Invariant 5 — Lexical resolution is explicit

Lexical resolution must exist as its own runtime layer between planning and realization.

### Invariant 6 — Debug info is structured

All runtime generation must return structured machine-readable debug/provenance metadata.

### Invariant 7 — Fallback is explicit

Fallback backend or capability downgrade must be visible in canonical runtime fields and related `debug_info`.

### Invariant 8 — Public responses originate from shared runtime truth

Public generation responses may remain backward-compatible, but they must originate from `SurfaceResult`, not backend-private payloads.

### Invariant 9 — One cross-boundary options object

`generation_options` is the canonical shared realization-options object.
No parallel generic `metadata` object may replace it at the planner-to-renderer boundary.

### Invariant 10 — Boundary layers remain distinct

Runtime, public HTTP, and frontend/client convenience layers must not collapse into one another.

### Invariant 11 — Shared runtime is language-neutral

Shared runtime layers must not encode language-specific surface strings as if they were language-neutral logic.

---

## 19. Non-goals

This document does not require:

* immediate migration of every construction in one commit,
* immediate full GF coverage for all languages,
* elimination of all compatibility code on day one,
* redesign of all schemas before runtime contract definition,
* or simultaneous completion of the entire multilingual system.

This document also does not authorize:

* a bio-only architecture fork,
* backend-specific runtime contracts,
* direct router-to-renderer sentence logic as a permanent pattern,
* public mapper repair as a permanent substitute for canonical runtime truth.

---

## 20. Risks if not adopted

If the system continues without this alignment, likely failure modes include:

* duplicated generation logic in multiple layers,
* drift between docs and runtime behavior,
* GF wrappers owning construction logic,
* family renderers diverging in input assumptions,
* poor scalability across large language inventories,
* hidden compatibility behavior masquerading as nominal success,
* inconsistent debug/provenance behavior,
* public/runtime/frontend contract collapse,
* and increased regression risk whenever new constructions are added.

---

## 21. Benefits if adopted

* one authoritative runtime center,
* reduced architectural drift,
* explicit planner-to-renderer contracts,
* explicit lexical-resolution layer,
* clean backend substitution,
* better multilingual scalability,
* clearer testing strategy,
* easier migration of existing constructions,
* cleaner separation of semantics vs realization,
* more robust public-contract consistency,
* and safer future extension beyond bio/person generation.

---

## 22. Ownership

### 22.1 Architecture authority

This document governs all new generation/runtime changes.

### 22.2 Enforcement rule

Any new generation feature must answer all of the following before implementation:

1. What is the `construction_id`?
2. What are the required and optional roles?
3. What does `PlannedSentence` look like?
4. What does `ConstructionPlan` look like?
5. How is lexical resolution performed?
6. Which renderers support it?
7. What is fallback behavior?
8. What runtime metadata will be returned?
9. What public fields, if any, will be exposed downstream?
10. How is boundary separation preserved?

If these are not defined, the feature is not ready for implementation.

---

## 23. Implementation consequence summary

The codebase must be updated so that:

* request normalization becomes explicit,
* frame-to-plan mapping becomes explicit,
* planner output becomes authoritative,
* `ConstructionPlan` assembly becomes explicit,
* lexical resolution becomes explicit,
* renderers consume `ConstructionPlan`,
* `SurfaceResult` becomes the canonical runtime result,
* public responses descend from `SurfaceResult`,
* GF and family renderers implement the same runtime boundary,
* and direct frame-to-renderer generation is permanently demoted to compatibility support only.

---

## 24. Relationship to other documents

This document should be read together with:

* `docs/architecture/EN_FR_FINAL_PARALLEL_LOCKDOWN.md`
* `docs/architecture/multilingual_runtime_target.md`
* `docs/migration/en_fr_cutover_plan.md`
* `docs/contracts/construction_runtime_contract.md`
* `docs/contracts/public_generation_response_contract.md`
* `docs/contracts/public_vs_runtime_vs_frontend_boundaries.md`
* `docs/testing/EN_FR_bio_acceptance.md`
* `docs/testing/en_fr_acceptance_and_multilingual_readiness.md`

Conflict rule:

* if the issue is execution-time precedence for parallel work, the lock document wins,
* if the issue is target multilingual architecture, the multilingual runtime target wins,
* if the issue is runtime contract shape, the construction runtime contract wins,
* if the issue is runtime alignment and boundary discipline, this document wins,
* if the issue is cutover sequencing, the cutover plan wins,
* if the issue is public HTTP success shape, the public response contract wins,
* if the issue is final EN/FR acceptance, `EN_FR_bio_acceptance.md` wins,
* if the issue is broader multilingual readiness framing, `en_fr_acceptance_and_multilingual_readiness.md` wins.

---

## 25. Final decision

The authoritative generation architecture for SKA is:

```text
request normalization
  -> normalized semantic input
  -> frame-to-plan bridge
  -> planner
  -> PlannedSentence
  -> ConstructionPlan
  -> lexical resolution
  -> renderer backend
  -> SurfaceResult
  -> public response mapping
```

This is the structure that all migrated generation code must implement and all future construction work must follow.

No renderer, mapper, router, wrapper, or compatibility path may replace this architecture as a parallel source of truth.



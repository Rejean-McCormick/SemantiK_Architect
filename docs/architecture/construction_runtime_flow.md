# Construction Runtime Flow

Status: normative
Owner: Architecture / Runtime
Scope: define the authoritative runtime flow for sentence generation across all constructions in SemantiK Architect

---

## 1. Purpose

This document defines the **authoritative runtime flow** for text generation in SemantiK Architect.

It exists to prevent drift between:

1. the documented architecture,
2. the planner and discourse layer,
3. the live API generation path,
4. the lexical resolution layer,
5. the realization backends,
6. the public response contract,
7. and the acceptance and evaluation model.

The core decision is:

> **Runtime generation is planner-first, construction-centered, and renderer-neutral at the shared runtime boundary.**

The authoritative flow is:

`HTTP payload -> request normalization -> canonical frame/domain shape -> planner -> ConstructionPlan -> lexical resolution -> realizer -> backend realization -> SurfaceResult -> public response mapping -> API response`

The runtime must **not** be organized as:

`raw frame -> backend-specific renderer -> surface text`

It must also **not** be organized as:

`request mapper -> backend shortcut -> debug-filled response`

The planner-first runtime is the nominal architecture. Any direct frame-to-backend behavior is compatibility-only during migration and is not a peer architecture.

---

## 2. Architectural context

SemantiK Architect is a multilingual generation system that separates:

* semantics,
* construction selection,
* discourse packaging,
* lexical resolution,
* morphosyntax,
* realization backends,
* and public response serialization.

The target runtime model is:

`canonical input -> planner -> lexical resolution -> realizer -> SurfaceResult -> public response`

The system therefore distinguishes:

* **runtime contracts**,
* **public HTTP contracts**,
* and **frontend/client consumption models**.

This document defines the runtime flow inside that architecture and the handoff points between:

* request normalization,
* planning,
* lexicalization,
* realization,
* and response mapping.

---

## 3. Problem statement

## 3.1 Historical mismatch

The repository has contained both:

1. a documented planner/construction architecture, and
2. live generation paths that could bypass planner-centered construction handling.

That is acceptable as a migration state, but it is not acceptable as the final architecture.

## 3.2 Main risk

If generation remains backend-centered, then:

* GF adapters,
* family engines,
* safe-mode renderers,
* runtime bridges,
* routers,
* or mappers

can each become hidden sources of sentence-planning logic.

That would break the architecture’s core goal of shared, construction-level runtime semantics.

## 3.3 Goal of this document

Define one runtime flow that:

* works for **all constructions**, not just biography,
* keeps the planner authoritative,
* allows multiple backends,
* scales across languages,
* preserves one shared runtime contract,
* and cleanly separates runtime truth from HTTP serialization.

---

## 4. Final runtime decision

## 4.1 Authoritative runtime source of truth

The runtime source of truth for sentence generation is:

1. normalized semantic input,
2. planner construction selection,
3. planner slot assignment,
4. lexical resolution,
5. realization through a shared runtime contract,
6. and emission of a canonical `SurfaceResult`.

## 4.2 Backend role

Backends do **not** decide the sentence’s semantic structure.

Backends decide only:

* how a selected construction is realized in a target language,
* how morphology, agreement, and word order are handled,
* how backend-specific realization is assembled,
* and how explicit backend fallback is executed and reported.

## 4.3 Mapper role

The response mapper is a **serialization boundary**, not a planner or realizer.

It maps a canonical runtime result into the public HTTP success envelope.

It must not be the place where nominal planner-first truth first appears.

## 4.4 Summary rule

* the planner decides **what is to be said**
* the lexical resolver decides **which lexical identities fill the slots**
* the realizer decides **how the target language says it**
* the response mapper decides **how the runtime result is serialized publicly**

---

## 5. Runtime layers

## 5.1 Layer A — Request normalization

### Responsibility

* accept HTTP payloads and tolerated compatibility variants,
* normalize them into authoritative internal frame or domain objects,
* attach request metadata needed for downstream orchestration,
* stop transport-specific quirks at the boundary.

### Examples

* `BioFrame`
* `EventFrame`
* relational or entity frames
* other normalized frame families

### Must do

* normalize language fields,
* normalize compatibility payload shapes,
* normalize legacy aliases,
* preserve semantic intent for downstream planning.

### Must not do

* language-specific wording,
* construction realization,
* backend-specific AST creation,
* hidden sentence templating,
* renderer selection,
* public response shaping.

---

## 5.2 Layer B — Planning entry

### Responsibility

* accept the normalized frame or domain object,
* interpret it as a planning problem,
* select the construction family,
* prepare planner-authoritative runtime semantics.

### Outputs

* planner input
* candidate or finalized `construction_id`
* canonical semantic role expectations
* discourse-relevant planning metadata

### Examples

* `copula_equative_classification`
* `copula_locative`
* `topic_comment_eventive`
* `topic_comment_copular`
* biography lead selection as one construction family among many

### Must not do

* backend-local realization,
* inflection,
* morphology,
* direct string templating.

---

## 5.3 Layer C — Planning

### Responsibility

* finalize construction choice,
* assign semantic roles into canonical slots,
* produce the planner-authoritative runtime object,
* assign topic and focus metadata,
* attach planner metadata needed for realization.

### Outputs

* `PlannedSentence` as a planner concept where still used,
* `ConstructionPlan` as the authoritative realization handoff,
* `construction_id`,
* `slot_map`,
* `topic_entity_id`,
* `focus_role`,
* `metadata`.

### Notes

`PlannedSentence` and `ConstructionPlan` may coexist during migration, but realization is governed by the `ConstructionPlan` contract.

The planner owns:

* sentence packaging,
* construction identity,
* slot assignment,
* discourse-sensitive information structure,
* semantic-level realization options.

The planner does **not** own:

* inflection,
* morphology,
* backend-specific AST creation,
* backend-specific syntax templates,
* final string assembly.

---

## 5.4 Layer D — Lexical resolution

### Responsibility

* resolve slot values into stable lexical or entity identities,
* preserve slot structure while enriching lexical identity,
* attach lemma, features, provenance, confidence, and fallback notes where needed,
* remain reusable across constructions, renderers, and languages.

### Examples

* profession lemma resolution,
* predicate nominal resolution,
* nationality or adjectival lookup,
* entity label normalization,
* alias normalization,
* controlled raw-string fallback.

### Output

A lexicalized `ConstructionPlan`, typically by enriching the existing `slot_map` rather than replacing the runtime contract.

### Must not do

* change sentence meaning,
* change planner-owned information packaging,
* change the selected construction,
* become a hidden surface realizer.

---

## 5.5 Layer E — Realization orchestration

### Responsibility

* consume the lexicalized `ConstructionPlan`,
* choose the realization backend explicitly,
* validate backend capability against language and construction,
* invoke the backend behind a shared realization interface,
* produce one canonical `SurfaceResult`.

### Canonical backends

* `family`
* `gf`
* `safe_mode`

Additional backends are allowed only if they consume the same construction-level runtime contract.

### Realization orchestration owns

* backend selection,
* capability checks,
* backend dispatch,
* fallback policy application,
* stable runtime result assembly.

### Must not do

* redefine semantic structure,
* re-plan the sentence,
* reassign canonical slot ownership,
* bypass the construction runtime contract.

---

## 5.6 Layer F — Backend realization

### Responsibility

Backends consume the same construction-level runtime contract and own:

* morphology,
* agreement,
* word-order realization,
* backend-local AST or template assembly,
* controlled backend fallback,
* language-specific realization details.

### Backends do not own

* request normalization,
* construction selection,
* semantic role assignment,
* canonical lexical normalization,
* public response shaping.

---

## 5.7 Layer G — Public response mapping

### Responsibility

* map the canonical runtime result into the public API success envelope,
* preserve authoritative top-level fields,
* preserve fallback visibility,
* preserve timing and tokens,
* ensure top-level and debug parity rules,
* serialize the result for HTTP transport.

### Output

A stable response mapped from `SurfaceResult`.

### Must not do

* invent missing nominal runtime truth,
* repair a planner-first result that lacks required nominal fields,
* become a second planner,
* become a hidden compatibility renderer.

---

## 6. Canonical runtime flow

## 6.1 High-level flow

```text id="zf9v3q"
HTTP request
  -> request normalization
  -> normalized frame/domain shape
  -> planner
  -> ConstructionPlan
  -> lexical resolution
  -> realizer
  -> backend realization
  -> SurfaceResult
  -> public response mapping
  -> HTTP response
```

## 6.2 Flow in terms of runtime objects

```text id="eyv28m"
Request JSON
  -> normalized_frame
  -> planned_sentence
  -> construction_plan
  -> lexicalized_construction_plan
  -> surface_result
  -> Response JSON
```

## 6.3 Authoritative runtime chain

```text id="jjz5tr"
generation router
  -> request mapper / normalization
  -> GenerateText / planning orchestration
  -> planner
  -> lexical resolver
  -> realizer
  -> renderer backend
  -> SurfaceResult
  -> response mapper
```

## 6.4 Compatibility rule

Any direct `frame -> engine.generate(...)` path is compatibility-only during migration.

It must not be treated as an architectural peer to the planner-first runtime.

---

## 7. Canonical data contracts

This document does not define full schemas, but it defines the runtime boundaries.

## 7.1 Semantic input

A normalized semantic frame must contain:

* `frame_type`
* normalized semantic content
* discourse-relevant entity information where available

Examples include:

* `BioFrame`
* `EventFrame`
* relational or entity frames
* generic normalized frame objects

## 7.2 Construction plan

A `ConstructionPlan` must contain at least:

* `construction_id`
* `lang_code`
* `slot_map`
* `topic_entity_id`
* `focus_role`
* `metadata`

### Alignment note

`metadata` is the canonical shared option bag for the runtime contract.

If another temporary interface refers to `generation_options` or a similar name, it must be normalized into `metadata` at the contract boundary.

## 7.3 Slot map

A `slot_map` contains semantically or constructionally named inputs, for example:

* `subject`
* `predicate_nominal`
* `predicate_adjective`
* `location`
* `event`
* `agent`
* `patient`
* `theme`
* `time`
* `topic`
* `comment`
* `profession`
* `nationality`

Slot names must be semantic or constructional, not backend-specific.

## 7.4 Lexical resolution result

Lexical resolution enriches slot values with:

* entity or lexeme identity,
* lemma,
* part of speech,
* lexical features,
* provenance,
* confidence,
* explicit fallback notes.

Lexical resolution does not change sentence meaning or planner-owned packaging.

## 7.5 Surface result

A `SurfaceResult` must contain:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `tokens`
* `debug_info`
* `generation_time_ms`

### Alignment note

`SurfaceResult` is the canonical renderer output before API response mapping.

Older wording such as `Sentence` or `sentence result` should be interpreted as this canonical runtime result unless another layer is explicitly defined.

### Nominal-path rule

On the nominal planner-first path, these fields must already exist before public response mapping.

The mapper serializes them. It does not invent them.

---

## 8. Sequence flow

## 8.1 Request-time flow

```text id="v5kxk4"
Client
  -> API Router
  -> Request Normalizer
  -> Planner
  -> Lexical Resolver
  -> Realizer
  -> Backend
  -> Response Mapper
  -> Client
```

## 8.2 Expanded step sequence

1. Client submits payload.
2. Router validates and normalizes payload.
3. Runtime obtains a normalized frame or domain object.
4. Planner selects and finalizes the construction.
5. Planner emits `ConstructionPlan`.
6. Lexical resolver enriches plan slots.
7. Realizer chooses a backend explicitly.
8. Backend realizes the construction.
9. Runtime emits `SurfaceResult`.
10. Response mapper serializes the public envelope.
11. Client receives the response.

## 8.3 Authority sequence

The authority order is:

`normalization -> planner -> lexical resolution -> realizer -> backend -> SurfaceResult -> response mapper`

The authority order is **not**:

`normalization -> backend -> string -> response repair`

---

## 9. Backend dispatch model

## 9.1 Why dispatch exists

Different languages and constructions require different realization strengths.

The runtime therefore supports multiple renderer backends behind one interface.

## 9.2 Backends

### A. Family-construction backend

Use when:

* the language family is supported,
* family realization exists for the construction,
* morphology or configuration data is available.

Best for:

* scalable multilingual support,
* family-shared realization,
* morphology-aware generation.

### B. GF-construction backend

Use when:

* a GF realization exists,
* the grammar path is healthy,
* the construction is representable in the available grammar.

Best for:

* high-quality controlled realization,
* deterministic grammar-backed output,
* selected high-support constructions and languages.

### C. Safe-mode backend

Use when:

* no stronger backend is available,
* capability is partial,
* the runtime must still produce a controlled fallback.

Best for:

* degraded mode,
* partial-coverage languages,
* continuity and debugging.

## 9.3 Dispatch rule

Dispatch is selected by:

* language capability,
* construction capability,
* backend readiness,
* runtime configuration,
* explicit fallback policy.

Dispatch must never change the semantic meaning of the plan.

Dispatch choice must be visible in:

* `renderer_backend`
* `fallback_used`
* `debug_info`

---

## 10. Relationship to the planner

## 10.1 Planner is authoritative

The planner is the runtime authority for:

* selecting `construction_id`,
* determining information packaging,
* assigning roles into `slot_map`,
* topic and focus metadata,
* sentence-level semantic ordering.

## 10.2 Planner is not a renderer

The planner must not:

* inflect words,
* choose backend-specific syntax as the shared runtime contract,
* emit backend-specific ASTs as the primary contract,
* perform final string concatenation.

## 10.3 Planner output is not optional side-data

Planner-side concepts such as:

* `PlannedSentence`
* `construction_id`
* `topic_entity_id`
* `focus_role`

are part of the planner-centered runtime model.

They are not optional decoration.

---

## 11. Relationship to constructions

## 11.1 Constructions are explicit runtime units

Constructions are explicit runtime units for semantic and syntactic packaging.

Examples include:

* equative or classification structures,
* attributive copular structures,
* locative structures,
* existential structures,
* possession structures,
* topic-comment structures,
* eventive structures,
* relative clauses,
* coordination.

## 11.2 Construction contract

Every construction must define:

* `construction_id`
* required slots
* optional slots
* validation assumptions
* realization assumptions
* capability notes where needed

## 11.3 Anti-pattern

A backend must not invent a private sentence type that bypasses the shared construction registry.

If a sentence type exists at runtime, it must be represented as an explicit construction with a registered contract.

---

## 12. Relationship to lexicon

## 12.1 Lexicon is separate by design

The lexicon subsystem remains separate from renderers.

This matters because lexical data must be reusable across:

* multiple constructions,
* multiple backends,
* multiple languages,
* QA and coverage tooling.

## 12.2 Runtime rule

Renderers consume lexical resolution results.

They do not own canonical lexical normalization.

## 12.3 Local vs external lexical sources

Runtime lexical resolution may combine:

* local lexicon data,
* alias or normalization tables,
* optional external identifiers such as QIDs,
* controlled raw-string fallback.

The runtime contract must remain stable even when lexical information is partial.

---

## 13. Relationship to morphology

## 13.1 Realization remains first-class

Morphology engines and grammar-based realization remain first-class components.

This flow preserves that design.

## 13.2 Morphology responsibility

Morphology layers are responsible for:

* inflection,
* feature-driven surface realization,
* agreement,
* family-specific or grammar-specific helper logic.

They are not responsible for deciding sentence meaning or construction choice.

## 13.3 Construction-to-morphology boundary

The `ConstructionPlan` determines:

* what roles exist,
* what lexical items are needed,
* what semantic packaging was chosen.

The renderer or morphology layer determines how those roles and lexical items surface in the target language.

---

## 14. Relationship to the public response contract

## 14.1 Runtime vs public boundary

`SurfaceResult` is a runtime object.

The public HTTP success envelope is a transport object derived from it.

They are aligned, but they are not the same boundary layer.

## 14.2 Public contract rule

The public success envelope must expose:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `tokens`
* `debug_info`
* `generation_time_ms`

## 14.3 Boundary rule

The response mapper may:

* normalize field names,
* enforce parity,
* serialize transport shape.

It must not:

* create missing nominal planner-first truth,
* hide fallback on the nominal path,
* contradict runtime top-level authority.

---

## 15. Current implementation gap

## 15.1 Existing mismatch

The live runtime may still contain direct frame-to-engine or compatibility-oriented generation behavior.

That means some semantic frames may still bypass the planner-first construction runtime contract.

## 15.2 Why this matters

This creates drift risk:

* planner logic can be bypassed,
* backend-specific assumptions can become hidden architecture,
* one domain can distort the generic runtime model,
* a mapper can appear to fix what runtime did not actually produce.

## 15.3 Resolution

The target authority order is:

`request normalization -> planner -> ConstructionPlan -> lexical resolution -> realizer -> backend -> SurfaceResult -> public response mapping`

Any direct frame-to-backend generation path is compatibility-only.

---

## 16. Migration policy

## 16.1 Policy

Migration proceeds by making the **construction runtime contract authoritative first**, then adapting modules behind it.

## 16.2 Required migration rule

No new runtime feature should bypass:

* construction planning,
* slot mapping,
* lexical resolution,
* realizer dispatch,
* canonical `SurfaceResult` emission.

## 16.3 Compatibility

Legacy payloads may continue to be accepted at the API boundary.

Compatibility belongs in the **normalization layer**, not in the planner or renderer layers.

## 16.4 Direct-runtime sunset rule

Temporary compatibility fallbacks may exist during migration, but they must:

* be explicit,
* preserve `construction_id` where applicable,
* preserve semantic role intent,
* expose fallback usage in top-level runtime truth and `debug_info`,
* be removable once construction coverage is complete.

---

## 17. Debugging and observability

## 17.1 Required runtime debug fields

When debug is enabled, the runtime should expose at least:

* `runtime_path`
* `construction_id`
* `renderer_backend`
* `lang_code`
* `fallback_used`
* lexical resolution summary
* backend trace

## 17.2 Backend-specific debug

Backends may expose additional metadata such as:

* GF AST or concrete name,
* family engine rule identifiers,
* morphology trace,
* fallback reasons,
* capability tier,
* resolved GF language.

## 17.3 Principle

Debug output should make runtime authority visible:

* which construction was chosen,
* which backend realized it,
* whether fallback occurred,
* whether lexical fallback or compatibility behavior was used,
* whether the runtime path was nominal planner-first.

## 17.4 Parity rule

Where public top-level fields are echoed in debug metadata, debug must not contradict top-level truth.

At minimum this applies to:

* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`

---

## 18. Example flows

## 18.1 Copular classification

Input:

* subject entity
* class or profession predicate

Flow:

* normalize frame
* planner chooses `copula_equative_classification`
* `slot_map` binds `subject` and `predicate_nominal`
* lexical resolver resolves the predicate nominal
* renderer realizes the classification sentence
* runtime emits `SurfaceResult`

## 18.2 Locative sentence

Input:

* subject entity
* location

Flow:

* normalize frame
* planner chooses `copula_locative`
* `slot_map` binds `subject` and `location`
* lexical resolver resolves location labeling and lexical features
* renderer realizes the locative form
* runtime emits `SurfaceResult`

## 18.3 Biography lead

Input:

* subject
* profession
* nationality

Flow:

* normalize frame
* planner chooses the appropriate biography lead construction
* `slot_map` binds subject and identity slots
* lexical resolver resolves profession and nationality
* renderer realizes the sentence according to language and backend capability
* runtime emits `SurfaceResult`

Biography is therefore one construction family inside the runtime flow, not the architecture itself.

---

## 19. Non-goals

This document does **not**:

* define every construction schema,
* define every backend’s internal algorithm,
* require GF to be the only backend,
* require family engines to be removed,
* prescribe one exact `debug_info` shape beyond shared core requirements,
* redesign the semantics model from scratch,
* or redefine the public HTTP contract in place of the runtime contract.

---

## 20. Acceptance criteria

This runtime flow is considered implemented when:

1. generation entrypoints normalize into canonical frame or domain shapes,
2. planner output is authoritative for sentence structure,
3. realization consumes a shared `ConstructionPlan` contract,
4. lexical resolution is reusable across renderers,
5. all renderers accept the same construction-level runtime contract,
6. runtime emits a canonical `SurfaceResult`,
7. debug output identifies runtime path, construction, and backend,
8. direct frame-to-engine generation is compatibility-only,
9. planner-first generation is the nominal path for migrated constructions,
10. public response mapping serializes runtime truth rather than inventing it.

---

## 21. Summary

The authoritative SemantiK Architect runtime flow is:

`HTTP payload -> request normalization -> canonical frame/domain shape -> planner -> ConstructionPlan -> lexical resolution -> realizer -> backend realization -> SurfaceResult -> public response mapping -> API response`

This preserves the final architecture:

* semantics are separate,
* constructions are explicit,
* the planner is authoritative,
* lexical resolution is reusable,
* morphology remains in realization backends,
* renderers are pluggable,
* the public response is a mapped transport layer,
* and no single backend or mapper is allowed to become the hidden architecture.

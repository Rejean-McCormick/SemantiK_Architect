# Multilingual Runtime Target

Status: normative  
Owner: Architecture / Runtime / Grammar  
Scope: final target architecture for multilingual generation in SemantiK Architect  
Immediate implementation scope: EN + FR bio/person cutover  
Architectural scope: scalable multilingual runtime for future expansion to hundreds of languages

---

## 1. Purpose

This document defines the **target architecture** for SemantiK Architect as a multilingual text generation system.

It is not a migration checklist and it is not an acceptance report.  
It is the document that defines what the system **must become**.

This target architecture is designed for:

- a language-neutral shared runtime,
- language-specific realization owned by concrete language modules,
- one planner-first generation path,
- one canonical runtime contract,
- one stable public generation contract,
- and future expansion from EN/FR to a very large multilingual surface area.

The immediate implementation focus is EN and FR, but the architecture defined here is intended for a system that can ultimately scale to **hundreds of languages**.

### 1.1 Role of this document

This document defines:

- the target runtime shape,
- the architectural ownership boundaries,
- the public contract invariants,
- the language-neutrality rules,
- and the readiness model for multilingual scaling.

This document does not define:

- cutover execution order,
- acceptance proof,
- per-file implementation sequencing,
- or temporary migration mechanics except where they affect architectural truth.

### 1.2 Relationship to other documents

This document is the architectural source of truth for multilingual runtime design.

It must be read together with:

- `docs/architecture/EN_FR_FINAL_PARALLEL_LOCKDOWN.md`
- `docs/migration/en_fr_cutover_plan.md`
- `docs/testing/EN_FR_bio_acceptance.md`
- `docs/testing/en_fr_acceptance_and_multilingual_readiness.md`
- `docs/contracts/construction_runtime_contract.md`
- `docs/contracts/public_generation_response_contract.md`

Conflict rule:

- if the issue is **target architecture**, this document wins,
- if the issue is **parallel edit safety and cross-doc precedence**, the lockdown document wins,
- if the issue is **execution order and cutover sequencing**, the cutover plan wins,
- if the issue is **final proof of acceptance**, the acceptance/testing documents win,
- if the issue is **runtime or public object shape**, the contract documents must remain consistent with this architecture.

---

## 2. Architectural statement

SemantiK Architect must become a **planner-first multilingual generation system** in which:

1. a canonical semantic input is normalized into one internal frame/domain shape,
2. a planner produces a construction-oriented runtime payload,
3. lexical resolution binds language-appropriate lexical material,
4. a language-specific realizer produces the final surface output,
5. one stable public API envelope is returned,
6. and language readiness is measured independently from mere routing or compilation.

The architecture must ensure that:

- shared layers are language-neutral,
- concrete language modules own realization,
- runtime contracts are language-agnostic,
- public response semantics remain identical across languages,
- and the nominal planner-first truth exists **before** API serialization.

---

## 3. Design principles

### 3.1 Planner-first is the only target runtime

The nominal generation path must be planner-first.

The target runtime path is:

`canonical input -> planner -> PlannedSentence -> ConstructionPlan -> lexical resolution -> realizer -> SurfaceResult -> public response`

Legacy direct frame-to-engine generation is not part of the final architecture.

Legacy may exist only as an explicitly marked compatibility fallback during cutover windows.  
It must never define nominal architectural truth.

### 3.2 Shared layers must be language-neutral

No shared layer may encode surface realization specific to a natural language.

This applies in particular to:

- shared GF layers,
- runtime bridges,
- shared fallbacks that pretend to be language-correct,
- shared string concatenation that encodes a natural language,
- and API-level shortcuts that bypass language-specific realization.

### 3.3 Concrete languages own realization

A concrete language module is responsible for its own surface realization.

That means:

- English surface belongs to English concrete modules,
- French surface belongs to French concrete modules,
- future languages must follow the same rule.

### 3.4 One canonical runtime contract

The internal multilingual runtime must converge on one canonical cross-boundary model:

`ConstructionPlan -> SurfaceResult`

Planner-local helpers may exist, and specialized construction-local specs may exist, but they must not replace the canonical shared runtime contract.

No construction may introduce a second private runtime contract as the authoritative shared runtime boundary.

### 3.5 One public response contract

All languages and all runtime backends must converge to one public success envelope.

The user-facing response contract must not drift based on:

- language,
- renderer backend,
- migration stage,
- or legacy compatibility path.

The API mapper serializes the public response **after** `SurfaceResult`.  
It must not become the place where nominal planner-first truth first appears.

### 3.6 Language routing is not language correctness

A language is not considered correct merely because:

- it compiles,
- it loads,
- it routes,
- or it returns non-empty text.

A language is correct only when it satisfies its acceptance requirements for both runtime behavior and surface realization.

### 3.7 EN/FR are the first full vertical slice, not the final system

EN and FR are the first implementation cutover, not the complete scope of the system.

The architecture must therefore avoid EN/FR-specific shortcuts that would later block scaling to large numbers of languages.

---

## 4. Normative variables

These variables are normative architectural constants. They may be implemented in code, docs, tests, or config, but they must remain conceptually consistent everywhere.

## 4.1 Runtime variables

- `PRIMARY_RUNTIME = "planner_first"`
- `ALLOW_LEGACY_AS_PRIMARY = false`
- `ALLOW_LEGACY_AS_NOMINAL_SUCCESS = false`
- `ALLOW_LANGUAGE_SPECIFIC_SURFACE_IN_SHARED_RUNTIME = false`
- `ALLOW_LANGUAGE_SPECIFIC_SURFACE_IN_SHARED_GF = false`
- `CANONICAL_RUNTIME_CONTRACT = "ConstructionPlan -> SurfaceResult"`
- `PUBLIC_MAPPING_HAPPENS_AFTER_SURFACE_RESULT = true`

## 4.2 Boundary naming variables

- `CANONICAL_PLANNER_OUTPUT_NAME = "planned_sentence"`
- `CANONICAL_RUNTIME_INPUT_NAME = "construction_plan"`
- `CANONICAL_RUNTIME_OUTPUT_NAME = "surface_result"`
- `CANONICAL_OPTIONS_NAME = "generation_options"`
- `CANONICAL_DEBUG_NAME = "debug_info"`

Avoid as authoritative shared runtime names:

- `sentence`
- `surface_text`
- `metadata`
- `engine_payload`
- `gf_payload`
- `template_payload`
- `render_input`
- `sentence_spec`

## 4.3 GF ownership variables

- `WIKII_IS_LANGUAGE_NEUTRAL = true`
- `WIKIENG_OWNS_EN_SURFACE = true`
- `WIKIFRE_OWNS_FR_SURFACE = true`
- `SHARED_GF_MUST_NOT_ENCODE_ENGLISH_BIO_SURFACE = true`
- `SHARED_GF_MUST_NOT_ENCODE_FRENCH_BIO_SURFACE = true`

## 4.4 Public contract variables

- `PUBLIC_RESPONSE_SHAPE_IS_GLOBAL = true`
- `PUBLIC_TEXT_FIELD = "text"`
- `PUBLIC_LANG_FIELD = "lang_code"`
- `PUBLIC_CONSTRUCTION_FIELD = "construction_id"`
- `PUBLIC_RENDERER_FIELD = "renderer_backend"`
- `PUBLIC_FALLBACK_FIELD = "fallback_used"`
- `PUBLIC_TOKENS_FIELD = "tokens"`
- `PUBLIC_DEBUG_FIELD = "debug_info"`
- `PUBLIC_TIME_FIELD = "generation_time_ms"`

## 4.5 Language scaling variables

- `LANGUAGE_ROUTE_DOES_NOT_IMPLY_LANGUAGE_READINESS = true`
- `LANGUAGE_READINESS_MODEL_REQUIRED = true`
- `NEW_LANGUAGE_MUST_PASS_READINESS_GATES = true`

---

## 5. Core runtime model

## 5.1 Canonical runtime shape

The internal target runtime model is:

`ConstructionPlan -> SurfaceResult`

This means:

- the planner must produce a construction-oriented representation,
- the realizer must consume that representation,
- the realizer must produce a surface-oriented result,
- runtime semantics must not depend on legacy direct frame rendering,
- and API mapping happens only after `SurfaceResult`.

### 5.1.1 Object-boundary rule

The runtime must keep these boundaries distinct:

- planner emits `PlannedSentence`,
- planner-to-renderer handoff is `ConstructionPlan`,
- renderers return `SurfaceResult`,
- public serialization happens after `SurfaceResult`.

If `PlannedSentence`, `ConstructionPlan`, and `SurfaceResult` are used inconsistently, the runtime is architecturally misaligned.

## 5.2 Planner responsibilities

The planner is responsible for:

- selecting the construction,
- structuring the generation problem,
- producing a runtime payload that is language-agnostic at the architecture level,
- exposing enough metadata for downstream observability,
- and preserving semantic identity across backends.

The planner is not responsible for:

- directly emitting final natural-language surface strings,
- hiding backend-specific surface packaging logic,
- or bypassing the canonical runtime boundary.

## 5.3 Lexical resolver responsibilities

The lexical resolver is responsible for:

- resolving lexical bindings for the target language,
- mapping semantic slots to lexical material,
- preserving semantic identity while selecting language-specific lexical forms,
- exposing structured lexical metadata when needed,
- and keeping lexical fallback behavior explicit and observable.

The lexical resolver is not responsible for becoming a hidden surface realizer.

## 5.4 Realizer responsibilities

The realizer is responsible for:

- consuming the planner output and lexical bindings,
- invoking the correct concrete language realization,
- producing final surface text,
- returning canonical runtime metadata,
- and producing a valid `SurfaceResult`.

The realizer is the authority for final surface text.

### 5.4.1 Backend rule

A renderer backend may differ in implementation, but it must not silently replace planner-selected construction semantics.

GF is one backend.  
Family renderers are one backend family.  
Neither becomes the architectural owner of shared construction semantics.

---

## 6. GF architecture target

## 6.1 Shared GF layer contract

The shared GF layer must contain only what is truly shareable across languages.

It may contain:

- shared categories,
- shared constructors,
- language-neutral helper structures,
- abstraction-level semantics.

It must not contain:

- English bio clauses,
- French bio clauses,
- hidden default surface strings,
- language-specific sentence templates,
- shared string concatenation that encodes a natural language.

## 6.2 Concrete language module contract

A concrete language module must own:

- language-specific realization of required constructions,
- required linguistic ordering,
- language-specific copula behavior,
- language-specific morphosyntactic decisions,
- and any language-specific lexical surface adjustments that belong in realization.

## 6.3 EN/FR immediate implication

For EN and FR, this means:

- `WikiI` must be neutral,
- `WikiEng` must explicitly define English bio/event realization,
- `WikiFre` must explicitly define French bio/event realization.

## 6.4 Scalability implication

For future languages, the same rule holds:

a language enters the system through a concrete module that owns its realization, not by inheriting hidden English-like behavior from a shared layer.

---

## 7. Public generation contract target

## 7.1 Canonical success envelope

All successful generation requests must serialize to one stable public JSON envelope:

```json
{
  "text": "Alan Turing is a British mathematician.",
  "lang_code": "en",
  "construction_id": "copula_equative_classification",
  "renderer_backend": "family",
  "fallback_used": false,
  "tokens": ["Alan", "Turing", "is", "a", "British", "mathematician."],
  "debug_info": {
    "runtime_path": "planner_first",
    "construction_id": "copula_equative_classification",
    "renderer_backend": "family",
    "fallback_used": false,
    "lang_code": "en"
  },
  "generation_time_ms": 12.5
}
````

## 7.2 Contract rules

The public contract must satisfy the following:

* `text` is authoritative,
* `lang_code` identifies the returned surface language,
* `construction_id` is explicit on the nominal path,
* `renderer_backend` is explicit on the nominal path,
* `fallback_used` is explicit,
* `tokens` correspond to final text,
* `generation_time_ms` is top-level and authoritative,
* `debug_info` must not contradict top-level fields,
* and nominal planner-first success must not depend on reconstructing top-level truth from `debug_info`.

## 7.3 Public contract is language-independent

The same response shape must apply to:

* English,
* French,
* and all future languages.

Public API clients must not have to branch by language to interpret success responses.

---

## 8. Shared vs concrete ownership

This section defines what each layer may own.

## 8.1 Shared runtime owns

* canonical runtime orchestration,
* planner-first flow,
* lexical resolution interfaces,
* realizer interfaces,
* final response shaping,
* language readiness evaluation model,
* observability semantics,
* public contract invariants.

## 8.2 Shared GF owns

* abstract categories,
* abstract constructors,
* language-neutral helper definitions.

## 8.3 Concrete language GF owns

* surface realization,
* ordering,
* language-specific syntax,
* language-specific morphology where exposed through the current realization layer,
* language-specific handling of required constructions.

## 8.4 Planner owns

* construction choice,
* sentence packaging at the planner level,
* construction planning metadata,
* canonical plan semantics.

## 8.5 Realizer owns

* realization of the provided contract,
* backend dispatch execution,
* final surface production,
* and canonical `SurfaceResult` output.

## 8.6 API mapper owns

* canonical public response serialization,
* top-level field consistency,
* debug/top-level field parity,
* language-code normalization at the public boundary.

The API mapper does **not** own nominal planner-first truth creation.

## 8.7 Evaluator owns

* readiness validation,
* surface-language checks,
* contract checks,
* gold example checks,
* multilingual acceptance reporting.

---

## 9. Language capability model

A multilingual system of this scale requires a capability model that distinguishes mere presence from readiness.

A language may exist in one of several capability states.

### Tier 0 — declared

The language has an identifier or intended slot in the system.

### Tier 1 — compile-capable

The language concrete module compiles.

### Tier 2 — runtime-loadable

The runtime can load the language.

### Tier 3 — routable

The public API can route requests to the language.

### Tier 4 — generates

The language returns non-empty surface output for required constructions.

### Tier 5 — construction-correct

Required constructions behave correctly for the language.

### Tier 6 — acceptance-ready

The language passes acceptance tests and evaluator gates for the target scope.

### Tier 7 — release-ready

The language meets the system’s full readiness bar for its intended deployment context.

For the immediate update:

* EN and FR must reach at least acceptance-ready for bio/person generation.

For future scaling:

* every new language must be classified by tier,
* and no language should be advertised beyond the tier it has actually earned.

---

## 10. Language onboarding contract

A new language is not considered integrated simply because a concrete GF file exists.

A language enters the system only when all required gates for its current tier are satisfied.

Minimum onboarding gates for a new language include:

1. concrete GF exists,
2. language compiles,
3. runtime loads it,
4. canonical bio/person generation routes to it,
5. public contract is valid,
6. evaluator runs against it,
7. readiness metadata is updated.

This rule prevents the system from confusing “present” with “working”.

---

## 11. Language-neutral core rule

This is the single most important structural rule in the entire architecture:

> The shared core must never contain surface strings that belong to a specific natural language.

Corollaries:

* the shared GF layer must not hide English realization,
* runtime bridges must not fake language-correct output in a language-agnostic layer,
* evaluators must not count routed-but-wrong-language output as success,
* concrete language modules must own the final surface behavior.

This rule exists to prevent the exact class of failure where French resolves correctly but surfaces English.

---

## 12. EN/FR immediate target

Although the architecture is multilingual, the immediate implementation target is EN/FR bio/person generation.

### EN immediate target

* resolves to `WikiEng`
* planner-first nominal path
* valid public response contract
* English surface output
* acceptance tests passing

### FR immediate target

* resolves to `WikiFre`
* planner-first nominal path
* valid public response contract
* French surface output
* acceptance tests passing

EN and FR are the first languages that must prove the architecture is coherent end to end.

---

## 13. Out of scope for this document

This document does not define:

* step-by-step migration order,
* file-by-file implementation sequence,
* rollback behavior,
* one-off tooling workarounds,
* per-language detailed test corpora,
* or the final proof of EN/FR acceptance.

Those belong in execution, contract, and acceptance documents.

---

## 14. What this architecture forbids

The target architecture explicitly forbids the following long-term states:

* legacy direct generation as nominal runtime,
* shared GF layers with hidden English surface strings,
* top-level public fields missing while the same information exists only in debug metadata on the nominal path,
* language routing treated as proof of language correctness,
* language readiness inferred from compile success alone,
* backend-specific private runtime contracts replacing the canonical contract,
* API serialization creating nominal runtime truth that should already exist in `SurfaceResult`,
* EN/FR-specific hacks that would block future multilingual scaling.

---

## 15. What success looks like

This architecture is considered realized when the following are all true:

1. the live generation path is planner-first,
2. shared GF layers are language-neutral,
3. EN owns English realization,
4. FR owns French realization,
5. the public success contract is stable and explicit,
6. nominal planner-first truth exists before API serialization,
7. readiness is measured independently from routing,
8. EN/FR pass acceptance as the first vertical slice,
9. the same design can be extended to many more languages without changing the core model.

---

## 16. Final rule

There must be exactly one architectural truth across:

* shared grammar,
* concrete language modules,
* runtime orchestration,
* runtime contracts,
* public response serialization,
* and language readiness evaluation.

If a language can still appear “successful” while inheriting another language’s surface behavior from a shared layer, the architecture is broken.

If the API mapper still has to invent nominal planner-first truth that should already have existed in `SurfaceResult`, the architecture is broken.


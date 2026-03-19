# Construction Runtime Test Plan

Status: normative  
Owner: QA / Runtime / Architecture / API  
Scope: complete test strategy for the aligned planner-first construction runtime in SemantiK Architect  
Immediate implementation scope: EN + FR bio/person cutover, plus generic runtime-contract coverage  
Architectural scope: reusable test strategy for multilingual construction runtime expansion

---

## 1. Purpose

This document defines the authoritative test strategy for the aligned construction runtime in SemantiK Architect.

It exists to verify that runtime generation is consistently implemented through the documented architecture:

```text
HTTP payload
  -> frame normalization
  -> frame-to-construction bridge
  -> planner
  -> PlannedSentence
  -> construction-plan builder
  -> ConstructionPlan
  -> lexical resolution
  -> renderer dispatch
  -> renderer backend
  -> SurfaceResult
  -> public response mapping
````

This test plan exists to prevent drift between:

* public API behavior,
* frame normalization,
* frame-to-construction mapping,
* planner behavior,
* construction-plan building,
* lexical resolution,
* renderer backend behavior,
* grammar/runtime realization,
* runtime metadata,
* and final public response serialization.

This document is not a replacement for the architecture, runtime-contract, public-contract, or EN/FR acceptance documents.
It defines how the repository must test those truths.

---

## 2. Role of this document

This document defines:

* the runtime test layers,
* the canonical objects and names that tests must use,
* the minimum coverage required by runtime stage,
* the assertions policy for semantic vs surface correctness,
* the required regression and fallback tests,
* and the gates that must pass before a migrated construction/runtime path is considered complete.

This document does not define:

* the target architecture itself,
* the public HTTP contract itself,
* the final EN/FR release decision by itself,
* or per-language gold corpora beyond the coverage needed for runtime validation.

---

## 3. Relationship to other documents

This test plan must be read together with:

* `docs/architecture/multilingual_runtime_target.md`
* `docs/architecture/EN_FR_FINAL_PARALLEL_LOCKDOWN.md`
* `docs/contracts/construction_runtime_contract.md`
* `docs/contracts/public_generation_response_contract.md`
* `docs/contracts/public_vs_runtime_vs_frontend_boundaries.md`
* `docs/testing/EN_FR_bio_acceptance.md`

Conflict rule:

* if the issue is target architecture, `multilingual_runtime_target.md` wins,
* if the issue is parallel-edit precedence or final-cutover interpretation, `EN_FR_FINAL_PARALLEL_LOCKDOWN.md` wins,
* if the issue is the internal runtime object boundary, `construction_runtime_contract.md` wins,
* if the issue is the public HTTP success envelope, `public_generation_response_contract.md` wins,
* if the issue is runtime/public/frontend boundary ownership, `public_vs_runtime_vs_frontend_boundaries.md` wins,
* if the issue is EN/FR final pass/fail acceptance, `EN_FR_bio_acceptance.md` wins,
* and this document defines how those truths must be tested.

---

## 4. Authoritative runtime flow under test

The authoritative runtime path under test is:

```text
HTTP payload
  -> frame normalization
  -> frame-to-construction bridge
  -> planner
  -> PlannedSentence
  -> construction-plan builder
  -> ConstructionPlan
  -> lexical resolution
  -> renderer dispatch
  -> renderer backend
  -> SurfaceResult
  -> public response mapping
```

The authoritative shared runtime contract is:

`ConstructionPlan -> SurfaceResult`

The authoritative object-boundary rule is:

* planner emits `PlannedSentence`,
* planner-to-renderer handoff is `ConstructionPlan`,
* renderers return `SurfaceResult`,
* public response mapping happens only after `SurfaceResult`.

Any test plan, test fixture, or helper that collapses these boundaries reintroduces runtime ambiguity and violates the architecture.

---

## 5. Core test objectives

The construction runtime test suite must prove all of the following.

### 5.1 Planner authority

* generation flows through planning and shared runtime contracts,
* planner-selected construction identity remains visible,
* renderers do not invent sentence semantics independently,
* and backends do not silently replace planner-selected construction semantics.

### 5.2 Contract stability

* `PlannedSentence`, `ConstructionPlan`, `SlotMap`, `EntityRef`, `LexemeRef`, and `SurfaceResult` remain structurally valid,
* the canonical runtime boundary remains `ConstructionPlan -> SurfaceResult`,
* and tests detect object-boundary drift early.

### 5.3 Renderer substitutability

* the same planned construction can be consumed by multiple backends where supported,
* backend variation does not become semantic drift,
* and backend choice does not create a second runtime contract.

### 5.4 Lexical resolution correctness

* lexical resolution produces normalized runtime inputs suitable for rendering,
* lexical fallback remains explicit,
* and unresolved lexical data does not silently corrupt construction semantics.

### 5.5 Construction consistency

* each construction enforces its required and optional role rules,
* planner output and construction-plan building remain consistent,
* and construction validation happens before realization.

### 5.6 Public-contract preservation

* public `POST /api/v1/generate/{lang_code}` behavior remains externally coherent,
* public success responses remain stable and explicit,
* and public mapping does not invent nominal planner-first truth that should already exist in `SurfaceResult`.

### 5.7 Fallback transparency

* capability downgrade or renderer fallback is explicit in runtime metadata,
* fallback is visible in the public response where required,
* and silent compatibility success is not counted as nominal runtime success.

### 5.8 Multilingual scalability

* construction logic remains generic,
* language-specific behavior remains localized to realization and lexical resolution,
* and routed-but-wrong-language output is treated as failure rather than partial success.

---

## 6. Test scope

This plan covers:

* domain planning objects,
* construction contract objects,
* frame normalization,
* frame-to-construction mapping,
* planner output,
* construction-plan building,
* slot mapping,
* lexical resolution,
* renderer selection,
* GF rendering,
* family-engine rendering,
* controlled fallback rendering where active,
* API integration,
* compatibility behavior,
* runtime metadata,
* public response serialization,
* and boundary correctness between runtime, public HTTP, and frontend/client views.

This plan does **not** attempt to fully test every lexical item in every language.
It verifies architecture, contracts, representative multilingual paths, fallback behavior, and public/runtime consistency.

---

## 7. Authoritative test rules

### 7.1 Runtime-authority rule

All runtime generation tests must treat the following as authoritative:

* `planned_sentence`
* `construction_plan`
* `construction_id`
* `slot_map`
* lexicalized `ConstructionPlan`
* `renderer_backend`
* `surface_result`
* structured `debug_info`

Tests must not treat backend-specific strings, AST internals, ad hoc engine payloads, or UI convenience objects as the primary source of semantic truth.

### 7.2 Boundary rule

Tests must respect the documented separation between:

* internal runtime objects,
* public HTTP response objects,
* and frontend/client convenience objects.

`SurfaceResult` is an internal runtime object.
It is not the public HTTP success envelope.
Frontend convenience fields such as `lang` or `sentences` are not canonical HTTP success fields.

### 7.3 Planner-first rule

A migrated runtime path is not considered correct merely because it returns text.
Tests must prove that planner-first generation actually occurred and remained visible in metadata and object flow.

### 7.4 No silent truth-reconstruction rule

Tests must fail when nominal planner-first success depends on reconstructing required top-level public truth from `debug_info` after the fact.

---

## 8. Canonical test object names

These names are canonical across tests:

* `raw_payload`
* `normalized_frame`
* `planned_sentence`
* `construction_plan`
* `slot_map`
* `resolved_construction_plan`
* `lang_code`
* `generation_options`
* `renderer_backend`
* `surface_result`
* `debug_info`

Use these names consistently across unit, integration, and API tests.

Avoid as authoritative shared-runtime names:

* `sentence`
* `surface_text`
* `metadata`
* `engine_payload`
* `gf_payload`
* `template_payload`
* `render_input`
* `sentence_spec`

Specialized helper names may exist inside construction-local tests, but they must not replace the canonical names above at the shared test boundary.

---

## 9. Test layers

## 9.1 Unit tests

### Goal

Verify the behavior of isolated runtime components.

### Targets

* planning objects,
* construction contract validation,
* frame normalization helpers,
* frame-to-construction mapping,
* construction-plan builders,
* slot mapping,
* lexical resolution,
* renderer adapters,
* runtime metadata builders,
* fallback policy helpers,
* and public response serialization helpers.

### Success condition

Each unit can be tested without requiring full API startup or end-to-end execution.

---

## 9.2 Integration tests

### Goal

Verify end-to-end cooperation between runtime layers inside Python.

### Targets

* normalized frame -> frame-to-construction bridge -> planner -> construction-plan builder -> lexical resolution -> renderer,
* shared `ConstructionPlan` consumed by multiple renderers,
* renderer backend selection,
* compatibility shim behavior during migration where still allowed,
* and `SurfaceResult` production before API mapping.

### Success condition

The full internal runtime path works without requiring browser or UI tools.

---

## 9.3 HTTP API tests

### Goal

Verify that public generation endpoints preserve stable behavior while using the planner-first runtime internally.

### Targets

* `POST /api/v1/generate/{lang_code}`,
* payload normalization,
* compatibility handling for tolerated legacy request shapes,
* response shape stability,
* metadata parity,
* and error status behavior.

### Success condition

External clients can continue using the API while the internals remain planner-first and contract-correct.

---

## 9.4 Regression tests

### Goal

Prevent old architectural drift from reappearing.

### Targets

* direct frame-to-renderer shortcuts,
* construction modules bypassing contract validation,
* renderer-specific reinterpretation of slot semantics,
* loss of `construction_id`,
* inconsistent `debug_info`,
* backend-private response payloads bypassing `SurfaceResult`,
* public mapping creating missing nominal truth,
* and frontend convenience fields leaking into the HTTP envelope.

### Success condition

Any regression toward multiple generation centers of truth is detected early.

---

## 9.5 Capability / fallback tests

### Goal

Verify support differences across renderers and languages are handled explicitly.

### Targets

* GF supported path,
* family-engine supported path,
* controlled fallback backend path where active,
* unsupported construction path,
* unsupported language path,
* and downgrade behavior.

### Success condition

The system fails or downgrades predictably, with structured runtime and public metadata.

---

## 10. Test matrix

## A. Frame normalization

### Objective

Verify that external payload variants normalize into stable internal frame/domain objects.

### Cases

* canonical payload,
* tolerated legacy payload,
* nested payload,
* top-level flat payload where compatibility is intentionally supported,
* payload with extra irrelevant fields,
* payload missing required frame-family fields,
* payload with conflicting language fields,
* malformed payload,
* wrong field types.

### Assertions

* normalized frame type is correct,
* required internal fields are present,
* normalization is deterministic,
* URL `lang_code` precedence is respected where documented,
* no renderer-specific fields appear at this layer,
* invalid input fails with correct error semantics.

---

## B. Frame-to-construction mapping

### Objective

Verify that normalized frames are routed to the correct construction family.

### Cases

* equative/classification frame,
* attributive frame,
* locative frame,
* existential frame,
* possession frame,
* topic-comment frame,
* eventive frame,
* relative-clause frame,
* ambiguous frame with deterministic rule,
* unsupported frame family.

### Assertions

* correct `construction_id`,
* correct planner input shape,
* unsupported frames fail explicitly,
* no backend-specific routing logic leaks into this layer.

---

## C. Planning

### Objective

Verify planner output is semantically correct and backend-neutral.

### Cases

* single-clause construction,
* topic/focus-sensitive construction,
* discourse-aware planning,
* planner with minimal roles,
* planner with all optional roles present,
* planner receiving unsupported role combinations.

### Assertions

* `construction_id` present,
* planner output is a valid `PlannedSentence`,
* `topic_entity_id` behavior correct where applicable,
* `focus_role` behavior correct where applicable,
* planner output does not embed GF-only structures,
* planner output does not embed family-template-only structures,
* planner output does not bypass the canonical runtime boundary.

---

## D. Construction-plan building

### Objective

Verify planner output is converted into the canonical renderer-facing runtime contract.

### Cases

* complete `PlannedSentence`,
* missing optional role,
* missing required role,
* repeated role where multiplicity is allowed,
* repeated role where multiplicity is forbidden,
* incompatible role type,
* entity vs predicate confusion,
* metadata propagation,
* surface hint presence/absence where supported.

### Assertions

* `ConstructionPlan` shape valid,
* `slot_map` present,
* required roles enforced,
* slot types validated,
* slot names canonical,
* multiplicity rules enforced,
* no silent coercion that changes semantics,
* no planner-local structure escapes as the renderer contract.

---

## E. Slot mapping

### Objective

Verify semantic roles are converted into stable runtime slots.

### Cases

* complete role set,
* missing optional role,
* missing required role,
* repeated role where multiplicity is allowed,
* repeated role where multiplicity is forbidden,
* incompatible role type,
* entity vs predicate confusion.

### Assertions

* required slots enforced,
* slot payload types validated,
* slot names canonical,
* no backend-private fields leak into the shared contract.

---

## F. Lexical resolution

### Objective

Verify semantic slot values are converted into lexicalized runtime values.

### Cases

* entity with explicit label,
* entity with QID and no label,
* profession/predicate with lemma,
* predicate with QID-backed lookup,
* nationality/adjectival lookup,
* unresolved lexical item with explicit fallback,
* missing lexical entry,
* language-specific lexical override,
* language-independent deterministic fallback.

### Assertions

* `EntityRef` shape valid,
* `LexemeRef` shape valid,
* fallback is explicit,
* lexical resolution is deterministic,
* missing lexical data does not silently corrupt construction semantics,
* output remains a valid shared `ConstructionPlan`.

---

## G. Renderer selection

### Objective

Verify the system selects the correct renderer backend.

### Cases

* GF available and supports construction,
* family renderer selected by capability,
* controlled fallback backend selected where allowed,
* forced backend override,
* unsupported backend,
* unsupported language in selected backend,
* backend downgrade path.

### Assertions

* chosen backend matches capability rules,
* backend fallback is explicit,
* `ConstructionPlan` is unchanged in semantic content by selection,
* debug info records selected backend,
* selection does not create a second semantic center of truth.

---

## H. GF renderer tests

### Objective

Verify GF consumes the generic construction runtime contract instead of owning sentence semantics directly.

### Cases

* valid `ConstructionPlan` to GF realization path,
* supported construction and language,
* missing slot rejected before GF realization,
* lexicalized plan with entity and predicate refs,
* unsupported construction for GF backend,
* unsupported language in GF backend,
* malformed realization failure.

### Assertions

* GF adapter consumes `construction_plan`,
* no direct raw frame-to-GF shortcut is used,
* failure path is structured,
* output metadata includes backend and construction info,
* GF does not become the hidden owner of shared construction semantics.

---

## I. Family renderer tests

### Objective

Verify family renderers consume the same contract as GF.

### Cases

* same `ConstructionPlan` realized by family renderer,
* family-specific word-order handling,
* morphology-dependent output,
* lexical fallback behavior,
* unsupported construction in a family engine,
* unsupported feature combination.

### Assertions

* family renderer uses shared contract,
* family renderer does not reinterpret slot semantics,
* family renderer may vary surface form while preserving semantic intent,
* failure is explicit and structured.

---

## J. Controlled fallback renderer tests

### Objective

Verify controlled fallback remains an explicit, observable compatibility path.

### Cases

* supported construction in fallback backend where active,
* fallback from unsupported GF path,
* fallback from unsupported family path,
* unresolved lexical item handled through explicit fallback,
* minimal slot plan.

### Assertions

* fallback output is well-formed where fallback is allowed,
* fallback is marked explicitly in metadata,
* fallback does not become an untracked silent success path,
* fallback cannot count as nominal planner-first acceptance success where acceptance docs disallow it.

---

## K. SurfaceResult tests

### Objective

Verify final internal runtime result shape is stable and complete.

### Cases

* successful generation,
* partial-fallback generation,
* failed generation,
* unsupported language,
* unsupported construction,
* lexical failure,
* renderer failure.

### Assertions

* `text` present on success,
* `lang_code` present,
* `construction_id` present,
* `renderer_backend` present,
* `fallback_used` present,
* `debug_info` present,
* `generation_time_ms` present where required by the canonical runtime model and public contract promotion path,
* error shape consistent on failure,
* no silent empty-string success unless explicitly permitted.

---

## L. Public response mapping tests

### Objective

Verify the public HTTP success envelope is produced from `SurfaceResult` without contract drift.

### Cases

* complete nominal planner-first runtime result,
* runtime result with fallback metadata,
* runtime result missing required public fields,
* runtime result with top-level/debug mismatch,
* runtime result with tokens absent,
* runtime result with generated timing,
* unsupported runtime result shape.

### Assertions

* public response contains `text`,
* public response contains `lang_code`,
* public response contains `construction_id` on the nominal path,
* public response contains `renderer_backend` on the nominal path,
* public response contains `fallback_used`,
* public response contains `tokens`,
* public response contains `debug_info`,
* public response contains `generation_time_ms`,
* top-level/debug parity is enforced where documented,
* public mapping happens after `SurfaceResult`,
* and nominal success does not depend on inventing missing planner-first truth inside the mapper.

---

## M. API compatibility tests

### Objective

Verify the public API remains stable while internals remain planner-first.

### Cases

* canonical current payload,
* tolerated legacy payload,
* language in URL only,
* language in payload where allowed,
* language mismatch,
* missing `frame_type`,
* missing required semantic fields,
* unknown construction/frame family,
* malformed JSON.

### Assertions

* response status codes correct,
* response model shape stable,
* compatibility normalization works where intended,
* invalid requests fail with correct status and detail shape,
* public response originates from `SurfaceResult`,
* compatibility handling is limited to normalization rather than hidden alternate runtime truth.

---

## N. Debug / provenance tests

### Objective

Verify runtime metadata is structured, useful, and aligned with documented fields.

### Required metadata

* `construction_id`
* `renderer_backend`
* `lang_code`
* `runtime_path`
* `fallback_used`
* language resolution / resolved-language markers where applicable
* lexical fallback markers where relevant
* backend downgrade markers where relevant
* planner/build metadata where relevant
* AST or renderer trace only where applicable

### Assertions

* metadata shape is structured,
* fields are stable across backends where documented,
* nominal planner-first tests require `runtime_path = "planner_first"` where applicable,
* missing required metadata is treated as failure for runtime-contract tests,
* metadata must not contradict top-level public fields where the public contract promotes those fields.

---

## O. Boundary separation tests

### Objective

Verify the repository does not collapse internal runtime results, public HTTP results, and frontend/client convenience objects into one undifferentiated contract.

### Cases

* internal `SurfaceResult`,
* public HTTP success envelope,
* frontend/client convenience `GenerationResult`,
* examples or helper functions carrying both `lang` and `lang_code`,
* tests that serialize runtime objects directly.

### Assertions

* no doc or test treats `SurfaceResult` as the public HTTP success object,
* no test treats frontend convenience fields as canonical HTTP fields,
* HTTP tests use `lang_code`,
* frontend/client tests may use `lang` only in the frontend/client boundary,
* examples respect the documented separation of concerns.

---

## 11. Minimum construction coverage

The following construction families must be represented in automated tests:

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

Each construction does not need identical coverage depth initially, but each must have at least:

* contract validation coverage,
* planner mapping coverage,
* one positive realization path,
* one negative/failure path.

---

## 12. Language coverage strategy

## 12.1 Target language sets

### Tier A — mandatory migration languages

These are the first languages used to validate the aligned runtime end to end.

* English
* French

### Tier B — representative family languages

Add at least one representative language for each active family backend as migration proceeds.

### Tier C — fallback coverage languages

Include languages expected to use partial support or explicit fallback to verify downgrade behavior.

## 12.2 EN/FR-specific rule

For the immediate cutover, EN and FR must receive the strongest end-to-end coverage because they are the first full vertical slice of:

* planner-first orchestration,
* lexical resolution,
* language-specific realization,
* public contract correctness,
* and acceptance gating.

FR routed-correctly but surfaced-in-English must be treated as a hard failure, not a partial pass.

---

## 13. Cross-backend equivalence testing

### Objective

Ensure backend variation does not become semantic drift.

### Rule

Where the same construction is supported by multiple backends, tests must verify:

* same `construction_id`,
* same slot semantics,
* same essential proposition,
* allowed surface variation only.

### Allowed differences

* article choice,
* word order,
* morphology,
* idiomatic phrasing,
* punctuation where language-specific.

### Forbidden differences

* changed predicate meaning,
* changed argument structure,
* dropped required roles without explicit fallback marker,
* silent reinterpretation of semantic roles.

---

## 14. Failure testing

The runtime must be tested for predictable failure behavior.

## 14.1 Failure classes

* invalid payload,
* unsupported frame family,
* unsupported construction,
* invalid `PlannedSentence`,
* invalid `ConstructionPlan`,
* missing required role,
* lexical resolution failure,
* renderer selection failure,
* renderer realization failure,
* unsupported language,
* backend capability mismatch,
* malformed or contradictory debug metadata,
* public-contract parity failure.

## 14.2 Failure requirements

Every failure test must verify:

* correct exception or error response type,
* stable error shape,
* no silent success,
* no hidden backend substitution unless explicitly allowed and recorded,
* no incorrect promotion of fallback success to nominal planner-first success.

---

## 15. Performance / stability sanity tests

These are not benchmark-heavy tests, but guardrails.

### Required sanity checks

* repeated generation with same plan is deterministic where expected,
* repeated generation does not mutate shared slot state,
* `PlannedSentence` is immutable or treated as immutable by later stages,
* `ConstructionPlan` is immutable or treated as immutable by renderers,
* lexical resolution does not leak cross-test cache state incorrectly,
* backend selection does not depend on incidental ordering.

---

## 16. Required test files

## 16.1 Unit

* `tests/unit/planning/test_construction_plan.py`
* `tests/unit/planning/test_frame_to_plan.py`
* `tests/unit/planning/test_frame_to_slots.py`
* `tests/unit/lexicon/test_lexical_resolution.py`
* `tests/unit/renderers/test_family_construction_adapter.py`
* `tests/unit/renderers/test_gf_construction_adapter.py`
* `tests/unit/use_cases/test_plan_text.py`
* `tests/unit/use_cases/test_realize_text.py`

## 16.2 Integration

* `tests/integration/test_generate_via_planner_en.py`
* `tests/integration/test_generate_via_planner_fr.py`

## 16.3 HTTP API / regression

* `tests/http_api/test_generate.py`
* `tests/http_api/test_generations.py`
* `tests/test_multilingual_generation.py`
* `tests/test_gf_dynamic.py`
* `tests/core/test_use_cases.py`
* `tests/core/test_domain_models.py`

These files together must cover:

* runtime object integrity,
* planner-first observability,
* metadata presence,
* fallback transparency,
* EN/FR public-contract correctness,
* and regression protection against multiple truths.

---

## 17. Acceptance gates

A construction-runtime migration is not complete until all of the following pass.

## Gate 1 — Contract gate

* shared contract objects exist,
* planner emits `PlannedSentence`,
* construction-plan building emits `ConstructionPlan`,
* renderers consume `ConstructionPlan`,
* renderers return `SurfaceResult`,
* tests verify the contract end to end.

## Gate 2 — Backend gate

At least one migrated construction is realizable through each active backend category that remains part of the supported runtime surface:

* GF backend,
* family backend,
* controlled fallback backend where applicable.

## Gate 3 — Public-contract gate

* nominal planner-first generation returns the documented public success envelope,
* required top-level fields are explicit,
* and top-level/debug parity is valid where documented.

## Gate 4 — Compatibility gate

* `/generate` remains externally usable,
* tolerated legacy-compatible payloads still behave as intended,
* and compatibility handling remains limited to normalization and explicit fallback behavior.

## Gate 5 — Metadata gate

* `debug_info` is present and structured,
* backend and construction identity are visible,
* planner-first path is observable where required,
* and fallback state is explicit.

## Gate 6 — Regression gate

* direct frame-to-renderer generation is no longer the primary runtime path for migrated coverage,
* planner-first generation is observable in tests,
* and tests fail when multiple centers of truth reappear.

## Gate 7 — EN/FR acceptance gate

For the immediate cutover, EN and FR must additionally satisfy the release-blocking EN/FR bio acceptance document, including the hard FR failure rule for routed-but-English output.

---

## 18. Test data guidelines

### 18.1 Use stable semantic examples

Prefer examples that are:

* simple,
* unambiguous,
* reproducible,
* easy to compare across languages.

### 18.2 Avoid test data that depends on

* incidental lexical richness,
* unstable external services,
* live external APIs,
* random generation,
* hidden mutable state.

### 18.3 Prefer semantic fixtures over raw strings

Where possible, tests should build canonical semantic inputs and compare normalized runtime behavior instead of only comparing final strings.

---

## 19. Assertions policy

### 19.1 Strong assertions

Use strong assertions for:

* `construction_id`,
* slot presence,
* backend selection,
* metadata shape,
* error types,
* fallback markers,
* public top-level fields on the nominal path.

### 19.2 Flexible assertions

Use flexible assertions for:

* allowed surface variation,
* morphology differences across backends,
* punctuation differences where not semantically important.

### 19.3 Avoid brittle assertions

Do not overfit tests to:

* incidental field ordering,
* exact debug formatting beyond documented fields,
* backend-internal AST details unless the test is explicitly about AST production.

---

## 20. Migration testing policy

During migration, every moved construction must receive tests in this order:

1. frame-to-construction mapping validation,
2. planner validation,
3. construction-plan validation,
4. lexical resolution validation,
5. one renderer success path,
6. one failure path,
7. public response-mapping coverage where publicly exposed,
8. API regression coverage where publicly exposed.

No construction should be considered migrated based only on manual browser testing.

---

## 21. Exit criteria

The construction runtime alignment is considered fully implemented when:

* all migrated generation paths pass through planner + shared construction runtime contract,
* all active renderers consume the same `ConstructionPlan` boundary,
* all active renderers return `SurfaceResult`,
* direct frame-to-renderer generation is compatibility-only where it still exists,
* required construction families have automated coverage,
* multilingual fallback behavior is explicit and tested,
* public API behavior remains stable,
* runtime/public/frontend boundaries remain documented and respected,
* debug/provenance metadata is structured and stable.

---

## 22. Final rule

A runtime generation feature is not complete until its tests prove:

* what construction is being realized,
* what roles or slots are being realized,
* how lexical resolution was resolved,
* which backend produced the result,
* whether fallback occurred,
* whether planner-first orchestration actually happened,
* and whether the final public response remained contract-correct.

If those facts are not testable, the runtime is not sufficiently aligned.

If a test can pass while the system still hides a second center of truth in a renderer, mapper, compatibility shim, or shared language layer, the test plan is insufficient.


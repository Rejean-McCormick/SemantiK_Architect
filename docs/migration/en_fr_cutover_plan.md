# EN/FR Cutover Plan

Status: normative execution plan
Owner: Runtime / Grammar / API / QA
Scope: final-complete cutover of EN and FR bio/person generation to the target multilingual runtime model
Immediate implementation scope: EN + FR bio/person only
Architectural intent: first full vertical slice of a system designed to scale to many more languages

---

## 1. Purpose

This document defines the **execution plan** for the EN/FR cutover.

It is not the final architecture document and it is not the final acceptance document.

Its purpose is to answer:

* what changes must be made,
* in what order,
* in which files,
* under which rules,
* what boundaries must remain explicit,
* and what conditions must be met before the cutover is considered complete.

This plan assumes:

* the system is in development,
* partial or substantial progress toward planner-first may already exist in the repository,
* preserving unstable legacy behavior is not a priority,
* and the goal is to replace transitional ambiguity with one final coherent model.

This plan updates the earlier short-form cutover framing.
For the final-complete update, the short cutover list is **not sufficient by itself**.
Execution must include the runtime contract layer, the public-boundary layer, the evaluator/test layer, and the documentation/boundary synchronization layer.

---

## 2. Cutover statement

This cutover exists to replace the current hybrid/legacy EN/FR bio generation path with a clean planner-first vertical slice that is final in structure, not merely transitional in behavior.

At the end of this cutover:

* EN bio/person generation must be planner-first,
* FR bio/person generation must be planner-first,
* `WikiI` must be language-neutral,
* `WikiEng` must own English realization,
* `WikiFre` must own French realization,
* the runtime must follow `ConstructionPlan -> SurfaceResult`,
* the public response contract must be coherent and explicit,
* the API mapper must serialize nominal truth rather than invent it,
* the acceptance/test path must reject language-routing false positives,
* and the docs must no longer tell competing stories about the runtime.

---

## 3. Non-goals

This cutover does not attempt to:

* fix all languages,
* complete all constructions,
* stabilize all tooling/UI behavior unrelated to the EN/FR slice,
* solve every multi-language compile problem in the repository,
* or make the full multilingual system complete now.

The implementation focus remains EN + FR bio/person generation.

However, every change made in this cutover must remain compatible with the future multilingual target.

---

## 4. Cutover rules

## 4.1 No rollback track

This cutover does not define a rollback path.

The objective is to replace broken/transitional behavior with the intended architecture, not preserve unstable legacy behavior indefinitely.

## 4.2 No shared-language surface

No shared layer may keep English or French surface strings after the cutover.

## 4.3 EN and FR move together

Any cleanup that removes shared bio realization from `WikiI` must update both:

* `WikiEng`
* `WikiFre`

in the same cutover sequence.

## 4.4 Planner-first becomes nominal

At the end of the cutover, planner-first must be the nominal generation path for EN/FR bio/person generation.

## 4.5 Legacy is not a success state

Legacy output may still exist during the cutover window, but it must not count as target-state success.

## 4.6 Runtime contract is canonical

The internal runtime contract for migrated generation is:

`ConstructionPlan -> SurfaceResult`

Planner-facing code must not introduce an alternate private runtime contract.

## 4.7 API mapping is downstream only

The public response mapper may serialize, normalize, and preserve explicit compatibility behavior where intentionally allowed.

It must not become the hidden owner of nominal planner-first truth.

## 4.8 Compatibility handling is boundary-limited

Compatibility payload handling belongs at explicit normalization boundaries.

It must not leak into shared runtime semantics.

## 4.9 Docs may not compete with each other

After the cutover:

* architecture docs,
* contract docs,
* acceptance docs,
* status docs,
* and overview/API docs

must describe one compatible reality.

No document may preserve a pre-cutover hybrid story as if it were still the intended design.

---

## 5. Current-state problem summary

The cutover addresses the following known problems:

1. `WikiFre` historically resolves correctly but may still surface English because of inherited English behavior from `WikiI`.
2. `WikiI` has historically acted as a hidden owner of English bio surface strings.
3. The repository may already contain planner-first progress, but the final nominal path and its boundaries are not yet fully locked as one complete truth.
4. Runtime metadata may still drift between top-level fields and `debug_info`.
5. Public serialization may still tolerate or repair shapes that should already be canonical by the time mapping occurs.
6. QA/evaluation does not always reject “routed correctly, surfaced incorrectly” cases strongly enough.
7. Documentation is still vulnerable to hybrid or duplicated narratives across architecture, contracts, acceptance, status, and overview pages.
8. EN/FR acceptance is not yet strong enough to act as the first multilingual reference slice unless all of the above converge together.

---

## 6. File set in scope

The final-complete cutover directly touches the following files.

### Grammar

* `gf/WikiI.gf`
* `gf/WikiEng.gf`
* `gf/WikiFre.gf`

### Runtime contract and orchestration

* `app/core/domain/models.py`
* `app/core/use_cases/generate_text.py`
* `app/core/use_cases/realize_text.py`
* `app/adapters/engines/construction_realizer.py`
* `app/adapters/engines/family_construction_adapter.py`
* `app/adapters/engines/gf_engine.py`

### API boundary

* `app/adapters/api/contracts/generation_request_mapper.py`
* `app/adapters/api/contracts/generation_response_mapper.py`
* `app/adapters/api/routers/generation.py`

### Tests and QA

* `tests/core/test_use_cases.py`
* `tests/core/test_domain_models.py`
* `tests/integration/test_generate_via_planner_en.py`
* `tests/integration/test_generate_via_planner_fr.py`
* `tests/http_api/test_generate.py`
* `tests/http_api/test_generations.py`
* `tests/test_multilingual_generation.py`
* `tests/test_gf_dynamic.py`
* `tests/unit/use_cases/test_realize_text.py`
* `tests/unit/use_cases/test_plan_text.py`
* `tests/unit/renderers/test_family_construction_adapter.py`
* `tests/unit/renderers/test_gf_construction_adapter.py`
* `tests/unit/planning/test_construction_plan.py`
* `tests/unit/planning/test_frame_to_plan.py`
* `tests/unit/planning/test_frame_to_slots.py`
* `tests/unit/lexicon/test_lexical_resolution.py`
* `tools/qa/eval_bios.py`

### Documentation and boundary synchronization

* `docs/architecture/EN_FR_FINAL_PARALLEL_LOCKDOWN.md`
* `docs/architecture/multilingual_runtime_target.md`
* `docs/migration/en_fr_cutover_plan.md`
* `docs/testing/EN_FR_bio_acceptance.md`
* `docs/testing/en_fr_acceptance_and_multilingual_readiness.md`
* `docs/contracts/public_generation_response_contract.md`
* `docs/contracts/construction_runtime_contract.md`
* `docs/contracts/debug_info_contract.md`
* `docs/contracts/planner_realizer_interfaces.md`
* `docs/contracts/public_vs_runtime_vs_frontend_boundaries.md`
* `docs/2-Technical-Reference/CURRENT_RUNTIME_STATUS.md`
* `docs/testing/construction_runtime_test_plan.md`
* `docs/architecture/construction_runtime_alignment.md`
* `docs/architecture/construction_runtime_flow.md`
* `docs/migration/generate_path_to_planner_runtime.md`
* `docs/1-Overview/API-Overview.md`
* `docs/1-Overview/Inputs-Frames.md`
* `docs/2-Technical-Reference/04-API_REFERENCE.md`
* `docs/status/language_validation_matrix.md`
* `docs/2-Technical-Reference/17-TOOLS_AND_TESTS_INVENTORY.md`
* `docs/1-Overview/_Sidebar.md`
* `docs/1-Overview/Changelog.md`

---

## 7. Execution phases

## Phase 1 — Shared GF cleanup

### Goal

Remove language-specific bio/event surface realization from the shared GF layer.

### Files

* `gf/WikiI.gf`

### Required changes

`WikiI` must stop owning language-specific bio/event surface text.

It may continue to own:

* shared lincats,
* language-neutral helper constructors,
* shared abstraction structure.

It must not continue to own:

* English bio clause templates,
* English event clause templates,
* French bio clause templates,
* French event clause templates,
* any hidden default that causes another language to inherit English-like surface behavior.

### Completion rule

This phase is complete only when `WikiI` no longer contains language-specific bio/event surface strings.

---

## Phase 2 — Concrete EN/FR GF ownership

### Goal

Make English and French concrete modules explicitly own their own bio/event realization.

### Files

* `gf/WikiEng.gf`
* `gf/WikiFre.gf`

### Required changes

`WikiEng` must define English realization for required bio/event functions.

`WikiFre` must define French realization for required bio/event functions.

At minimum, the required functions are:

* `mkBioProf`
* `mkBioNat`
* `mkBioFull`
* `mkEvent`

### EN rule

English must remain explicit and complete after `WikiI` becomes neutral.

### FR rule

French must not emit English literals through inherited behavior.

### Completion rule

This phase is complete only when:

* EN compiles with explicit concrete ownership,
* FR compiles with explicit concrete ownership,
* and neither language depends on shared English bio strings.

---

## Phase 3 — Canonical runtime contract lock

### Goal

Lock the migrated runtime to the canonical contract:

`ConstructionPlan -> SurfaceResult`

### Files

* `app/core/domain/models.py`
* `app/core/use_cases/realize_text.py`
* `app/adapters/engines/construction_realizer.py`
* `app/adapters/engines/family_construction_adapter.py`
* `app/adapters/engines/gf_engine.py`

### Required changes

The runtime must:

* preserve one canonical planner-to-realizer contract,
* return a canonical `SurfaceResult`,
* expose `construction_id`, `renderer_backend`, `fallback_used`, `tokens`, `debug_info`, and `generation_time_ms`,
* keep backend-specific behavior behind the realizer boundary,
* and avoid reintroducing a backend-private or construction-private runtime contract.

### Completion rule

This phase is complete only when migrated EN/FR bio/person realization returns a canonical runtime result regardless of backend path.

---

## Phase 4 — Runtime nominal-path cutover

### Goal

Make planner-first the nominal orchestration path for EN/FR bio/person generation.

### Files

* `app/core/use_cases/generate_text.py`

### Required changes

`GenerateText` must:

* treat planner-first as the nominal runtime,
* stop treating legacy as the default path,
* allow legacy only as explicit compatibility fallback during the cutover window if still present,
* expose runtime-path truth in metadata,
* normalize into the canonical runtime result rather than an ambiguous transport object,
* and fail fast when nominal planner-first metadata is incomplete.

### Required runtime metadata

Planner-first results must expose enough metadata for the public contract:

* `construction_id`
* `renderer_backend`
* `fallback_used = false`
* `runtime_path = "planner_first"`
* `lang_code`
* `tokens`
* `generation_time_ms`

### Completion rule

This phase is complete only when EN/FR bio/person requests run through planner-first as the nominal path and expose the required runtime metadata before API serialization.

---

## Phase 5 — Public-boundary cleanup

### Goal

Make the HTTP boundary explicit, coherent, and final.

### Files

* `app/adapters/api/contracts/generation_request_mapper.py`
* `app/adapters/api/contracts/generation_response_mapper.py`
* `app/adapters/api/routers/generation.py`

### Required changes

The request boundary must remain the compatibility/normalization boundary.

The response boundary must produce one canonical success envelope:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `tokens`
* `debug_info`
* `generation_time_ms`

### Required consistency rules

* `text` is authoritative
* `lang_code` identifies the returned surface
* `fallback_used` must match `debug_info.fallback_used`
* `generation_time_ms` top-level is authoritative
* `construction_id` must not live only in `debug_info` on the nominal path
* `renderer_backend` must not live only in `debug_info` on the nominal path
* compatibility parsing must not become nominal planner-first truth
* the router must expose the final public response semantics consistently

### Completion rule

This phase is complete only when the public success envelope is coherent for EN and FR planner-first bio generation and the mapper is no longer the hidden owner of nominal runtime truth.

---

## Phase 6 — Test and evaluator hardening

### Goal

Make tests fail on the exact failure modes this cutover is meant to eliminate.

### Files

* all scoped test files listed above
* `tools/qa/eval_bios.py`

### Required changes

Tests and evaluator must cover at least:

* planner-first nominal success,
* explicit legacy fallback behavior if still temporarily present,
* fallback-disabled failure behavior,
* required runtime metadata presence,
* canonical `SurfaceResult` behavior,
* top-level/debug parity,
* deterministic repeated planner-first behavior,
* HTTP success-envelope correctness,
* FR routed-but-English hard failure,
* and contract-shaping assumptions needed by the public response path.

### Required anti-regression rules

* a test must fail if planner-first is claimed but required runtime metadata is missing
* a test must fail if the public success envelope drifts by backend or language
* evaluator must fail FR if the request is `fr`, resolution is `WikiFre`, and the output still looks English

### Completion rule

This phase is complete only when runtime path regression, metadata regression, silent fallback regression, public-envelope drift, and routed-but-wrong-language FR output are all detectable.

---

## Phase 7 — Documentation and boundary synchronization

### Goal

Make the docs reflect the real state reached by the cutover and remove competing documentation narratives.

### Files

* all scoped documentation files listed above

### Required changes

#### Architecture and lock docs

* architecture docs must describe planner-first as the target and `ConstructionPlan -> SurfaceResult` as the canonical runtime model
* the lock doc must remain the execution-time source of precedence for parallel work

#### Acceptance docs

* `EN_FR_bio_acceptance.md` must be the operative EN/FR acceptance reference
* `en_fr_acceptance_and_multilingual_readiness.md` must retain the broader multilingual readiness model without competing with the EN/FR operative gate

#### Contract docs

* `public_generation_response_contract.md` must document the final success envelope used by EN/FR after cutover
* runtime/contract/boundary docs must keep runtime, public HTTP, and frontend/client views distinct

#### Status docs

* `CURRENT_RUNTIME_STATUS.md` must describe the real runtime state after cutover, not a pre-cutover hybrid story

#### Overview/API docs

* overview/API docs must not preserve old success-envelope examples or ambiguous runtime narratives

### Completion rule

This phase is complete only when the docs no longer describe removed transitional behavior as if it were the intended state and no document contradicts the final architecture, contracts, or acceptance gates.

---

## 8. Legacy removal gate

Legacy may remain only until the EN/FR cutover satisfies all required conditions.

Legacy direct generation must be removed or permanently demoted only after all of the following are true:

1. EN bio/person generation succeeds through planner-first.
2. FR bio/person generation succeeds through planner-first.
3. EN resolves to `WikiEng`.
4. FR resolves to `WikiFre`.
5. FR output is actually French.
6. The runtime contract is canonical before API mapping.
7. The public response contract is coherent at top level.
8. Core, integration, and HTTP tests are green for the new nominal path.
9. `eval_bios` rejects routed-but-wrong-language FR output.
10. Runtime status and acceptance docs reflect the new truth.
11. No remaining nominal EN/FR path depends on hidden compatibility repair in the response mapper.

Once all of these are true, legacy is no longer justified for EN/FR bio/person generation.

---

## 9. Build and validation sequence

This is the required execution order for the cutover.

### Step 1 — change source files

Apply code/doc changes in the required phases.

### Step 2 — rebuild system index

Refresh the Everything Matrix after source changes.

### Step 3 — compile grammar

Build the PGF after GF changes.

### Step 4 — run runtime/language health

Run the health/audit path needed for EN/FR validation.

### Step 5 — run real generation calls

Run real EN and FR generation requests.

### Step 6 — run tests

Run the scoped core, unit, integration, and HTTP tests relevant to the cutover.

### Step 7 — run evaluator

Run `eval_bios` against EN/FR examples.

### Step 8 — sync docs

Update runtime status, contracts, acceptance docs, and overview/API docs to match the real cutover result.

### Step 9 — remove remaining EN/FR legacy use

Remove or demote any remaining EN/FR legacy primary-path behavior.

### Step 10 — revalidate boundaries

Confirm that runtime, public HTTP, and frontend/client convenience layers are still distinct and aligned.

---

## 10. Risks and failure modes

This cutover intentionally avoids rollback, so the main protection is correctness of execution order and validation.

### Risk 1 — `WikiI` becomes too empty before concrete modules are updated

Effect:

* EN and/or FR become incomplete.

Mitigation:

* update `WikiEng` and `WikiFre` in the same cutover sequence.

### Risk 2 — planner-first is enabled nominally but lacks required metadata

Effect:

* response mapper drift,
* fake planner-first success.

Mitigation:

* fail fast on incomplete planner-first runtime metadata.

### Risk 3 — FR compiles but still surfaces English

Effect:

* false positive language success.

Mitigation:

* evaluator and acceptance docs must explicitly fail that case.

### Risk 4 — public contract cleanup lags behind runtime cleanup

Effect:

* top-level/debug drift remains,
* mapper becomes a hidden repair layer.

Mitigation:

* response-boundary cleanup must be part of the cutover, not deferred.

### Risk 5 — tests validate non-empty output but not language correctness

Effect:

* regression survives.

Mitigation:

* harden both tests and `eval_bios`.

### Risk 6 — runtime/public/frontend boundaries collapse

Effect:

* `SurfaceResult` is mistaken for the public HTTP object,
* frontend convenience fields drift into the HTTP contract,
* or HTTP contract details leak backward into runtime semantics.

Mitigation:

* keep boundary docs, mapper behavior, router behavior, and examples synchronized.

---

## 11. Definition of completion by file group

### Grammar is complete when

* `WikiI` is neutral,
* `WikiEng` owns English bio/event surface,
* `WikiFre` owns French bio/event surface.

### Runtime is complete when

* planner-first is nominal,
* `ConstructionPlan -> SurfaceResult` is canonical,
* legacy is not the primary path.

### API boundary is complete when

* one stable response envelope is returned for EN/FR success,
* top-level fields are explicit and authoritative,
* the mapper is not inventing nominal planner-first truth.

### QA is complete when

* tests fail on runtime-path regressions,
* tests fail on missing metadata,
* tests fail on public-envelope drift,
* evaluator fails on routed-but-wrong-language FR output.

### Docs are complete when

* runtime status reflects the post-cutover truth,
* EN/FR acceptance defines real gates,
* public response contract matches the live success envelope,
* boundary docs remain explicit,
* overview/API docs do not preserve obsolete examples.

---

## 12. What “done” means for this cutover

This cutover is done only when all of the following are true:

* EN bio/person generation is planner-first,
* FR bio/person generation is planner-first,
* EN resolves to `WikiEng`,
* FR resolves to `WikiFre`,
* FR emits French surface text,
* shared GF no longer hides English or French bio/event surface,
* the runtime contract is canonical,
* the public response contract is coherent,
* the mapper is no longer the hidden owner of nominal truth,
* the evaluator can reject false positives,
* the docs reflect the new reality,
* and EN/FR no longer require legacy direct generation as their nominal path.

---

## 13. Relationship to other documents

This plan should be read together with:

* `docs/architecture/EN_FR_FINAL_PARALLEL_LOCKDOWN.md`
* `docs/architecture/multilingual_runtime_target.md`
* `docs/contracts/construction_runtime_contract.md`
* `docs/contracts/public_generation_response_contract.md`
* `docs/contracts/public_vs_runtime_vs_frontend_boundaries.md`
* `docs/testing/EN_FR_bio_acceptance.md`
* `docs/testing/en_fr_acceptance_and_multilingual_readiness.md`

Conflict rule:

* if the issue is execution-time precedence for parallel work, the lock document wins,
* if the issue is target architecture, the architecture document wins,
* if the issue is runtime contract shape, the runtime contract document wins,
* if the issue is public HTTP success shape, the public response contract wins,
* if the issue is execution order and cutover sequencing, this document wins,
* if the issue is final proof of EN/FR acceptance, `EN_FR_bio_acceptance.md` wins,
* if the issue is broader multilingual readiness framing, `en_fr_acceptance_and_multilingual_readiness.md` wins.

---

## 14. Final rule

The EN/FR cutover is not complete merely because a small set of files was updated.

It is complete only when:

* grammar ownership,
* runtime contract,
* nominal orchestration,
* public serialization,
* tests,
* evaluator behavior,
* and documentation boundaries

all converge to one final-compatible truth.

That is the standard for the first real multilingual vertical slice.

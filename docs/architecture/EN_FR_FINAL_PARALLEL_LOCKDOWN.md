# EN/FR Final Parallel Lockdown

Status: normative lock document
Owner: Architecture / Runtime / Grammar / API / QA
Scope: final lock for the EN/FR cutover while multiple files are edited in parallel
Immediate implementation scope: EN + FR bio/person only
Architectural intent: remove remaining ambiguity before the final cutover

---

## 1. Purpose

This document exists to eliminate remaining ambiguity while the EN/FR final update is coded in parallel.

It does **not** replace the architecture, runtime-contract, public-contract, boundary-contract, cutover, or acceptance documents.
It locks how they must be interpreted together for the final implementation.

Its job is to prevent parallel work from diverging on:

* source of truth,
* field ownership,
* compatibility behavior,
* planner-first semantics,
* runtime vs public vs frontend boundaries,
* public response semantics,
* QA pass/fail interpretation,
* and documentation precedence.

---

## 2. Source-of-truth stack

The source-of-truth order for this final cutover is:

1. `docs/architecture/multilingual_runtime_target.md`
2. `docs/contracts/construction_runtime_contract.md`
3. `docs/contracts/public_generation_response_contract.md`
4. `docs/contracts/public_vs_runtime_vs_frontend_boundaries.md`
5. `docs/migration/en_fr_cutover_plan.md`
6. `docs/testing/EN_FR_bio_acceptance.md`
7. this document

Interpretation rule:

* architecture defines what the system must be,
* the construction runtime contract defines the canonical runtime object model,
* the public generation response contract defines the canonical HTTP success envelope,
* the boundary contract defines ownership separation between runtime, public HTTP, and frontend/client layers,
* the cutover plan defines sequencing and completion gates,
* EN/FR acceptance defines the release-blocking proof layer,
* this document locks operational interpretation where parallel coding could otherwise drift.

---

## 3. Documents that are authoritative vs informative

### 3.1 Authoritative for the final EN/FR cutover

The following are authoritative:

* `docs/architecture/multilingual_runtime_target.md`
* `docs/contracts/construction_runtime_contract.md`
* `docs/contracts/public_generation_response_contract.md`
* `docs/contracts/public_vs_runtime_vs_frontend_boundaries.md`
* `docs/migration/en_fr_cutover_plan.md`
* `docs/testing/EN_FR_bio_acceptance.md`
* this document

### 3.2 Informative but not the operative EN/FR acceptance gate

`docs/testing/en_fr_acceptance_and_multilingual_readiness.md` remains authoritative for the multilingual readiness model and tiering vocabulary, but it is **not** the operative EN/FR release gate once the final cutover lands.

Lock:

* `EN_FR_bio_acceptance.md` is the operative EN/FR acceptance reference.
* `en_fr_acceptance_and_multilingual_readiness.md` is the broader readiness-framework reference.
* If the two overlap on EN/FR release gating, `EN_FR_bio_acceptance.md` wins.

### 3.3 Current-state doc rule

`docs/2-Technical-Reference/CURRENT_RUNTIME_STATUS.md` is a status document only.
It is never allowed to overrule architecture, contracts, boundary rules, or acceptance.

If it still describes a hybrid or pre-cutover state, it is stale and must be rewritten.

---

## 4. What is already locked in the current repo state

The following are treated as already structurally decided and must not be reopened:

1. `WikiI` is language-neutral for the EN/FR bio functions and must remain so.
2. `WikiEng` owns English bio/event realization.
3. `WikiFre` owns French bio/event realization.
4. The target nominal runtime is planner-first.
5. The target internal runtime contract is `ConstructionPlan -> SurfaceResult`.
6. The public success envelope uses:

   * `text`
   * `lang_code`
   * `construction_id`
   * `renderer_backend`
   * `fallback_used`
   * `tokens`
   * `debug_info`
   * `generation_time_ms`
7. FR routed-to-`WikiFre` but surfacing English is a hard acceptance failure.

These items are no longer design questions.
They are implementation obligations.

---

## 5. Remaining ambiguities now resolved by this document

The current repository state still leaves a few operational ambiguities.
This document resolves them definitively.

### 5.1 Canonical runtime result object

Lock:

* The canonical planner-first output object is `SurfaceResult`.
* `Sentence` may remain only as a backward-compatible alias or compatibility model, not as the conceptual runtime target.
* New planner-first code must construct and return canonical runtime results conforming exactly to the `SurfaceResult` contract.
* No planner-first success path may rely on the response mapper to invent missing nominal metadata.

### 5.2 Mapper backfill scope

Lock:

* `generation_response_mapper.py` may normalize data.
* It may preserve compatibility for old result shapes only where explicitly required.
* It must **not** be the place where planner-first nominal metadata becomes real for the first time.
* On the nominal planner-first path, `construction_id`, `renderer_backend`, `fallback_used`, `tokens`, and `generation_time_ms` must already exist at top level before mapping.
* Missing nominal planner-first metadata is a runtime bug, not a mapper responsibility.

### 5.3 Legacy-field acceptance

Lock:

* The final public success envelope never emits `surface_text` or `meta` as primary success fields.
* Compatibility ingestion of legacy result shapes is tolerated only as an internal migration shim, never as the target contract.
* No new code may be written that depends on legacy-only top-level success fields.

### 5.4 Compatibility markers

Lock:

* Compatibility markers such as `compatibility_mode`, `compatibility_shim`, `legacy_result_key`, or `fallback_reason` may appear inside `debug_info` when they truthfully describe compatibility behavior.
* Their presence never upgrades a compatibility path into nominal success.
* If compatibility behavior is used, `fallback_used` and `runtime_path` must make that visible.

### 5.5 Acceptance-doc duplication

Lock:

* `docs/testing/EN_FR_bio_acceptance.md` is the release-blocking EN/FR acceptance gate.
* `docs/testing/en_fr_acceptance_and_multilingual_readiness.md` retains the multilingual readiness model.
* The latter must cross-reference the former and must not redefine the EN/FR release gate differently.

---

## 6. Final architectural invariants

These invariants are mandatory and non-negotiable.

### 6.1 Planner-first runtime invariant

The nominal runtime path is exactly:

`canonical input -> planner -> lexical resolution -> realizer -> SurfaceResult -> public response`

Locks:

* direct legacy generation is compatibility-only,
* compatibility-only does not count as nominal success,
* no backend may become a second planner,
* no renderer may invent the sentence architecture after planning.

### 6.2 Shared-core language neutrality invariant

Locks:

* no shared runtime layer may own EN or FR surface strings,
* no shared GF layer may hide English or French sentence templates,
* no bridge, runtime shortcut, or mapper may fake language-correct French from a language-agnostic layer.

### 6.3 Concrete-language ownership invariant

Locks:

* `WikiEng` owns English bio/event surface realization,
* `WikiFre` owns French bio/event surface realization,
* future languages must follow the same rule,
* no language is allowed to inherit hidden English-like realization from shared GF.

### 6.4 Public-envelope invariant

The final success envelope is exactly:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `tokens`
* `debug_info`
* `generation_time_ms`

Locks:

* `text` is authoritative,
* `lang_code` is authoritative,
* `generation_time_ms` top-level is authoritative,
* `debug_info` must not contradict top-level fields,
* success responses must not drift by backend or language.

### 6.5 Boundary invariant

Locks:

* runtime contracts are not public HTTP contracts,
* public HTTP contracts are not frontend convenience models,
* frontend/client shapes must not redefine the public success envelope,
* the mapper is a serialization boundary, not the source of nominal runtime truth.

### 6.6 Language-correctness invariant

Locks:

* routable is not accepted,
* compile-capable is not accepted,
* non-empty output is not accepted,
* FR output that still looks English is a hard failure,
* language acceptance is measured by runtime path, contract validity, and surface correctness together.

---

## 7. File ownership and edit boundaries for parallel work

This section locks what each file is allowed to decide.

### 7.1 `gf/WikiI.gf`

Owns only:

* shared lincats,
* language-neutral helpers,
* abstraction-level support.

Must not own:

* English bio clauses,
* French bio clauses,
* hidden default bio/event realization,
* string concatenation that encodes one natural language.

### 7.2 `gf/WikiEng.gf`

Owns:

* English realization of `mkBioProf`
* English realization of `mkBioNat`
* English realization of `mkBioFull`
* English realization of `mkEvent`

Must remain explicit even after shared GF cleanup.

### 7.3 `gf/WikiFre.gf`

Owns:

* French realization of `mkBioProf`
* French realization of `mkBioNat`
* French realization of `mkBioFull`
* French realization of `mkEvent`

Must never depend on inherited English literals.

### 7.4 `app/core/use_cases/generate_text.py`

Owns:

* nominal-path orchestration,
* planner-first truth,
* explicit fallback policy,
* result normalization into a canonical runtime result,
* runtime-path truth in metadata.

Must not delegate nominal contract truth to the API mapper.

### 7.5 `app/adapters/api/contracts/generation_response_mapper.py`

Owns:

* public success serialization,
* top-level/debug parity,
* token normalization,
* compatibility parsing where still intentionally preserved.

Must not:

* invent nominal planner-first metadata that should already exist,
* become the hidden owner of runtime truth,
* emit alternate success shapes.

### 7.6 `tests/core/test_use_cases.py`

Owns:

* use-case regression detection,
* planner-first nominal assertions,
* fallback-path assertions,
* missing-metadata failures,
* repeated-call stability checks for the migrated path.

### 7.7 `tools/qa/eval_bios.py`

Owns:

* public-contract validation for evaluation runs,
* surface-language plausibility checks,
* FR routed-but-English failure detection,
* evaluator pass/fail semantics for EN/FR bio generation.

### 7.8 `docs/2-Technical-Reference/CURRENT_RUNTIME_STATUS.md`

Owns only:

* current-state description after cutover.

Must not:

* tell a pre-cutover hybrid story after the final update,
* contradict the final architecture or acceptance state.

### 7.9 `docs/testing/EN_FR_bio_acceptance.md`

Owns:

* operative EN/FR release gate,
* concrete pass/fail criteria,
* mandatory FR failure semantics,
* required response-shape expectations for EN/FR bio generation.

### 7.10 `docs/testing/en_fr_acceptance_and_multilingual_readiness.md`

Owns:

* tier model,
* multilingual readiness vocabulary,
* broader onboarding and readiness framing.

Must not own the operative EN/FR release gate once the final cutover is locked.

### 7.11 `docs/contracts/public_generation_response_contract.md`

Owns:

* public HTTP success envelope shape,
* success-field semantics,
* field parity rules,
* deprecation of legacy success shapes.

### 7.12 `docs/contracts/public_vs_runtime_vs_frontend_boundaries.md`

Owns:

* runtime vs public vs frontend layer separation,
* field ownership by boundary layer,
* mapper boundary semantics,
* anti-drift rules across runtime, HTTP, and frontend/client models.

---

## 8. Runtime-result contract locked for implementation

The runtime object handed to the response mapper on the nominal planner-first path must satisfy all of the following before mapping:

* `text`: non-empty string
* `lang_code`: normalized lowercase language code
* `construction_id`: explicit, top-level, non-empty on nominal path
* `renderer_backend`: explicit, top-level, non-empty on nominal path
* `fallback_used`: explicit boolean
* `tokens`: explicit ordered list of strings on nominal planner-first success
* `debug_info`: dict
* `generation_time_ms`: float-like top-level value

### 8.1 Required `debug_info` keys on nominal planner-first path

The following keys must be present or mirrored in `debug_info` for nominal planner-first success:

* `runtime_path = "planner_first"`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`

Recommended when available:

* `resolved_language`
* `selected_backend`
* `attempted_backends`
* `slot_keys`
* `backend_trace`

### 8.2 Parity rule

When both top-level and `debug_info` contain the same semantic field, they must match.
This includes at least:

* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`

### 8.3 No nominal nulls rule

On nominal planner-first success for EN/FR bio generation:

* `construction_id` must not be null,
* `renderer_backend` must not be null,
* `fallback_used` must not be omitted,
* `tokens` must not be omitted,
* `debug_info` must not be omitted.

---

## 9. Mapper lock rules

### 9.1 Allowed responsibilities

The mapper may:

* coerce field types,
* normalize `lang_code`,
* normalize `tokens`,
* mirror canonical top-level fields into `debug_info`,
* preserve truthful compatibility metadata,
* parse older internal result shapes during the migration tail.

### 9.2 Forbidden responsibilities

The mapper must not:

* silently turn planner-first missing fields into acceptable nominal output,
* declare a compatibility result to be nominal planner-first,
* emit a success envelope missing required top-level fields,
* rely on `debug_info`-only values as the intended steady-state source for nominal planner-first fields.

### 9.3 Final-state strictness

For the final EN/FR cutover branch, the intended steady state is:

* planner-first results arrive mapper-ready,
* the mapper serializes rather than repairs,
* legacy ingestion is tolerated only as a diminishing compatibility edge.

---

## 10. GenerateText lock rules

### 10.1 Nominal-path rule

`GenerateText` must treat planner-first as the nominal runtime whenever planner and realizer are available.

### 10.2 Legacy rule

Legacy direct generation may remain only as an explicit compatibility fallback while final cleanup is still being completed.
It must never be treated as target-state success.

### 10.3 Fallback visibility rule

If fallback occurs:

* `fallback_used = true`
* `debug_info.runtime_path` must state the actual path used
* `debug_info` may record compatibility details
* the result must still serialize to the same public envelope

### 10.4 Failure-fast rule

If planner-first is claimed but required nominal metadata is missing, the runtime must fail fast rather than silently degrade into a fake nominal success.

---

## 11. Test and evaluator lock rules

### 11.1 Core tests must fail on

* planner-first nominal path regression,
* missing `construction_id` on nominal planner-first success,
* missing `renderer_backend` on nominal planner-first success,
* missing `tokens` on nominal planner-first success,
* silent fallback when fallback is disallowed,
* nondeterministic behavior introduced by shared mutable state,
* contract assumptions drifting away from the public envelope.

### 11.2 Evaluator must fail on

* invalid public envelope,
* wrong `lang_code`,
* missing or contradictory `fallback_used`,
* missing or contradictory `runtime_path`,
* missing required nominal public fields,
* FR resolved to `WikiFre` but surfacing obvious English,
* contract-valid but language-invalid output.

### 11.3 Acceptance counting rule

The evaluator and docs must count the following as **not accepted**:

* compile success only,
* routable success only,
* non-empty output only,
* compatibility-only legacy success,
* FR output that still looks English.

---

## 12. Documentation synchronization lock

When the final code lands, the docs must describe one coherent truth.

### 12.1 `CURRENT_RUNTIME_STATUS.md`

Must be rewritten to the post-cutover truth.
It must no longer say, imply, or preserve as current that:

* planner-first is still merely partial for EN/FR bio,
* FR is only routable but not validated,
* hybrid runtime status is the intended current state.

### 12.2 `EN_FR_bio_acceptance.md`

Must be treated as the operative acceptance gate.
It should contain the final pass/fail truth, not a provisional migration story.

### 12.3 `en_fr_acceptance_and_multilingual_readiness.md`

Must explicitly defer EN/FR operative gating to `EN_FR_bio_acceptance.md`.
It remains the reference for readiness tiering and future-language policy.

### 12.4 `public_generation_response_contract.md`

Must match the live final success envelope exactly.
No drift is allowed between this doc, the mapper, tests, and evaluator assumptions.

### 12.5 `public_vs_runtime_vs_frontend_boundaries.md`

Must remain aligned with the final branch truth that:

* `SurfaceResult` is a runtime object,
* the HTTP success envelope is a public transport object,
* frontend or client convenience models do not redefine the public contract,
* the mapper is a public boundary, not the owner of nominal runtime truth.

---

## 13. Forbidden moves during parallel coding

The following are forbidden while implementing the final update:

1. reintroducing EN or FR surface strings into `WikiI`
2. adding a new shared-layer language-specific fallback
3. making the mapper the hidden owner of nominal planner-first fields
4. counting legacy fallback as accepted EN/FR success
5. documenting FR routing as equivalent to FR correctness
6. emitting alternate public success shapes by backend
7. keeping two EN/FR acceptance truths active after the update
8. shipping code that claims planner-first while omitting required nominal metadata
9. leaving `CURRENT_RUNTIME_STATUS.md` on a pre-cutover hybrid story after code is final
10. adding new compatibility shims instead of converging on the target contract

---

## 14. Locked build and validation sequence

The final execution order remains:

1. change source files
2. refresh Everything Matrix or system index
3. compile GF or PGF
4. run runtime and language health
5. run real EN and FR generation calls
6. run tests
7. run `eval_bios`
8. synchronize docs to the achieved truth
9. remove or permanently demote remaining EN/FR legacy-primary behavior

This order is locked for the final cutover.

---

## 15. Definition of done locked for this branch

The branch is not done until all of the following are true at the same time:

1. EN bio/person generation is nominal planner-first
2. FR bio/person generation is nominal planner-first
3. EN resolves to `WikiEng`
4. FR resolves to `WikiFre`
5. FR output is actually French
6. `WikiI` is still language-neutral
7. planner-first runtime returns mapper-ready `SurfaceResult` objects
8. public responses expose the canonical success envelope with explicit top-level fields
9. top-level and `debug_info` parity holds for canonical shared fields
10. core tests fail on missing nominal metadata
11. `eval_bios` fails routed-but-English FR output
12. `CURRENT_RUNTIME_STATUS.md` reflects the post-cutover truth
13. `EN_FR_bio_acceptance.md` is the operative EN/FR release gate
14. `en_fr_acceptance_and_multilingual_readiness.md` no longer competes with the operative EN/FR gate
15. legacy direct generation is no longer the nominal EN/FR bio/person path

---

## 16. Final rule

During the final EN/FR cutover, there is exactly one acceptable implementation direction:

* planner-first as nominal runtime,
* language-neutral shared core,
* concrete-language-owned realization,
* canonical `SurfaceResult` before API mapping,
* one public success envelope,
* one operative EN/FR acceptance gate,
* one explicit runtime/public/frontend boundary model,
* and no false-positive language success.

If any file, test, or document still allows FR to appear successful while inheriting another language’s surface behavior, or allows planner-first to appear successful while missing canonical nominal metadata, the cutover is not complete.

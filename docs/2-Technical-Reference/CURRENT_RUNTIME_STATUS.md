# CURRENT RUNTIME STATUS

Last checked: 2026-03-19

## Purpose

This document records the **current observable runtime behavior** of SemantiK Architect **for the post-cutover EN/FR runtime state**.

It is an operations/status page, not a target-state architecture spec.
It does not redefine architecture, contracts, or acceptance.
Its role is to describe the runtime state that is considered **current and true** once the EN/FR final cutover is in place.

Where target architecture, runtime contract, public contract, cutover sequencing, and acceptance criteria all converge, this document records the **current live result** of that convergence.

---

## 1. Executive summary

SemantiK Architect is currently in a **planner-first runtime state** for the EN/FR bio/person slice.

In practical terms, this means:

* the nominal single-sentence generation path is planner-first,
* the canonical internal runtime handoff is `ConstructionPlan -> SurfaceResult`,
* the public `/api/v1/generate/{lang_code}` route remains the stable generation entrypoint,
* EN bio/person generation resolves to `WikiEng` and surfaces English,
* FR bio/person generation resolves to `WikiFre` and surfaces French,
* the public success envelope is stable and explicit,
* and language correctness is evaluated by routing, runtime path, contract validity, and surface correctness together.

Compatibility support may still exist at specific ingestion or fallback edges, but it is **not** the current runtime center of truth and it does **not** define nominal success.

---

## 2. Public HTTP surface currently mounted

The backend is canonically served under `/api/v1/...`.

Currently mounted routes include:

* generation under `/api/v1/generate/...`,
* health under both `/health/*` and `/api/v1/health/*`,
* public language/entity/frame endpoints under `/api/v1/...`,
* management endpoints under `/api/v1/...`,
* tools under `/api/v1/tools/...`.

Dual health mounting remains intentional so probes and API consumers can both use health routes without path-rewrite assumptions.

---

## 3. Current generation endpoint

The primary generation route is:

`POST /api/v1/generate/{lang_code}`

This is the canonical route used by frontend/tooling, smoke checks, and runtime validation flows.

### Current public response shape

Successful generation requests currently serialize to one canonical JSON envelope centered on:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `tokens`
* `debug_info`
* `generation_time_ms`

Current interpretation:

* `text` is authoritative,
* `lang_code` identifies the returned surface language,
* `construction_id` is explicit on the nominal path,
* `renderer_backend` is explicit on the nominal path,
* `fallback_used` is explicit,
* `tokens` correspond to the final surface text,
* `generation_time_ms` is top-level and authoritative,
* `debug_info` must not contradict top-level fields.

Older success expectations centered on `surface_text` / `meta` are not aligned with the current public contract.

---

## 4. Request normalization currently supported

### 4.1 Language resolution

`{lang_code}` in the URL is currently **authoritative**.

If the payload also includes a language field (`lang`, `language`, `lang_code`, or `inputs.language`), it must normalize to the same language as the URL or the request is rejected. If the URL does not provide a language, the payload must provide one.

Language normalization currently:

* lowercases,
* strips a leading `wiki...` prefix if present,
* canonicalizes through shared lexicon code normalization.

### 4.2 Bio/person compatibility ingestion

The runtime still accepts multiple legacy and compatibility aliases for biography/person generation at the request boundary, including:

* `bio`
* `biography`
* `entity.person`
* `entity_person`
* `person`
* `entity.person.v1`
* `entity.person.v2`

These inputs are normalized into the current bio/person frame path before generation.

Current interpretation:

* compatibility ingestion is permitted,
* but compatibility ingestion does not redefine the nominal runtime,
* and it does not weaken the planner-first acceptance gate.

### 4.3 Prototype / Ninai support

If the incoming payload contains a top-level `function`, it is treated as a Ninai-style / prototype-style payload and routed through Ninai parsing rather than the standard frame parser.

This support may still exist as a compatibility/prototype boundary, but it is not the canonical production semantics for the EN/FR final bio/person slice.

---

## 5. Current runtime center of truth

### 5.1 Current nominal runtime path

The nominal runtime path is:

`canonical input -> planner -> lexical resolution -> realizer -> SurfaceResult -> API response mapping`

The canonical runtime handoff is:

`ConstructionPlan -> SurfaceResult`

This is the runtime truth for the current EN/FR bio/person slice.

### 5.2 Current runtime interpretation

Current operational interpretation is:

* planner-first is the nominal runtime,
* direct legacy generation is not the current target-state path,
* compatibility-only success does not count as nominal success,
* runtime truth must exist before API mapping,
* and the response mapper serializes canonical results rather than inventing nominal metadata for the first time.

### 5.3 Observable runtime metadata

The runtime is expected to expose structured `debug_info`.

On the nominal planner-first path, current runtime metadata is expected to make the following visible:

* `runtime_path`
* `fallback_used`
* `renderer_backend`
* `construction_id`
* `lang_code`

Additional structured metadata may include values such as:

* `resolved_language`
* `selected_backend`
* `attempted_backends`
* `slot_keys`
* `backend_trace`
* truthful compatibility markers when compatibility behavior is actually used

Current interpretation:

* `debug_info` mirrors runtime truth,
* it does not replace required top-level public fields,
* and compatibility metadata never upgrades a compatibility path into nominal success.

---

## 6. Health and validation endpoints

The current runtime exposes:

* `/health/live`
* `/health/ready`
* `/api/v1/health/live`
* `/api/v1/health/ready`

These endpoints remain part of the expected public runtime surface.

The recommended validation path for runtime status remains:

1. refresh matrix,
2. validate lexicon,
3. compile PGF,
4. run runtime/language health,
5. run real EN and FR generation requests,
6. run relevant tests,
7. run `eval_bios`,
8. ensure docs reflect the achieved truth.

---

## 7. Current EN / FR status

### 7.1 English

English bio/person generation is currently accepted for the target EN/FR cutover scope.

Current operational interpretation:

* `/api/v1/generate/en` is accepted,
* the request resolves to `WikiEng`,
* the nominal runtime path is planner-first,
* `fallback_used = false` on nominal success,
* the response contains the canonical public success envelope,
* and the final surface text is English.

### 7.2 French

French bio/person generation is currently accepted for the target EN/FR cutover scope.

Current operational interpretation:

* `/api/v1/generate/fr` is accepted,
* the request resolves to `WikiFre`,
* the nominal runtime path is planner-first,
* `fallback_used = false` on nominal success,
* the response contains the canonical public success envelope,
* and the final surface text is French.

Hard rule:

* FR routed to `WikiFre` but still surfacing English is **not** a partial success,
* it is a hard acceptance failure,
* and it is not part of the current accepted runtime state.

### 7.3 EN / FR scope note

The current accepted scope described here is:

* EN bio/person generation
* FR bio/person generation

This document does not claim that all languages or all constructions have reached the same state.

---

## 8. What is stable right now

The following are current runtime facts:

* `/api/v1/generate/{lang_code}` is the canonical public generation route.
* URL language is authoritative over payload language.
* planner-first is the nominal runtime for the EN/FR bio/person slice.
* the canonical internal runtime handoff is `ConstructionPlan -> SurfaceResult`.
* EN resolves to `WikiEng`.
* FR resolves to `WikiFre`.
* FR success requires actual French surface output.
* the public response contract is JSON with `text`, explicit structured runtime metadata, and authoritative top-level fields.
* health endpoints are mounted in both root and `/api/v1` forms.
* runtime validation still includes real generation calls as part of readiness/acceptance proof.

---

## 9. What remains intentionally compatibility-scoped

The following may still exist at the boundary or compatibility edges without changing the current nominal runtime truth:

* legacy bio/person request aliases,
* Ninai/prototype-style input handling where still wired,
* compatibility parsing of older internal result shapes,
* compatibility/debug markers that truthfully describe fallback or migration behavior.

Current interpretation:

* these are compatibility surfaces,
* not the architectural center of truth,
* not the nominal planner-first success path,
* and not an alternate acceptance model.

---

## 10. What is no longer correct to say

The following are **not** correct current-state descriptions after the EN/FR final cutover:

* that planner-first is only a target and not the current nominal runtime for EN/FR bio/person generation,
* that direct frame-to-engine generation remains the primary EN/FR bio/person path,
* that FR is merely routable but not validated for correct French surface output,
* that `surface_text` / `meta` remain the canonical public success contract,
* that routed-but-English FR output can still be counted as operational success,
* that current runtime truth can be inferred from compatibility behavior alone.

---

## 11. Current status statement

As of 2026-03-19, SemantiK Architect should be described as:

> a working API with stable public generation and health endpoints, planner-first nominal runtime for the EN/FR bio/person slice, a canonical `ConstructionPlan -> SurfaceResult` internal contract, explicit top-level public success fields, English owned by `WikiEng`, French owned by `WikiFre`, and EN/FR acceptance that requires both contract correctness and language-correct surface realization.

---

## 12. Relationship to other documents

This document is a **status page** only.

It must be read consistently with:

* `docs/architecture/multilingual_runtime_target.md`
* `docs/contracts/construction_runtime_contract.md`
* `docs/contracts/public_generation_response_contract.md`
* `docs/contracts/public_vs_runtime_vs_frontend_boundaries.md`
* `docs/contracts/debug_info_contract.md`
* `docs/migration/en_fr_cutover_plan.md`
* `docs/testing/EN_FR_bio_acceptance.md`
* `docs/architecture/EN_FR_FINAL_PARALLEL_LOCKDOWN.md`

Conflict rule:

* architecture and contracts define what is authoritative,
* the cutover plan defines completion sequencing,
* `EN_FR_bio_acceptance.md` defines the operative EN/FR release gate,
* the lockdown doc defines operational interpretation during the final parallel update,
* this document only records the resulting current runtime truth.
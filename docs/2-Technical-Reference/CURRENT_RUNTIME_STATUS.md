# CURRENT RUNTIME STATUS

Last checked: 2026-03-16

## Purpose

This document records the **current observable runtime behavior** of SemantiK Architect. It is an operations/status page, not a target-state architecture spec.

Where the repository contains both:

* a **target** planner-centered contract, and
* a **currently live** compatibility path,

this document describes the **currently live** behavior first, then notes the intended direction.  

---

## 1. Executive summary

SemantiK Architect is currently in a **mixed runtime state**:

* the repository’s target runtime is **planner-centered**,
* the public `/api/v1/generate/{lang_code}` route is still externally stable,
* but live single-sentence generation may still run through a **legacy direct frame path** depending on runtime configuration,
* and compatibility shims remain active for legacy bio/person payload shapes.  

In practical terms, the system is **usable now**, but it is **not yet fully converged** on the planner-first runtime contract across all active generation paths.  

---

## 2. Public HTTP surface currently mounted

The backend is canonically served under `/api/v1/...`.

Currently mounted routes include:

* generation under `/api/v1/generate/...`,
* health under both `/health/*` and `/api/v1/health/*`,
* public language/entity/frame endpoints under `/api/v1/...`,
* management endpoints under `/api/v1/...`,
* tools under `/api/v1/tools/...`. 

This dual health mounting is intentional so probes and API consumers can both use health routes without path rewriting assumptions. 

---

## 3. Current generation endpoint

The primary generation route is:

`POST /api/v1/generate/{lang_code}`

This is the route used by the frontend/tooling and by runtime validation flows in the repo.  

### Current public response shape

The public response mapper currently targets a JSON response centered on:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `tokens`
* `debug_info`
* optionally `generation_time_ms` when present in the underlying result.  

This means older docs or clients expecting only `surface_text` / `meta` are not aligned with the current public contract. 

---

## 4. Request normalization currently supported

### 4.1 Language resolution

`{lang_code}` in the URL is currently **authoritative**.

If the payload also includes a language field (`lang`, `language`, `lang_code`, or `inputs.language`), it must normalize to the same language as the URL or the request is rejected. If the URL does not provide a language, the payload must provide one.  

Language normalization currently:

* lowercases,
* strips a leading `wiki...` prefix if present,
* canonicalizes through shared lexicon code normalization. 

### 4.2 Bio/person compatibility shims

The runtime still accepts multiple legacy and compatibility aliases for biography/person generation, including:

* `bio`
* `biography`
* `entity.person`
* `entity_person`
* `person`
* `entity.person.v1`
* `entity.person.v2` 

These inputs are normalized into the current bio/person frame path before generation. 

### 4.3 Prototype / Ninai support

If the incoming payload contains a top-level `function`, it is treated as a Ninai-style / prototype-style payload and routed through Ninai parsing rather than the standard frame parser. This support still exists, but it is not the canonical production path. 

---

## 5. Current runtime center of truth

### 5.1 Target direction

The approved migration target is:

`API payload -> frame normalization -> frame-to-plan bridge -> planner -> PlannedSentence -> ConstructionPlan -> lexical resolution -> renderer backend -> SurfaceResult -> API response mapping` 

The contract docs are explicit that active backends are expected to converge on:

`ConstructionPlan -> SurfaceResult` 

### 5.2 Current live behavior

The migration doc also states that the live `/generate` path still bypasses the planner-centered architecture for single-sentence generation in the current state. 

In other words:

* the planner-first runtime exists,
* the target contract exists,
* but the externally stable generate path is still in migration,
* and compatibility layers remain part of the active system.  

### 5.3 Observable runtime metadata

The runtime is expected to expose structured `debug_info`, and migration acceptance criteria require backend identity, construction identity, and fallback state to remain visible.  

In current local smoke tests on 2026-03-16, generation returned debug metadata including values such as:

* `runtime_path`
* `fallback_used`
* `renderer_backend`
* `compatibility_shim`
* `resolved_language`

This is consistent with the repository’s current migration/testing direction.

---

## 6. Health and validation endpoints

The current runtime exposes:

* `/health/live`
* `/health/ready`
* `/api/v1/health/live`
* `/api/v1/health/ready` 

Repo smoke tests treat these endpoints as part of the expected public runtime surface. 

The repository’s recommended validation path for runtime status remains:

1. refresh matrix,
2. validate lexicon,
3. compile PGF,
4. run language health,
5. run one real generation request. 

---

## 7. Current EN / FR status

### 7.1 English

English biography generation is currently operational in local smoke tests.

Observed on 2026-03-16:

* `/api/v1/generate/en` accepted a bio payload,
* returned `text`,
* resolved to `WikiEng`,
* and produced an English sentence.

### 7.2 French

French is **routable**, but not yet fully validated as a correct French surface generator in the currently observed runtime.

Observed on 2026-03-16:

* `/api/v1/generate/fr` accepted the same bio payload,
* returned `lang_code: "fr"`,
* resolved the concrete language to `WikiFre`,
* but still produced an English sentence in output.

This is consistent with the current grammar layout where `WikiFre` is present as a concrete grammar, while the FR surface behavior is not yet demonstrably aligned with the target French output expectations. The migration/test docs also treat EN/FR planner-first validation as an explicit acceptance concern rather than a completed fact.  

Current operational interpretation:

* **EN bio:** working
* **FR routing:** working
* **FR surface realization quality:** not yet validated as production-correct

---

## 8. What is stable right now

The following appear stable enough to treat as current runtime facts:

* `/api/v1/generate/{lang_code}` is the canonical public generation route. 
* URL language is authoritative over payload language. 
* legacy bio/person aliases are intentionally still accepted. 
* health endpoints are mounted in both root and `/api/v1` forms. 
* the public response contract is JSON with `text` and structured runtime metadata, not only legacy `surface_text/meta`. 
* runtime validation in the repo still assumes “one real generation call” is part of language readiness. 

---

## 9. What is not yet safe to claim as fully complete

The following should **not** yet be documented as universally true in current-state docs:

* that planner-first runtime is the only active generation path,
* that direct frame-to-engine generation is no longer primary in all live cases,
* that French bio generation is fully correct end to end,
* that all active backends already consume one identical planner-facing contract in production behavior,
* that current runtime docs can be inferred from target-state migration docs alone.   

---

## 10. Current status statement

As of 2026-03-16, SemantiK Architect should be described as:

> a working API with stable public generation and health endpoints, active compatibility shims for bio/person payloads, an in-progress migration toward a planner-centered `ConstructionPlan -> SurfaceResult` runtime, and partial but not yet fully validated EN/FR parity in live generation behavior.  

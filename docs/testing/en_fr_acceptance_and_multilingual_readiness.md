# EN/FR Acceptance and Multilingual Readiness

Status: normative acceptance and readiness document  
Owner: QA / Runtime / Grammar / API  
Scope: operative relationship between EN/FR acceptance and the multilingual readiness model  
Immediate implementation scope: EN + FR bio/person only  
Architectural scope: scalable readiness framework for future expansion to hundreds of languages

---

## 1. Purpose

This document defines two related but distinct things:

1. the relationship between the **EN/FR acceptance gate** and the broader system,
2. the **readiness model** that future languages must follow.

It exists to prevent the system from confusing:

- routing with correctness,
- compile success with readiness,
- non-empty output with language success,
- compatibility behavior with nominal runtime behavior,
- and broad multilingual presence with acceptance for a specific target scope.

This document is not the only acceptance document in the system.  
For the EN/FR bio/person cutover, the operative pass/fail acceptance gate is defined in `EN_FR_bio_acceptance.md`.

This document defines the broader readiness framework that must remain consistent with that gate.

---

## 2. Document role and precedence

This document is normative, but it does not replace the more specific EN/FR acceptance gate.

### 2.1 EN/FR acceptance gate

For EN/FR bio/person generation, the operative acceptance reference is:

- `docs/testing/EN_FR_bio_acceptance.md`

That document is the direct pass/fail gate for the EN/FR cutover.

### 2.2 Role of this document

This document defines:

- how EN/FR acceptance relates to the larger multilingual model,
- how readiness tiers must be interpreted,
- how future languages must be classified,
- and which distinctions the system must preserve as it scales.

### 2.3 Conflict rule

If the issue is:

- **specific EN/FR bio/person acceptance behavior**, `EN_FR_bio_acceptance.md` wins,
- **multilingual readiness tiering or future-language onboarding**, this document wins,
- **runtime architecture**, `multilingual_runtime_target.md` wins,
- **public success envelope**, `public_generation_response_contract.md` wins.

This document must not contradict any of those sources.

---

## 3. Core acceptance principle

A language is accepted only when it passes the acceptance requirements for its declared scope.

A language is not accepted because it:

- exists in GF,
- compiles,
- loads,
- routes,
- or emits any non-empty string.

Acceptance requires a full vertical slice for the target scope:

- canonical semantic input,
- planner-first runtime behavior,
- language-appropriate lexical resolution,
- language-specific realization,
- coherent public response contract,
- evaluator success,
- and explicit surface-language correctness.

---

## 4. EN/FR cutover interpretation

For the immediate cutover, EN and FR are the first complete vertical slice.

That means EN and FR must prove that the architecture works end to end for bio/person generation:

- canonical input enters the system,
- planner-first is the nominal path,
- the shared core remains language-neutral,
- English realization is owned by `WikiEng`,
- French realization is owned by `WikiFre`,
- the public success envelope is coherent,
- and evaluation rejects false positives.

This document does not itself redefine all EN/FR acceptance details.  
Those details belong in `EN_FR_bio_acceptance.md`.

---

## 5. Normative variables

These variables are normative and must stay consistent across tests, QA tools, docs, and reporting.

### 5.1 Runtime variables

- `EXPECTED_PRIMARY_RUNTIME = "planner_first"`
- `LEGACY_SUCCESS_COUNTS_AS_ACCEPTED = false`
- `LEGACY_FALLBACK_COUNTS_AS_NOMINAL_SUCCESS = false`
- `LANGUAGE_ROUTE_DOES_NOT_IMPLY_LANGUAGE_READINESS = true`

### 5.2 EN variables

- `EN_REQUEST_LANG = "en"`
- `EN_EXPECTED_GF_LANGUAGE = "WikiEng"`
- `EN_SURFACE_LANGUAGE = "english"`

### 5.3 FR variables

- `FR_REQUEST_LANG = "fr"`
- `FR_EXPECTED_GF_LANGUAGE = "WikiFre"`
- `FR_SURFACE_LANGUAGE = "french"`
- `FR_SURFACE_MUST_NOT_LOOK_ENGLISH = true`

### 5.4 Public contract variables

- `REQUIRED_PUBLIC_TEXT = true`
- `REQUIRED_PUBLIC_LANG_CODE = true`
- `REQUIRED_PUBLIC_CONSTRUCTION_ID = true` on nominal path
- `REQUIRED_PUBLIC_RENDERER_BACKEND = true` on nominal path
- `REQUIRED_PUBLIC_FALLBACK_USED = true`
- `REQUIRED_PUBLIC_TOKENS = true`
- `REQUIRED_PUBLIC_DEBUG_INFO = true`
- `REQUIRED_PUBLIC_GENERATION_TIME_MS = true`

### 5.5 Metadata parity variables

- `TOP_LEVEL_AND_DEBUG_LANG_CODE_MUST_MATCH = true`
- `TOP_LEVEL_AND_DEBUG_FALLBACK_MUST_MATCH = true`
- `TOP_LEVEL_AND_DEBUG_BACKEND_MUST_MATCH = true` when both are present
- `TOP_LEVEL_TIME_IS_AUTHORITATIVE = true`

### 5.6 Readiness variables

- `READINESS_MODEL_REQUIRED = true`
- `NEW_LANGUAGE_MUST_PASS_READINESS_GATES = true`
- `ADVERTISED_LANGUAGE_SCOPE_MUST_NOT_EXCEED_EARNED_TIER = true`

---

## 6. Acceptance scope

This document covers:

- the role of EN/FR acceptance within the larger multilingual system,
- readiness classification for future languages,
- the distinction between presence and readiness,
- public contract expectations relevant to readiness,
- and evaluator/reporting expectations for language status.

This document does not claim:

- that all languages are accepted,
- that all constructions are accepted,
- that compile success implies runtime correctness,
- or that EN/FR acceptance automatically implies acceptance for future languages.

---

## 7. EN/FR acceptance dependency

EN and FR are considered accepted for the immediate cutover only when they satisfy the full requirements defined in `EN_FR_bio_acceptance.md`.

At minimum, that means:

- request language matches the returned surface language,
- runtime resolves to the correct concrete language module,
- planner-first is the nominal path,
- `fallback_used = false` on the nominal path,
- the public success envelope is complete and coherent,
- and FR fails hard if the surface still looks English.

This document adopts those rules by reference.  
It does not weaken them, duplicate them incompletely, or replace them.

---

## 8. Multilingual readiness model

A language may exist in one of several readiness tiers.

### Tier 0 — declared

The language has an identifier, intended slot, or planned presence in the system.

### Tier 1 — compile-capable

A concrete language module exists and compiles.

### Tier 2 — runtime-loadable

The runtime can load the language.

### Tier 3 — routable

The public API can route requests to the language.

### Tier 4 — generates

The language returns non-empty surface output for required constructions.

### Tier 5 — construction-correct

Required constructions behave correctly for the language.

### Tier 6 — acceptance-ready

The language passes acceptance gates and evaluator checks for its target scope.

### Tier 7 — release-ready

The language satisfies the system’s deployment bar for its intended production context.

---

## 9. Tier interpretation rules

These tiers must be interpreted strictly.

### 9.1 Presence is not readiness

A language may be present in the repository while still being below acceptance-ready.

### 9.2 Routing is not correctness

Tier 3 does not imply language-correct output.

A routed language that still emits another language’s surface is not accepted and does not qualify as construction-correct.

### 9.3 Non-empty output is not acceptance

Tier 4 does not imply grammatical correctness, construction correctness, or public-contract readiness.

### 9.4 Acceptance is scope-bound

Acceptance applies only to the scope actually evaluated.

A language accepted for one narrow construction family is not automatically accepted for all constructions.

### 9.5 Marketing and reporting rule

No language may be described externally or internally beyond the tier it has actually earned.

---

## 10. Minimum onboarding gates for a new language

A new language is not integrated merely because a GF file exists.

Minimum gates include:

1. a concrete language module exists,
2. the language compiles,
3. the runtime loads it,
4. canonical generation routes to it,
5. the public success contract remains valid,
6. evaluator coverage exists for the target scope,
7. readiness metadata is updated,
8. the language is classified by tier.

Until these gates are satisfied, the language must not be represented as accepted.

---

## 11. Evaluator requirements

Evaluator and QA tooling must preserve the distinction between routing and correctness.

They must validate, at minimum where applicable:

- request language,
- resolved language,
- runtime path,
- fallback status,
- public response shape,
- surface-language plausibility,
- and scope-appropriate construction behavior.

For FR in the immediate cutover, the evaluator must fail hard if:

- request language is `fr`,
- runtime resolves to `WikiFre`,
- but the output still looks English.

This is not a soft failure, not a warning, and not a partial success.

---

## 12. Public response relevance to readiness

Readiness and acceptance cannot ignore the public success envelope.

A language cannot be treated as acceptance-ready for a publicly exposed generation scope unless the success response is coherent and stable.

At minimum, the accepted public success shape includes:

- `text`
- `lang_code`
- `construction_id`
- `renderer_backend`
- `fallback_used`
- `tokens`
- `debug_info`
- `generation_time_ms`

The presence of a string alone is not enough.

If a language produces text but cannot satisfy the public contract for that scope, it is not acceptance-ready for that scope.

---

## 13. Documentation and reporting rules

All readiness and acceptance reporting must preserve the correct layer of truth.

### 13.1 EN/FR gate reporting

EN/FR acceptance reporting must point to `EN_FR_bio_acceptance.md` as the operative gate.

### 13.2 Broader readiness reporting

Broader multilingual readiness reporting may cite this document for tier definitions and onboarding interpretation.

### 13.3 Status docs must not overclaim

Status documents must not present a language as accepted merely because it compiles, routes, or emits text.

### 13.4 No contradictory truth

If any status page, QA output, or documentation artifact contradicts the operative acceptance gate or the public contract, it must be corrected.

---

## 14. Relationship to other docs

This document is aligned with:

- `EN_FR_bio_acceptance.md`
- `multilingual_runtime_target.md`
- `en_fr_cutover_plan.md`
- `public_generation_response_contract.md`
- `construction_runtime_contract.md`
- `debug_info_contract.md`
- `public_vs_runtime_vs_frontend_boundaries.md`

Conflict rule:

- if the issue is EN/FR cutover acceptance, `EN_FR_bio_acceptance.md` wins,
- if the issue is runtime architecture, `multilingual_runtime_target.md` wins,
- if the issue is public success serialization, `public_generation_response_contract.md` wins,
- if the issue is multilingual readiness tiering, this document wins.

Any disagreement must be corrected immediately.

---

## 15. Final rule

There must be no path by which a language appears accepted while still failing the acceptance requirements for its declared scope.

If a language is routed successfully, compiles successfully, or emits text successfully, but still fails surface correctness, runtime truth, or public contract requirements, it is not accepted.

If the system cannot distinguish between presence, routing, generation, construction correctness, acceptance-ready status, and release-ready status, the readiness model is broken.
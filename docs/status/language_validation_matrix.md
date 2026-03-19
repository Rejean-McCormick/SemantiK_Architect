# Language Validation Matrix

Status: normative operational status document  
Owner: QA / Runtime / Grammar / API  
Scope: real validation state of languages at the runtime boundary  
Applies to: Everything Matrix reporting, runtime validation, EN/FR bio acceptance reporting, future-language readiness tracking

---

## 1. Purpose

This page records the **observed validation state** of each language at the runtime boundary.

It complements the Everything Matrix by adding:

* observed generation evidence,
* runtime-path evidence,
* construction-level correctness,
* contract-level validation,
* regression / evaluator status,
* and readiness tier classification.

This page exists to prevent the system from confusing:

* matrix presence with integration,
* compile success with language readiness,
* routing with language correctness,
* non-empty output with acceptance,
* and compatibility-path success with canonical-runtime success.

---

## 2. Relationship to other documents

This page is an **operational status document**.

It does **not** overrule architecture, contracts, migration locks, or acceptance gates.

### 2.1 Authoritative documents that outrank this page

The following documents remain authoritative over this page:

1. `docs/architecture/multilingual_runtime_target.md`
2. `docs/contracts/construction_runtime_contract.md`
3. `docs/contracts/public_generation_response_contract.md`
4. `docs/migration/en_fr_cutover_plan.md`
5. `docs/testing/EN_FR_bio_acceptance.md`
6. `docs/architecture/EN_FR_FINAL_PARALLEL_LOCKDOWN.md`

### 2.2 EN/FR gate rule

For EN/FR bio/person generation:

* `docs/testing/EN_FR_bio_acceptance.md` is the **operative release gate**.
* this page mirrors the latest verified state and evidence.
* if this page conflicts with EN/FR acceptance, this page is stale and must be updated.

### 2.3 Readiness-model rule

`docs/testing/en_fr_acceptance_and_multilingual_readiness.md` remains authoritative for the broader multilingual readiness model and tier vocabulary.

This page applies that readiness model to observed runtime evidence.

---

## 3. Matrix model used by this page

The matrix model used across the repository is organized into four zones:

* RGL / Logic
* Lexicon / Data
* Application / Use-case readiness
* QA / Verification

The canonical metrics are:

* `CAT`
* `NOUN`
* `PARA`
* `GRAM`
* `SYN`
* `SEED`
* `CONC`
* `WIDE`
* `SEM`
* `PROF`
* `ASST`
* `ROUT`
* `BIN`
* `TEST`

All metric values are recorded on a `0..10` scale.

These are the same matrix concepts used by repository orchestration and the frontend matrix UI.

---

## 4. Canonical matrix columns

### 4.1 Zone A — RGL / Logic

| Metric | Meaning                   |
| ------ | ------------------------- |
| `CAT`  | Category definitions      |
| `NOUN` | Noun / morphology support |
| `PARA` | Paradigms                 |
| `GRAM` | Grammar core              |
| `SYN`  | Syntax API                |

### 4.2 Zone B — Lexicon / Data

| Metric | Meaning                    |
| ------ | -------------------------- |
| `SEED` | Core seed vocabulary       |
| `CONC` | Domain concepts            |
| `WIDE` | Wide import / bulk lexicon |
| `SEM`  | Semantic alignment         |

### 4.3 Zone C — Application / Use-case readiness

| Metric | Meaning                       |
| ------ | ----------------------------- |
| `PROF` | Bio-ready                     |
| `ASST` | Assistant-ready               |
| `ROUT` | Routing / topology configured |

### 4.4 Zone D — QA / Verification

| Metric | Meaning                                |
| ------ | -------------------------------------- |
| `BIN`  | Present in PGF / binary path available |
| `TEST` | Regression / evaluator status          |

---

## 5. Readiness model

This page uses the canonical multilingual readiness model.

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

### Readiness rule

A language must never be advertised beyond the tier it has actually earned.

### Core rule

`ROUT > 0` or “Tier 3 — routable” does **not** imply language correctness or acceptance.

---

## 6. Canonical status recording model

For each language and construction family, this page records **both**:

1. matrix metrics,
2. observed runtime validation evidence.

The canonical status payload for a language / construction family must include at least:

* `lang_code`
* `construction_family`
* `target_endpoint`
* `readiness_tier`
* `observed_runtime_path`
* `resolved_language`
* `renderer_backend`
* `fallback_used`
* `public_contract_valid`
* `surface_language_status`
* `surface_result`
* `judge_status`
* `last_verified_on`
* `verified_by`
* `notes`

Recommended additional fields:

* `construction_id`
* `tokens_valid`
* `generation_time_ms_present`
* `debug_parity_valid`
* `compat_aliases_validated`
* `health_status`
* `matrix_snapshot_ref`
* `evaluator_ref`

---

## 7. Validation rules

A language should only be marked as validated for a construction family when **all** of the following are true:

1. the language is discoverable in the matrix,
2. the language compiles into the PGF or is otherwise available through the configured runtime,
3. runtime health checks pass,
4. a real generation call returns non-empty text,
5. the returned text is correct for the target language,
6. the returned text is correct for the target construction family,
7. the public response contract is valid,
8. the observed runtime path is recorded truthfully,
9. fallback state is explicit,
10. judge / regression evidence exists for the relevant construction family,
11. the readiness tier recorded here is consistent with the observed evidence.

Matrix presence alone is **not** enough.

Compile success alone is **not** enough.

Routing alone is **not** enough.

Non-empty output alone is **not** enough.

---

## 8. Contract validation rules

Validation on this page must follow the canonical public success envelope.

For accepted success cases, the response must contain:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `tokens`
* `debug_info`
* `generation_time_ms`

The following invariants must hold:

* `text` is authoritative,
* `lang_code` identifies the returned surface language,
* `construction_id` is explicit on the nominal path,
* `renderer_backend` is explicit on the nominal path,
* `fallback_used` is explicit,
* `tokens` correspond to the final text,
* `generation_time_ms` is top-level and authoritative,
* `debug_info` must not contradict top-level fields.

For runtime validation, at minimum the following `debug_info` values must remain visible where applicable:

* `runtime_path`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `lang_code`

Recommended additional observability includes:

* `resolved_language`
* `attempted_backends`
* `selected_backend`
* `backend_trace`
* `lexical_resolution`
* `warnings`

---

## 9. Runtime-path rules

This page must record the **actual observed runtime path**.

Allowed examples include:

* `planner_first`
* `compatibility_shim`
* `legacy_direct_frame`

### Rules

* `planner_first` is the canonical target path.
* compatibility paths may be recorded while migration exists.
* compatibility-path success must not be recorded as equivalent to canonical planner-first success.
* if a case succeeds only through compatibility fallback, that fact must be explicit in both status notes and readiness interpretation.

---

## 10. Automatic fail rules

Any of the following is an automatic validation failure for the affected language / construction family.

### 10.1 Contract failures

* missing `construction_id`
* missing `renderer_backend`
* missing `fallback_used`
* missing `debug_info`
* missing or invalid `lang_code`
* top-level and `debug_info` contradiction on canonical shared fields
* missing `generation_time_ms` on a claimed nominal planner-first success
* missing `tokens` on a claimed nominal planner-first success without an approved explicit exception

### 10.2 Runtime failures

* claimed planner-first success with `runtime_path` missing
* claimed planner-first success with incomplete nominal metadata
* silent backend fallback
* silent construction drift
* backend-specific hidden contract required outside the canonical runtime contract
* compatibility-path success recorded as though it were canonical-runtime success

### 10.3 Language failures

* requested language differs from returned surface language without explicit, approved fallback semantics
* resolved concrete language is correct but the surface output is still another language
* lexical material for the target language is incorrect for the tested construction family

### 10.4 EN/FR-specific hard failure

For EN/FR bio/person validation:

* EN is a failure if the accepted English case is not actually English.
* FR is a failure if the request is `fr`, the path resolves to `WikiFre`, and the output still looks English.

A routed-but-English French result is a **hard failure**.

---

## 11. EN/FR bio/person interpretation rule

This page may record EN/FR bio/person status, but the operative pass/fail gate remains:

* `docs/testing/EN_FR_bio_acceptance.md`

For EN/FR bio/person, this page must only mark a record as acceptance-ready or release-ready when **all** of the following are true:

* request language is correct,
* resolved concrete language is correct,
* runtime path is `planner_first`,
* `fallback_used = false`,
* public contract is valid,
* surface language is correct,
* profession/nationality lexicalization are correct for the target language,
* evaluator / regression evidence passes,
* the recorded readiness tier matches that evidence.

For FR specifically:

* “routed to `WikiFre` but surfaced English” is never acceptable.
* “non-empty French response envelope” is not enough.
* “compatibility path happened to return something” is not enough.

---

## 12. Canonical evidence to archive per verification run

For each verification run that updates this page, archive at minimum:

* commit SHA
* PGF build timestamp
* matrix snapshot reference
* health output reference
* EN public API response JSON where applicable
* FR public API response JSON where applicable
* evaluator / judge summary
* observed runtime path
* fallback annotations
* verifier identity
* verification date

This page may summarize the evidence, but the evidence itself should remain archivable and reproducible.

---

## 13. Normal validation sequence

The canonical validation sequence for this repository is:

1. refresh Everything Matrix,
2. validate lexicon,
3. compile PGF,
4. validate health,
5. run at least one real generation call,
6. run judge / regression,
7. record observed runtime path and surface result,
8. update this page.

A language is not truly integrated until it **generates real text** and that text is validated for correctness.

---

## 14. Matrix / readiness interpretation guide

This page should be interpreted using both the numeric matrix and the readiness tier.

### 14.1 Numeric matrix says where supporting assets stand

The `0..10` matrix metrics describe support strength across:

* grammar logic,
* lexicon/data,
* application routing/readiness,
* and QA artifacts.

### 14.2 Readiness tier says what the language has actually earned

The readiness tier records the highest validated operational state reached by the language for the relevant scope.

### 14.3 Conflicts are resolved conservatively

If matrix metrics and runtime evidence disagree:

* runtime evidence wins for readiness interpretation,
* acceptance docs win for release-gate interpretation,
* this page must record the lower safe interpretation until the conflict is resolved.

Examples:

* high `ROUT` with wrong-language output is **not** acceptance-ready,
* high `BIN` with no real generation evidence is **not** acceptance-ready,
* high `PROF` with compatibility-only success is **not** canonical-runtime success.

---

## 15. Operational snapshot rules

The “current validation snapshot” section below must always reflect the **latest verified observed state**.

It must not be used for:

* target-state aspirations,
* planned future milestones,
* unverified claims,
* or preemptive “should be passing” statements.

If the last verified state is unknown or stale, mark it as stale explicitly.

---

## 16. Current validation snapshot

**Last verified:** update on each real verification run  
**Verification scope:** update on each real verification run

### 16.1 Biography generation (`bio`, `entity.person.v2`)

| Lang | Construction family | Endpoint              | Readiness tier | Observed runtime path | Resolved language | Renderer backend | Fallback used | Public contract valid | Surface language status | Judge / regression | Status notes |
| ---- | ------------------- | --------------------- | -------------- | --------------------- | ----------------- | ---------------- | ------------- | --------------------- | ----------------------- | ------------------ | ------------ |
| `en` | biography lead      | `/api/v1/generate/en` | `update`       | `update`              | `update`          | `update`         | `update`      | `update`              | `update`                | `update`           | `update from observed evidence only` |
| `fr` | biography lead      | `/api/v1/generate/fr` | `update`       | `update`              | `update`          | `update`         | `update`      | `update`              | `update`                | `update`           | `update from observed evidence only` |

### 16.2 Snapshot interpretation rules

When updating the EN/FR rows above:

* do not mark EN or FR beyond the readiness tier actually earned,
* do not collapse compatibility-path success into canonical-runtime success,
* do not count FR as passing if it still surfaces English,
* do not count non-empty text as acceptance,
* do not let this page disagree with `EN_FR_bio_acceptance.md`.

---

## 17. What counts as “done” for a language record

A language / construction-family record is “done” for a verification cycle only when all of the following are present:

* matrix context exists,
* runtime evidence exists,
* surface-language correctness is evaluated,
* public contract validity is evaluated,
* runtime path is recorded,
* fallback state is recorded,
* judge / regression status is recorded,
* readiness tier is explicitly assigned,
* notes explain any temporary compatibility or blocking condition.

---

## 18. Pending-validation section rules

Use a separate pending section for planned work.

Pending work must never be mixed into the verified snapshot.

### Template

#### Pending validations

##### `en`

* `...`

##### `fr`

* `...`

##### `xx`

* `...`

---

## 19. Template for new languages

Use this template when adding a new language / construction-family status row.

| Lang | Construction family | Endpoint              | Readiness tier | Observed runtime path | Resolved language | Renderer backend | Fallback used | Public contract valid | Surface language status | Judge / regression | Last verified on | Verified by | Notes |
| ---- | ------------------- | --------------------- | -------------- | --------------------- | ----------------- | ---------------- | ------------- | --------------------- | ----------------------- | ------------------ | ---------------- | ----------- | ----- |
| `xx` | `...`               | `/api/v1/generate/xx` | `Tier 0..7`    | `...`                 | `...`             | `...`            | `...`         | `...`                 | `...`                   | `...`              | `YYYY-MM-DD`     | `...`       | `...` |

---

## 20. Final rule

This page is successful only when it tells the truth about language readiness more strictly than “it compiled” or “it routed”.

If a language can still appear healthy here while:

* inheriting another language’s surface behavior,
* succeeding only through hidden compatibility behavior,
* or lacking the canonical planner-first/runtime/public-contract evidence,

then this page is wrong and must be corrected.
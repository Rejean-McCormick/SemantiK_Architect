# Language Validation Matrix

This page records the **real validation state** of each language at the runtime boundary. It complements the Everything Matrix by adding **observed generation evidence**, **construction-level status**, and **regression status**. The matrix model used across the repo is organized into four zones — RGL, Lexicon, Application, and QA — with the canonical metrics `CAT`, `NOUN`, `PARA`, `GRAM`, `SYN`, `SEED`, `CONC`, `WIDE`, `SEM`, `PROF`, `ASST`, `ROUT`, `BIN`, and `TEST`, all on a `0..10` scale.   

The normal integration path in this repo is: **Refresh Everything Matrix → Validate lexicon → Compile PGF → Validate health → Generate one real sentence → Run Judge / regression**. A language is not truly integrated until it **generates a sentence**, and robust validation is expected to include gold-standard / judge checks rather than stopping at compile success.    

---

## 1. Canonical columns

### Zone A — RGL / Logic

| Metric | Meaning                   |
| ------ | ------------------------- |
| `CAT`  | Category definitions      |
| `NOUN` | Noun / morphology support |
| `PARA` | Paradigms                 |
| `GRAM` | Grammar core              |
| `SYN`  | Syntax API                |

### Zone B — Lexicon / Data

| Metric | Meaning                    |
| ------ | -------------------------- |
| `SEED` | Core seed vocabulary       |
| `CONC` | Domain concepts            |
| `WIDE` | Wide import / bulk lexicon |
| `SEM`  | Semantic alignment         |

### Zone C — Application / Use-case readiness

| Metric | Meaning                       |
| ------ | ----------------------------- |
| `PROF` | Bio-ready                     |
| `ASST` | Assistant-ready               |
| `ROUT` | Routing / topology configured |

### Zone D — QA / Verification

| Metric | Meaning                                |
| ------ | -------------------------------------- |
| `BIN`  | Present in PGF / binary path available |
| `TEST` | Regression / gold-standard status      |

These are the same matrix concepts used by the orchestrator and the frontend matrix UI.   

---

## 2. Validation rules

A language should only be marked **validated** for a construction family when all of the following are true:

1. the language is discoverable in the matrix,
2. the language compiles into the PGF or is otherwise available through the configured runtime,
3. health checks pass,
4. a real generation call returns non-empty text,
5. the returned text is correct for the target language and construction,
6. judge / regression evidence exists for the relevant construction family,
7. the observed runtime path is recorded (`planner-first` or temporary legacy compatibility path).   

Matrix presence alone is **not** enough. Runtime validation must include actual output quality and regression evidence.  

---

## 3. Runtime-status vocabulary

| Status             | Meaning                                                          |
| ------------------ | ---------------------------------------------------------------- |
| `DISCOVERED`       | Language exists in repo / matrix inputs                          |
| `BUILDABLE`        | Build path exists and expected assets are present                |
| `RUNNABLE`         | Health and runtime can produce text                              |
| `PARTIAL`          | Produces text, but validation is incomplete or path is temporary |
| `BLOCKED`          | Routing/build exists but output is incorrect or incomplete       |
| `VALIDATED`        | Correct runtime output with regression evidence                  |
| `PRODUCTION_READY` | Validated on the canonical runtime path with regression coverage |

---

## 4. Canonical evidence to record per language

For each language / construction family, record:

* `construction_family`
* `target_endpoint`
* `observed_runtime_path`
* `resolved_language`
* `renderer_backend`
* `fallback_used`
* `surface_result`
* `judge_status`
* `last_verified_on`
* `verified_by`
* `notes`

This aligns with the canonical runtime/result contracts around `construction_id`, `renderer_backend`, `surface_result`, `debug_info`, and explicit fallback observability.   

---

## 5. Current validation snapshot

*Last verified: 2026-03-16*

### Biography generation (`bio`, `entity.person.v2`)

| Lang | Construction family | Endpoint              | Observed runtime path | Resolved language | Surface result                                         | Compat aliases                                     | Judge / regression    | Status    | Notes                                                                                     |
| ---- | ------------------- | --------------------- | --------------------- | ----------------- | ------------------------------------------------------ | -------------------------------------------------- | --------------------- | --------- | ----------------------------------------------------------------------------------------- |
| `en` | biography lead      | `/api/v1/generate/en` | `legacy_direct_frame` | `WikiEng`         | Correct English output observed                        | `bio` and `entity.person.v2` both observed working | Not yet recorded here | `PARTIAL` | Runnable and semantically correct, but not yet validated on the planner-first target path |
| `fr` | biography lead      | `/api/v1/generate/fr` | `legacy_direct_frame` | `WikiFre`         | Incorrect surface observed: output remained in English | Routing works                                      | Not yet recorded here | `BLOCKED` | Language resolution succeeds, but French surface realization is not yet validated         |

### Interpretation

* `en` biography generation is currently **working on the compatibility path**, not yet fully validated as planner-first production runtime.
* `fr` biography generation is currently **not validated**, because the runtime returns English surface text even when the request is routed to `fr` / `WikiFre`.
* Compatibility aliases for biography-shaped inputs are functioning at the request boundary, but alias acceptance is not the same as language validation. The request layer explicitly accepts legacy aliases and normalizes them to canonical bio semantics. 

---

## 6. What counts as “done” for EN/FR bio

`en` or `fr` should only be moved to `VALIDATED` for biography generation when all of the following are present:

* one or more successful real generation calls,
* correct target-language surface realization,
* stable `construction_id` / runtime metadata,
* explicit runtime-path recording,
* no hidden fallback,
* judge / regression evidence for the biography family,
* status refreshed in the matrix after validation.   

`PRODUCTION_READY` is stricter than `VALIDATED`: it requires the **canonical runtime path**, not only a temporary compatibility path. During migration, direct engine generation may exist as a temporary fallback, but the planner-first runtime is the authoritative target and fallback use must remain explicit.  

---

## 7. Update procedure

Update this page only after running the normal sequence:

1. refresh Everything Matrix,
2. validate lexicon,
3. compile PGF,
4. validate health,
5. run at least one real generation call,
6. run judge / regression where applicable,
7. record observed runtime path and surface result,
8. update status table.  

---

## 8. Pending next validations

### EN

* Record judge / regression evidence for biography generation
* Re-test on planner-first runtime when configured
* Promote from `PARTIAL` only after runtime-path and regression confirmation

### FR

* Fix French surface realization
* Re-run `/api/v1/generate/fr`
* Add judge / regression evidence
* Promote from `BLOCKED` only after correct French output is observed

---

## 9. Status template for new languages

| Lang | Construction family | Endpoint              | Observed runtime path | Resolved language | Surface result | Compat aliases | Judge / regression | Status                                                                                 | Notes |
| ---- | ------------------- | --------------------- | --------------------- | ----------------- | -------------- | -------------- | ------------------ | -------------------------------------------------------------------------------------- | ----- |
| `xx` | `...`               | `/api/v1/generate/xx` | `...`                 | `...`             | `...`          | `...`          | `...`              | `DISCOVERED / BUILDABLE / RUNNABLE / PARTIAL / BLOCKED / VALIDATED / PRODUCTION_READY` | `...` |

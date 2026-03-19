# EN/FR Bio Acceptance

Status: normative acceptance document  
Owner: QA / Runtime / Grammar / API  
Scope: release-blocking acceptance criteria for EN/FR bio/person generation on the planner-first runtime path

---

## 1. Purpose

This document defines the operative release gate for English (`en`) and French (`fr`) bio/person generation.

It exists to prevent the system from confusing:

- routing with correctness,
- compile success with readiness,
- non-empty output with language success,
- compatibility behavior with target-state success,
- and debug-only metadata with a valid nominal public contract.

This is the final proof layer for EN/FR bio/person generation.
It does not replace the architecture document, the cutover plan, or the public response contract.
It applies those documents as a concrete acceptance gate for the EN/FR vertical slice.

---

## 2. Governing precedence

This document is governed by the following precedence rules:

1. `docs/architecture/multilingual_runtime_target.md` defines the target architecture.
2. `docs/architecture/EN_FR_FINAL_PARALLEL_LOCKDOWN.md` defines the lock rules and conflict-resolution policy for the final cutover.
3. `docs/contracts/public_generation_response_contract.md` defines the canonical public success envelope.
4. `docs/contracts/construction_runtime_contract.md` defines the canonical runtime contract.
5. `docs/migration/en_fr_cutover_plan.md` defines execution sequencing and completion gates.
6. This document defines the operative EN/FR release gate.
7. `docs/testing/en_fr_acceptance_and_multilingual_readiness.md` remains the broader readiness model and multilingual template.
8. `docs/2-Technical-Reference/CURRENT_RUNTIME_STATUS.md` must not contradict any of the documents above.

If any lower-precedence document conflicts with a higher-precedence document, the higher-precedence document wins.

---

## 3. Acceptance statement

EN and FR are accepted only when they pass a full vertical slice:

- canonical bio/person input,
- planner-first runtime,
- language-specific realization,
- coherent public response contract,
- explicit runtime diagnostics,
- evaluator success,
- and correct surface language.

A language is **not accepted** because it:

- exists in GF,
- compiles,
- loads,
- routes,
- or emits any non-empty text.

---

## 4. Normative acceptance variables

These variables are normative and must remain conceptually consistent across runtime, tests, QA tools, and docs.

### 4.1 Runtime variables

- `EXPECTED_PRIMARY_RUNTIME = "planner_first"`
- `LEGACY_SUCCESS_COUNTS_AS_ACCEPTED = false`
- `LEGACY_FALLBACK_COUNTS_AS_NOMINAL_SUCCESS = false`

### 4.2 EN variables

- `EN_REQUEST_LANG = "en"`
- `EN_EXPECTED_GF_LANGUAGE = "WikiEng"`
- `EN_SURFACE_LANGUAGE = "english"`

### 4.3 FR variables

- `FR_REQUEST_LANG = "fr"`
- `FR_EXPECTED_GF_LANGUAGE = "WikiFre"`
- `FR_SURFACE_LANGUAGE = "french"`
- `FR_SURFACE_MUST_NOT_LOOK_ENGLISH = true`

### 4.4 Public contract variables

- `REQUIRED_PUBLIC_TEXT = true`
- `REQUIRED_PUBLIC_LANG_CODE = true`
- `REQUIRED_PUBLIC_CONSTRUCTION_ID = true` on nominal path
- `REQUIRED_PUBLIC_RENDERER_BACKEND = true` on nominal path
- `REQUIRED_PUBLIC_FALLBACK_USED = true`
- `REQUIRED_PUBLIC_TOKENS = true`
- `REQUIRED_PUBLIC_DEBUG_INFO = true`
- `REQUIRED_PUBLIC_GENERATION_TIME_MS = true`

### 4.5 Metadata parity variables

- `TOP_LEVEL_AND_DEBUG_LANG_CODE_MUST_MATCH = true`
- `TOP_LEVEL_AND_DEBUG_FALLBACK_MUST_MATCH = true`
- `TOP_LEVEL_AND_DEBUG_BACKEND_MUST_MATCH = true` when both are present
- `TOP_LEVEL_AND_DEBUG_CONSTRUCTION_ID_MUST_MATCH = true` when both are present
- `TOP_LEVEL_TIME_IS_AUTHORITATIVE = true`

---

## 5. Acceptance scope

This document covers:

- `POST /api/v1/generate/{lang_code}`,
- EN bio/person generation,
- FR bio/person generation,
- planner-first runtime behavior for these requests,
- public success contract for these requests,
- evaluator behavior for these requests,
- and language-surface correctness for these requests.

This document does not claim acceptance for:

- all languages,
- all constructions,
- all backends in all contexts,
- all historical compatibility paths,
- or full multilingual readiness beyond the EN/FR scope.

---

## 6. Canonical entrypoint

Primary endpoint under test:

```http
POST /api/v1/generate/{lang_code}
````

Rules:

* `{lang_code}` is authoritative at the public boundary,
* accepted values for this document are `en` and `fr`,
* URL language and payload language must match if both are present,
* language compatibility must be validated through the public API, not only through internal tests.

Examples:

* `/generate/en` + payload `lang=en` → valid
* `/generate/fr` + payload `lang=fr` → valid
* `/generate/fr` + payload `lang=en` → fail
* missing language everywhere → fail

---

## 7. Canonical input contract for EN/FR bio acceptance

### 7.1 Canonical semantic shape

The acceptance target is a normalized bio/person frame carrying at least:

* subject identity,
* profession,
* nationality,
* optional gender,
* optional metadata,
* optional lexical provenance.

Example canonical shape:

```json
{
  "frame_type": "bio",
  "subject": {
    "name": "Marie Curie",
    "qid": "Q7186",
    "gender": "f"
  },
  "properties": {
    "profession": "physicist",
    "nationality": "Polish"
  },
  "meta": {
    "register": "neutral"
  }
}
```

### 7.2 Compatibility aliases at the boundary

The public boundary may continue to accept compatibility aliases such as:

* `bio`
* `biography`
* `entity.person`
* `entity_person`
* `person`
* `entity.person.v1`
* `entity.person.v2`

However:

* acceptance is awarded only after normalization,
* compatibility ends at normalization,
* downstream planner/runtime code must not depend on legacy payload quirks,
* compatibility-path success does not count as nominal planner-first acceptance.

---

## 8. Canonical runtime expectations

For migrated EN/FR bio/person generation, the authoritative path is:

1. request normalization,
2. frame-to-plan bridge,
3. planner,
4. lexical resolution,
5. realizer,
6. response mapping.

The acceptance path for EN/FR bio/person generation is **planner-first**.

Legacy direct frame-to-engine generation may remain temporarily as explicit compatibility fallback while migration cleanup is still being completed, but it is not a target-state success condition.

---

## 9. Canonical runtime result expectations

The nominal planner-first runtime result handed to the response mapper must already be mapper-ready.

Required top-level runtime fields on nominal path:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `tokens`
* `debug_info`
* `generation_time_ms`

Required `debug_info` keys on nominal planner-first success:

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
* `lexical_resolution`
* `backend_trace`
* `warnings`

Parity rule:

* when the same semantic field exists both top-level and inside `debug_info`, the values must match.

No nominal-null rule:

* `construction_id` must not be null,
* `renderer_backend` must not be null,
* `fallback_used` must not be omitted,
* `debug_info` must not be omitted.

The mapper may serialize and normalize.
It must not be the place where nominal planner-first truth first appears.

---

## 10. EN acceptance criteria

EN is accepted only when all of the following are true.

### 10.1 Routing

* request language is `en`
* runtime resolves to `WikiEng`

### 10.2 Runtime path

* nominal path is planner-first
* `runtime_path = "planner_first"`
* `fallback_used = false`

### 10.3 Surface

* output is non-empty
* output is English
* output reflects the intended bio/person meaning

### 10.4 Public contract

The public success envelope contains:

* `text`
* `lang_code = "en"`
* `construction_id`
* `renderer_backend`
* `fallback_used = false`
* `tokens`
* `debug_info`
* `generation_time_ms`

### 10.5 Metadata consistency

* `debug_info.lang_code = "en"`
* `debug_info.fallback_used = false`
* `debug_info.runtime_path = "planner_first"`

### 10.6 Negative acceptance rule

EN is not accepted if it only succeeds through legacy fallback.

---

## 11. FR acceptance criteria

FR is accepted only when all of the following are true.

### 11.1 Routing

* request language is `fr`
* runtime resolves to `WikiFre`

### 11.2 Runtime path

* nominal path is planner-first
* `runtime_path = "planner_first"`
* `fallback_used = false`

### 11.3 Surface

* output is non-empty
* output is French
* output does not leak English literals from shared layers
* output reflects the intended bio/person meaning

### 11.4 Public contract

The public success envelope contains:

* `text`
* `lang_code = "fr"`
* `construction_id`
* `renderer_backend`
* `fallback_used = false`
* `tokens`
* `debug_info`
* `generation_time_ms`

### 11.5 Metadata consistency

* `debug_info.lang_code = "fr"`
* `debug_info.fallback_used = false`
* `debug_info.runtime_path = "planner_first"`

### 11.6 Mandatory failure rule

FR must fail acceptance if:

* request language is `fr`,
* runtime resolves to `WikiFre`,
* but the output still looks English.

This is not a soft failure and not a partial success.
It is a hard acceptance failure.

### 11.7 Negative acceptance rule

FR is not accepted if it only succeeds through legacy fallback.

---

## 12. Public response acceptance

For EN and FR, the accepted success response shape is:

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
```

Contract rules:

* `text` is authoritative,
* `lang_code` identifies the returned surface language,
* `construction_id` is explicit on the nominal path,
* `renderer_backend` is explicit on the nominal path,
* `fallback_used` is explicit,
* `tokens` correspond to final text,
* `generation_time_ms` is top-level and authoritative,
* `debug_info` must not contradict top-level fields.

---

## 13. Lexical-resolution acceptance requirements

Lexical resolution must be explicit and testable.

For EN/FR bio/person acceptance, this includes at least:

* profession lexicalization,
* nationality lexicalization,
* provenance visibility where available,
* deterministic fallback behavior where lexical lookup fails.

Lexical resolution must preserve:

* `construction_id`
* `lang_code`
* slot identity
* semantic role intent

Lexical resolution must not:

* silently reinterpret slots,
* silently replace semantic meaning,
* hide raw-string fallback,
* bypass provenance when provenance exists.

If the French path produces English lexical material for the same bio case without explicit, approved fallback trace, acceptance fails.

---

## 14. Cross-language semantic equivalence requirements

For the same normalized bio input and the same generation options:

* EN and FR must preserve the same subject identity,
* EN and FR must preserve the same profession meaning,
* EN and FR must preserve the same nationality meaning,
* EN and FR must preserve the same construction semantics,
* EN and FR may differ in morphology, article use, agreement, and word order,
* EN and FR must not diverge in truth conditions.

Semantic equivalence does not require token-by-token literal correspondence.
It requires preserved semantic intent.

---

## 15. Mandatory test suites

EN/FR bio acceptance is awarded only when all required suites pass.

### 15.1 Suite A — Public API canonical bio tests

Run public API tests for:

* `POST /api/v1/generate/en`
* `POST /api/v1/generate/fr`

Required cases:

1. canonical `bio` payload,
2. canonical payload with explicit metadata,
3. canonical payload with lexicalized profession/nationality,
4. response-shape validation,
5. `debug_info` validation,
6. token alignment validation.

### 15.2 Suite B — Legacy alias normalization tests

Required input alias coverage:

* `bio`
* `biography`
* `entity.person`
* `entity_person`
* `person`
* `entity.person.v1`
* `entity.person.v2`

All of these must normalize to the same bio semantics.

This suite validates compatibility only.
It does not replace planner-first acceptance.

### 15.3 Suite C — Planner-first runtime tests

Required assertions:

* runtime path is `planner_first`,
* fallback is `false`,
* `construction_id` is canonical,
* `renderer_backend` is explicit,
* lexical resolution is visible when applied,
* slot keys include at least `subject`, `profession`, `nationality`.

### 15.4 Suite D — Fallback behavior tests

If fallback is triggered, tests must verify:

* `fallback_used = true`,
* original backend is traceable,
* final backend is traceable,
* fallback reason is present,
* `construction_id` is preserved,
* `lang_code` is preserved,
* semantics are preserved.

Silent fallback is an automatic fail.

### 15.5 Suite E — Gold regression tests

A gold-standard regression suite is mandatory for EN and FR.

Minimum required coverage:

* at least 3 person records,
* each record with gold bios for both `en` and `fr`,
* each record carrying profession and nationality data,
* each record usable by automated evaluation.

Recommended starter records:

* Marie Curie
* Ada Lovelace
* Alan Turing

---

## 16. Gold data requirements

Each gold record should include:

* stable identifier (`id` or `qid`),
* display label,
* gender where relevant to the tested language behavior,
* profession lemma(s),
* nationality lemma(s),
* `gold_bios` map keyed by language code.

Example record shape:

```json
{
  "id": "Q7186",
  "label": "Marie Curie",
  "gender": "f",
  "profession_lemmas": ["physicist"],
  "nationality_lemmas": ["Polish"],
  "gold_bios": {
    "en": "Marie Curie was a Polish physicist.",
    "fr": "Marie Curie était une physicienne polonaise."
  }
}
```

Gold strings must be version-controlled and reviewed.
If generation options change tense or register, the gold set must specify those options explicitly.

---

## 17. Acceptance commands

Use the repository validation workflow expected for EN/FR language acceptance.

### 17.1 Required validation flow

1. refresh matrix,
2. validate lexicon,
3. compile PGF,
4. run language health,
5. run real EN/FR generation,
6. run evaluator/judge,
7. refresh matrix again.

### 17.2 Canonical commands

```bash
build_index --langs en fr --regen-rgl --regen-lex --regen-app --regen-qa --verbose
lexicon_coverage --lang en --include-files
lexicon_coverage --lang fr --include-files
compile_pgf --langs en fr --verbose
language_health --mode both --langs en fr --json --verbose
run_judge .
build_index --langs en fr --regen-rgl --regen-lex --regen-app --regen-qa --verbose
```

### 17.3 Public API smoke calls

Canonical English call:

```bash
curl -X POST http://localhost:8000/api/v1/generate/en \
  -H "Content-Type: application/json" \
  -d '{
    "frame_type": "bio",
    "name": "Marie Curie",
    "profession": "physicist",
    "nationality": "Polish",
    "gender": "f"
  }'
```

Canonical French call:

```bash
curl -X POST http://localhost:8000/api/v1/generate/fr \
  -H "Content-Type: application/json" \
  -d '{
    "frame_type": "bio",
    "name": "Marie Curie",
    "profession": "physicist",
    "nationality": "Polish",
    "gender": "f"
  }'
```

Compatibility alias call:

```bash
curl -X POST http://localhost:8000/api/v1/generate/en \
  -H "Content-Type: application/json" \
  -d '{
    "frame_type": "entity.person.v2",
    "subject": {
      "name": "Alan Turing",
      "profession": "mathematician",
      "nationality": "British"
    }
  }'
```

---

## 18. Mandatory pass conditions

EN/FR bio acceptance passes only if all conditions below are satisfied.

### 18.1 Public response pass conditions

For every accepted EN/FR bio case:

* HTTP status is success,
* `text` is non-empty,
* `lang_code` matches the requested language,
* `construction_id` is present,
* `renderer_backend` is present,
* `fallback_used` is present,
* `debug_info` is present,
* `generation_time_ms` is present,
* `tokens` are aligned with the returned text.

### 18.2 Runtime pass conditions

For planner-first acceptance:

* `runtime_path == "planner_first"`
* `fallback_used == false`
* selected construction is canonical
* selected backend is explicit
* attempted backends are explicit or inferable
* lexical resolution is explicit when applied

### 18.3 English pass conditions

* output is English,
* profession is English,
* nationality is English,
* semantics match the gold target for the configured options.

### 18.4 French pass conditions

* output is French,
* profession is French,
* nationality is French,
* semantics match the gold target for the configured options,
* no English scaffold remains.

### 18.5 Cross-language pass conditions

For the same semantic record and options:

* EN and FR preserve the same subject,
* EN and FR preserve the same semantic classification,
* EN and FR preserve the same profession and nationality meaning,
* EN and FR preserve the same canonical runtime construction identity.

---

## 19. Automatic fail conditions

Any of the following is an automatic fail.

### 19.1 Contract failures

* missing `construction_id`
* missing `renderer_backend`
* missing `fallback_used`
* missing `debug_info`
* missing `generation_time_ms`
* missing or invalid `lang_code`
* top-level/debug parity mismatch on canonical shared fields
* hidden planner-facing contract required by one backend only

### 19.2 Runtime failures

* migrated bio generation uses `legacy_direct_frame` in the main acceptance suite
* fallback occurred but was not explicitly annotated
* renderer silently changed construction semantics
* runtime consumed raw payload quirks below normalization
* mapper repaired nominal planner-first nulls instead of serializing a valid runtime result

### 19.3 English failures

* English request returns non-English surface text
* English request returns wrong semantic classification
* English lexicalization is unresolved without explicit fallback trace

### 19.4 French failures

* French request returns English scaffold such as `is`, `is a`, or other obvious English clause packaging
* French request returns non-French profession/nationality realization without explicit, approved fallback trace
* French request is routed successfully but surface text is still English

### 19.5 Regression failures

* gold example similarity falls below the project threshold
* judge or evaluator fails
* matrix, build, or health state regresses after a change
* one language passes only through compatibility fallback while the other passes planner-first

---

## 20. Compatibility quarantine

Legacy compatibility tests must remain separate from release acceptance.

Allowed temporary suite:

* prove that old client payloads still normalize correctly,
* prove that fallback paths remain explicit,
* prove that compatibility behavior is observable.

Not allowed:

* counting a compatibility-path success as planner-first acceptance,
* counting a legacy-direct FR sentence as evidence that French bio generation is robust,
* counting a non-empty output as language acceptance.

---

## 21. Evidence to archive for every acceptance run

For each acceptance run, archive:

* commit SHA,
* PGF build timestamp,
* matrix snapshot before and after,
* language health output,
* EN public API response JSON,
* FR public API response JSON,
* gold/judge summary,
* failing diffs if any,
* backend/runtime path used,
* fallback annotations if any.

---

## 22. Definition of done

EN/FR bio/person generation is considered accepted only when:

1. canonical bio inputs and compatibility aliases both normalize correctly,
2. planner-first runtime is used for migrated bio/person generation,
3. EN and FR share the same canonical construction semantics,
4. French generates actual French surface text,
5. English generates actual English surface text,
6. lexical resolution is explicit and testable,
7. public response fields are stable and complete,
8. fallback is explicit and machine-readable,
9. gold examples exist for both languages,
10. judge and evaluator pass,
11. matrix and health checks remain green after the acceptance run.

If any of these conditions is false, EN/FR bio/person acceptance is not complete.

---

## 23. Final rule

EN/FR bio/person acceptance is not awarded for “some sentence came out”.

It is awarded only when:

* semantics are preserved,
* contracts are aligned,
* runtime path is correct,
* diagnostics are explicit,
* French is truly French,
* English is truly English,
* and regressions are mechanically catchable.


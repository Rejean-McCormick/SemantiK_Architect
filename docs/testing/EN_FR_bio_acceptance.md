# EN/FR Bio Acceptance

Status: normative  
Owner: Runtime / Grammar / API  
Scope: release-blocking acceptance criteria for biography generation in English (`en`) and French (`fr`)

---

## 1. Purpose

This document defines the acceptance gate for biography generation in English and French.

It exists to prevent drift between:

- frame normalization,
- planner output,
- lexical resolution,
- renderer behavior,
- GF/runtime fallback behavior,
- and the public API response.

This is not a “smoke test only” document.  
This is the release gate for saying that EN/FR bio generation is aligned, robust, and production-credible.

---

## 2. What this document covers

This document covers:

- generation through `POST /api/v1/generate/{lang}`,
- biography/person payloads normalized to the canonical bio frame,
- planner-first generation for migrated bio constructions,
- public API response shape,
- lexical-resolution visibility,
- fallback behavior,
- gold-example regression for English and French.

This document does **not** define the full generic runtime contract for every construction family.  
It applies the generic runtime contract specifically to EN/FR bio generation.

---

## 3. Acceptance philosophy

EN/FR bio acceptance is achieved only when all of the following are true:

1. the same semantic input can be normalized for both English and French,
2. the runtime uses the same planner-facing contract for both languages,
3. the selected construction semantics remain stable across backends,
4. lexical resolution is explicit and inspectable,
5. the public response shape is stable,
6. French produces actual French surface text,
7. English produces actual English surface text,
8. fallback, if used, is explicit and machine-readable,
9. regression can be caught automatically using gold examples.

A passing compile is not sufficient.  
A passing legacy direct-generation result is not sufficient.  
A non-empty sentence is not sufficient.

---

## 4. Canonical entrypoint

Primary endpoint under test:

```http
POST /api/v1/generate/{lang}
````

Where:

* `{lang}` is the authoritative path language,
* accepted values for this document are `en` and `fr`,
* URL language and payload language must match if both are present,
* language compatibility must be tested through the public API, not only internal unit tests.

---

## 5. Canonical input contract for bio acceptance

### 5.1 Canonical semantic shape

The acceptance target is a normalized bio/person frame that carries, at minimum:

* subject identity,
* profession,
* nationality,
* optional gender and metadata,
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

### 5.2 Legacy compatibility at the boundary

The system may accept legacy or compatibility aliases such as:

* `bio`
* `biography`
* `entity.person`
* `entity_person`
* `person`
* `entity.person.v1`
* `entity.person.v2`

However:

* acceptance is awarded only after these inputs are normalized,
* compatibility ends at normalization,
* downstream planner/runtime code must not depend on legacy payload quirks.

### 5.3 Language authority rule

If the path language is provided, it is authoritative.

Examples:

* `/generate/en` + payload `lang=en` → valid
* `/generate/fr` + payload `lang=fr` → valid
* `/generate/fr` + payload `lang=en` → fail
* missing language everywhere → fail

---

## 6. Canonical runtime expectations

For migrated bio generation, the authoritative path is:

1. request normalization,
2. frame-to-plan bridge,
3. planner,
4. lexical resolution,
5. realization,
6. response mapping.

The acceptance path for migrated EN/FR bio generation is **planner-first**.

Legacy direct frame-to-engine generation may remain temporarily for compatibility, but it must be treated as a compatibility path, not as the target architecture.

---

## 7. Canonical runtime objects

EN/FR bio acceptance must align to these runtime concepts:

* `planned_sentence`
* `construction_plan`
* `construction_id`
* `slot_map`
* `lexical_bindings`
* `generation_options`
* `renderer_backend`
* `surface_result`
* `debug_info`
* `fallback_used`

No backend may require a second private planner-facing contract.

No renderer may silently replace planner-selected construction semantics.

---

## 8. Construction expectations

### 8.1 Construction identity

The same semantic bio case in EN and FR must be realized from the same canonical runtime construction identity.

Requirements:

* `construction_id` must be canonical and planner-owned,
* `construction_id` must not be backend-local,
* EN and FR must not diverge into different semantic constructions for the same test case,
* dotted compatibility input names are not acceptable runtime `construction_id` values.

### 8.2 Allowed construction family

The selected runtime construction for bio acceptance must belong to the canonical construction inventory for equative/classification-style biography output.

Examples of acceptable canonical runtime IDs include project-approved IDs such as:

* `copula_equative_simple`
* `copula_equative_classification`
* `bio_lead_identity`

The exact accepted ID is whichever canonical runtime ID the planner selects for the tested bio lead configuration in this repository.

What matters is:

* it is canonical,
* it is stable,
* it is shared across EN and FR for the same semantic case.

---

## 9. Public API response requirements

A successful public generation response for EN/FR bio acceptance must expose:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `tokens`
* `debug_info`

Minimum successful example shape:

```json
{
  "text": "Marie Curie was a Polish physicist.",
  "lang_code": "en",
  "construction_id": "copula_equative_classification",
  "renderer_backend": "family",
  "fallback_used": false,
  "tokens": [
    "Marie",
    "Curie",
    "was",
    "a",
    "Polish",
    "physicist."
  ],
  "debug_info": {
    "runtime_path": "planner_first",
    "construction_id": "copula_equative_classification",
    "renderer_backend": "family",
    "lang_code": "en",
    "fallback_used": false,
    "slot_keys": ["subject", "profession", "nationality"],
    "selected_backend": "family",
    "attempted_backends": ["family"]
  }
}
```

French example shape:

```json
{
  "text": "Marie Curie était une physicienne polonaise.",
  "lang_code": "fr",
  "construction_id": "copula_equative_classification",
  "renderer_backend": "family",
  "fallback_used": false,
  "tokens": [
    "Marie",
    "Curie",
    "était",
    "une",
    "physicienne",
    "polonaise."
  ],
  "debug_info": {
    "runtime_path": "planner_first",
    "construction_id": "copula_equative_classification",
    "renderer_backend": "family",
    "lang_code": "fr",
    "fallback_used": false,
    "slot_keys": ["subject", "profession", "nationality"],
    "selected_backend": "family",
    "attempted_backends": ["family"]
  }
}
```

---

## 10. Required `debug_info` expectations

The top-level public response must keep stable diagnostics.

For EN/FR bio acceptance, `debug_info` must expose enough information to determine:

* which runtime path was used,
* which construction was realized,
* which backend produced the final surface,
* whether fallback occurred,
* which slots were consumed,
* whether lexical resolution was applied.

### 10.1 Minimum required debug keys

Required keys:

* `runtime_path`
* `construction_id`
* `renderer_backend`
* `lang_code`
* `fallback_used`

Strongly recommended keys:

* `slot_keys`
* `selected_backend`
* `attempted_backends`
* `lexical_resolution`
* `warnings`

### 10.2 Runtime path requirement

For migrated bio constructions, passing acceptance requires:

```json
{
  "runtime_path": "planner_first"
}
```

If the runtime path is `legacy_direct_frame`, the result may be recorded as compatibility evidence, but it does **not** satisfy planner-first EN/FR bio acceptance.

---

## 11. Lexical-resolution requirements

Lexical resolution must be explicit and testable.

For bio acceptance, this includes at least:

* profession lexicalization,
* nationality lexicalization,
* source/provenance visibility where available,
* deterministic fallback behavior where lexical lookup fails.

### 11.1 Required lexical invariants

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

### 11.2 Language-specific lexicalization requirement

For EN and FR, lexical realization must be language-appropriate.

Examples:

* English profession/nationality realizations must be English.
* French profession/nationality realizations must be French.

If the French path produces English lexical material for the same bio case, acceptance fails.

---

## 12. English-specific surface requirements

For `lang=en`, accepted output must satisfy all of the following:

* the sentence is grammatical English,
* the copular/equative structure is English,
* profession and nationality are expressed in English,
* tokens and text align,
* no French-only morphology appears unless explicitly quoted in the subject string,
* no silent fallback changes semantics.

Examples of acceptable English outputs depend on `generation_options`, but the language must remain clearly English.

---

## 13. French-specific surface requirements

For `lang=fr`, accepted output must satisfy all of the following:

* the sentence is grammatical French,
* the copular/equative structure is French,
* profession and nationality are expressed in French,
* article and agreement behavior are French-appropriate for the tested lexical items,
* tokens and text align,
* no English copula/article scaffold remains in the final surface,
* no silent fallback changes semantics.

Examples of unacceptable French outputs include outputs that contain English scaffold such as:

* `is`
* `is a`
* `participated in`

for ordinary French biography generation.

A French request that resolves successfully but returns English surface text is a release blocker.

---

## 14. EN/FR semantic equivalence requirements

For the same normalized bio input and the same generation options:

* EN and FR must preserve the same subject identity,
* EN and FR must preserve the same profession meaning,
* EN and FR must preserve the same nationality meaning,
* EN and FR must preserve the same construction semantics,
* EN and FR may differ in morphology, article use, agreement, and word order,
* EN and FR must not diverge in truth conditions.

Semantic equivalence does **not** require token-by-token literal correspondence.
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

### 15.4 Suite D — Renderer parity tests

At least two deterministic realizers/backends must be able to consume the same bio-oriented plan shape during migration or staging, where repository support exists.

Parity does **not** require identical strings.
Parity requires:

* same `construction_id`,
* same `lang_code`,
* same semantic slot intent,
* explicit backend trace.

### 15.5 Suite E — Fallback behavior tests

If fallback is triggered, tests must verify:

* `fallback_used=true`,
* original backend is traceable,
* final backend is traceable,
* fallback reason is present,
* `construction_id` is preserved,
* `lang_code` is preserved,
* semantics are preserved.

Silent fallback is an automatic fail.

### 15.6 Suite F — Gold regression tests

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
If generation options change tense/register, the gold set must specify those options explicitly.

---

## 17. Acceptance commands

Use the exact repo workflow expected for language validation.

### 17.1 Required validation flow

1. refresh matrix,
2. validate lexicon,
3. compile PGF,
4. validate language health,
5. run real EN/FR generation,
6. run judge/regression,
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
* missing or invalid `lang_code`
* hidden planner-facing contract required by one backend only

### 19.2 Runtime failures

* migrated bio generation uses `legacy_direct_frame` in the main acceptance suite
* fallback occurred but was not explicitly annotated
* renderer silently changed construction semantics
* runtime consumed raw payload quirks below normalization

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
* judge/regression fails
* matrix/build/health state regresses after a change
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

EN/FR bio generation is considered accepted only when:

1. canonical bio inputs and compatibility aliases both normalize correctly,
2. planner-first runtime is used for migrated bio generation,
3. EN and FR share the same canonical construction semantics,
4. French generates actual French surface text,
5. English generates actual English surface text,
6. lexical resolution is explicit and testable,
7. public response fields are stable and complete,
8. fallback is explicit and machine-readable,
9. gold examples exist for both languages,
10. judge/regression passes,
11. matrix and health checks remain green after the acceptance run.

If any of these conditions is false, EN/FR bio acceptance is not complete.

---

## 23. Final rule

EN/FR bio acceptance is not awarded for “some sentence came out.”

It is awarded only when:

* semantics are preserved,
* contracts are aligned,
* runtime path is correct,
* diagnostics are explicit,
* French is truly French,
* English is truly English,
* and regressions are mechanically catchable.


# Debug Info Contract

Status: normative for renderer/runtime diagnostics; authoritative for shared `debug_info` semantics across runtime layers and canonical public success responses; compatibility-aware for legacy payload readers during migration  
Applies to: internal `SurfaceResult` objects, planner-first renderer outputs, public HTTP generation success responses, legacy `Sentence`-compatible payloads during migration, frontend `nlg.api.GenerationResult` payloads when diagnostics are exposed, QA tooling, test fixtures

---

## 1. Purpose

`debug_info` is the structured diagnostics object attached to a generation result.

It exists to support:

- runtime debugging,
- planner/construction tracing,
- lexical-resolution tracing,
- backend comparison,
- fallback observability,
- QA assertions,
- frontend developer tooling,
- safe operational diagnostics without exposing secrets.

`debug_info` is diagnostic metadata.  
It is not user-facing prose, not semantic content, and not a replacement for the main response envelope.

---

## 2. Scope and boundaries

This document defines:

- the shared meaning of `debug_info`,
- the required stable keys used across runtime layers,
- parity rules between top-level result fields and `debug_info`,
- visibility rules by boundary,
- compatibility rules for legacy debug payloads,
- safety and observability constraints.

This document does **not** define:

- the full public HTTP success envelope,
- the full internal `ConstructionPlan` contract,
- the request payload contract,
- the public error envelope,
- arbitrary frontend-only wrapper models.

---

## 3. Source of truth and precedence

This document governs the meaning and minimum structure of `debug_info`.

Related contract boundaries:

- `construction_runtime_contract.md` governs internal runtime handoff and `SurfaceResult`
- `planner_realizer_interfaces.md` governs planner / lexical-resolution / realizer interface expectations
- `public_generation_response_contract.md` governs the canonical public HTTP success envelope
- `public_vs_runtime_vs_frontend_boundaries.md` governs what belongs to runtime, public API, and frontend wrappers
- `EN_FR_FINAL_PARALLEL_LOCKDOWN.md` governs final branch lock rules and conflict resolution during the EN/FR cutover
- `nlg/api.py` defines a separate frontend convenience API and is **not** the canonical public HTTP response contract

Conflict rules:

1. if the issue is the public HTTP top-level response shape, `public_generation_response_contract.md` wins;
2. if the issue is runtime/renderer diagnostics semantics, this document must agree with `construction_runtime_contract.md`;
3. if the issue is planner/realizer ownership or where metadata must first exist, `planner_realizer_interfaces.md` and the final lock document win;
4. if the issue is frontend convenience wrappers, they may be stricter or thinner, but they must not redefine the shared meaning of the stable debug keys defined here.

Any disagreement must be corrected immediately.

---

## 4. Where `debug_info` appears

### 4.1 Internal runtime / renderer boundary

For the aligned planner-first runtime, `debug_info` is attached to renderer outputs and internal `SurfaceResult` results.

This is the most important boundary for this contract.

### 4.2 Public HTTP generation success responses

For canonical public HTTP generation success responses, `debug_info` **MUST** be included as part of the public success envelope and **MUST** preserve the stable shared keys defined here when they are available on the runtime result.

Compatibility serializers may temporarily accept thinner legacy inputs during migration, but new public response code must not treat `debug_info` omission as the default design.

### 4.3 Frontend `nlg.api.GenerationResult`

The `nlg.api` frontend wrapper is a separate interface.

It may expose `debug_info` only when `debug=True`.  
This conditional exposure does not weaken the shared meaning of the keys when `debug_info` is present.

### 4.4 Legacy wrappers

During migration, `debug_info` may also appear on:

- legacy `Sentence` objects,
- direct engine payloads,
- compatibility wrappers,
- old test fixtures.

Readers must tolerate thinner legacy payloads.  
New canonical producers must not treat those thinner payloads as the target design.

---

## 5. Core rules

### 5.1 Object only

If present, `debug_info` MUST be a JSON object / dictionary.

It must never be:

- a string,
- a list,
- a number,
- nested under another arbitrary wrapper.

### 5.2 Machine-readable first

Values SHOULD be structured and stable.

Prefer:

```json
{ "renderer_backend": "gf", "fallback_used": false }
````

Over:

```json
{ "note": "GF worked and no fallback was needed" }
```

### 5.3 Shared keys stay shared

The shared diagnostics keys defined in this document MUST retain stable meaning across backends.

Backend-specific keys MAY be added, but they MUST NOT silently replace shared keys.

### 5.4 Additive evolution only

New keys MAY be added.

Existing keys MUST NOT be silently repurposed.

### 5.5 Forward-compatible readers

Readers MUST tolerate:

* missing keys,
* unknown keys,
* partial payloads,
* legacy payloads,
* backend-specific extensions.

### 5.6 No hidden semantic contract

`debug_info` is diagnostics only.

It MUST NOT become a shadow planner contract, a hidden slot map, or the only carrier of data required to interpret the result semantically.

If a renderer, serializer, evaluator, or client needs some field to understand the generation result semantically or contractually, that field belongs in the real runtime or public response contract, not only in `debug_info`.

### 5.7 Mapper must not invent nominal truth

For canonical planner-first results, `debug_info` MUST already exist on the runtime result before API mapping.

The API mapper MAY normalize, preserve, or thin compatibility payloads where explicitly allowed, but it MUST NOT invent nominal planner-first facts that should already exist on the canonical runtime result.

### 5.8 Safe for logs and UI diagnostics

`debug_info` MUST NOT contain:

* API keys,
* bearer tokens,
* raw credentials,
* auth headers,
* full secrets,
* full env dumps,
* raw secret-bearing exception context,
* unredacted sensitive PII beyond already-public labels,
* internal filesystem paths in public production responses unless explicitly allowed in development mode,
* full upstream payloads if they may contain sensitive data.

---

## 6. Presence rules by boundary

### 6.1 Internal runtime / renderer outputs

For new runtime/renderer producers returning canonical `SurfaceResult` outputs, `debug_info` **MUST** be present.

### 6.2 Public HTTP success responses

For canonical public HTTP generation success responses, `debug_info` **MUST** be present.

Public HTTP serializers MUST NOT strip already-available stable debug fields without an explicit contract decision.

### 6.3 Frontend `nlg.api.GenerationResult`

For the frontend wrapper, `debug_info` MAY be omitted unless `debug=True`.

When present, it SHOULD preserve the stable shared keys and SHOULD avoid inventing frontend-only meanings for shared fields.

### 6.4 Legacy compatibility payloads

Legacy compatibility payloads MAY omit `debug_info`.

New code must not rely on omission as the desired long-term behavior.

---

## 7. Stable shared keys

These keys have stable shared meaning across runtime and backend layers.

### 7.1 Required shared keys for canonical planner-first runtime producers

Canonical planner-first runtime/renderer producers MUST provide:

* `construction_id`
* `renderer_backend`
* `lang_code`
* `slot_keys`
* `fallback_used`
* `runtime_path`

### 7.2 Semantics of required shared keys

#### `construction_id`

* Type: `string`
* Meaning: the construction the runtime claims to have realized
* Rule: MUST remain stable across fallback
* Rule: MUST NOT exist only in `debug_info` on the nominal public success path

#### `renderer_backend`

* Type: `string`
* Examples:

  * `"gf"`
  * `"family"`
  * `"safe_mode"`
* Meaning: the backend that produced the realized result
* Rule: MUST match the top-level result backend when both are present

#### `lang_code`

* Type: `string`
* Examples:

  * `"en"`
  * `"fr"`
* Meaning: the normalized language code of the realized surface result
* Rule: MUST match the realized language code carried by the result itself

#### `slot_keys`

* Type: `array[string]`
* Meaning: the semantic slot names available to the realized construction/result
* Rule: MUST reflect semantic slot names, not backend-local field names
* Rule: SHOULD be stable enough for tests and QA assertions

#### `fallback_used`

* Type: `boolean`
* Meaning: whether fallback occurred on the path that produced the returned result
* Rule: MUST be explicit
* Rule: MUST match the top-level result fallback flag when both are present

#### `runtime_path`

* Type: `string`
* Canonical nominal value: `"planner_first"`
* Meaning: the runtime path that produced the returned result
* Rule: MUST be explicit for canonical planner-first results
* Rule: MUST NOT claim `"planner_first"` if required nominal metadata is missing

### 7.3 Public HTTP note

Public HTTP serializers MUST preserve the canonical shared keys when they are available on the runtime result.

During migration, older compatibility serializers may temporarily expose only a subset.
That is compatibility debt, not the target contract.

---

## 8. Metadata parity rules

When both top-level result fields and `debug_info` carry the same fact, they MUST agree.

### 8.1 Required parity rules

* top-level `lang_code` and `debug_info.lang_code` MUST match
* top-level `fallback_used` and `debug_info.fallback_used` MUST match
* top-level `renderer_backend` and `debug_info.renderer_backend` MUST match when both are present
* top-level `construction_id` and `debug_info.construction_id` MUST match when both are present

### 8.2 Time authority rule

`generation_time_ms` is a top-level result/public-contract field.
If timing diagnostics are also present inside `debug_info`, the top-level field remains authoritative.

### 8.3 No debug-only nominal metadata rule

On the canonical nominal planner-first path, required public/runtime facts such as:

* `construction_id`
* `renderer_backend`
* `lang_code`
* `fallback_used`

MUST NOT live only inside `debug_info`.

---

## 9. Recommended additional keys

The following keys are strongly recommended when available.

### 9.1 Backend selection and dispatch

* `selected_backend`
* `requested_backend`
* `attempted_backends`
* `dispatch_policy`
* `capability_tier`
* `fallback_reason`

### 9.2 Runtime path and provenance

* `producer`
* `input_kind`
* `trace_id`
* `backend_trace`

### 9.3 Lexical-resolution diagnostics

* `lexical_resolution`
* `lexical_sources`
* `missing_slots`
* `unsupported_features`

### 9.4 Renderer-specific diagnostics

* `resolved_language`
* `concrete_name`
* `family`
* `template_id`
* `template_used`
* `ast`
* `surface_tokens`

### 9.5 Timing and warning diagnostics

* `timings_ms`
* `warnings`
* `errors`

---

## 10. Canonical organization

When `debug_info` is rich, new producers SHOULD prefer a structured envelope like this:

```json
{
  "construction_id": "copula_equative_classification",
  "renderer_backend": "gf",
  "lang_code": "fr",
  "slot_keys": ["subject", "profession", "nationality"],
  "fallback_used": false,
  "runtime_path": "planner_first",
  "selected_backend": "gf",
  "attempted_backends": ["gf"],
  "dispatch_policy": {
    "allow_fallback": true,
    "forced_backend": null
  },
  "lexical_resolution": {
    "profession": {
      "source": "lexicon",
      "confidence": 0.94
    },
    "nationality": {
      "source": "lexicon",
      "confidence": 0.95
    }
  },
  "backend_trace": [
    "validated slots",
    "resolved lexical bindings",
    "assembled equative clause"
  ],
  "warnings": []
}
```

Rules:

* the required shared keys remain top-level inside `debug_info`,
* nested sections SHOULD be preferred over unstructured top-level sprawl,
* backend-specific data MAY be added,
* public HTTP serializers MUST NOT move shared keys into nested-only form.

---

## 11. Canonical nested sections

To avoid top-level key sprawl, rich payloads SHOULD prefer these nested sections where appropriate.

### 11.1 `planning`

Planning-stage metadata.

Example:

```json
{
  "planning": {
    "planner": "discourse.planner",
    "construction_id": "copula_equative_classification",
    "topic_entity_id": "Q7251",
    "focus_role": "predicate_nominal",
    "sentence_kind": "definition",
    "domain": "generic"
  }
}
```

### 11.2 `lexical_resolution`

Lexeme/entity normalization and provenance metadata.

Example:

```json
{
  "lexical_resolution": {
    "resolved_slots": {
      "subject": "entity_ref",
      "predicate_nominal": "lexeme_ref"
    },
    "sources": {
      "subject": "frame.subject",
      "predicate_nominal": "local_lexicon"
    },
    "fallback_slots": [],
    "confidence": 0.91
  }
}
```

### 11.3 `realization`

Renderer-specific realization metadata.

Example:

```json
{
  "realization": {
    "renderer_backend": "gf",
    "ast": "mkCopulaEquativeClassification (...)",
    "surface_strategy": "gf_linearization",
    "resolved_language": "WikiFre",
    "concrete_name": "WikiFre",
    "family": null,
    "profile": null
  }
}
```

### 11.4 `timings_ms`

Timing breakdown in milliseconds.

Example:

```json
{
  "timings_ms": {
    "planning": 0.2,
    "lexical_resolution": 0.4,
    "realization": 1.8,
    "total": 2.7
  }
}
```

---

## 12. Language-code rules

`lang_code` is the canonical shared debug key for the normalized result language.

Rules:

* use `lang_code` as the stable shared key,
* keep it aligned with the actual result language code,
* do not invent parallel top-level keys such as `lang_code_resolved` as the new canonical shared field,
* backend-specific concrete grammar selection may still use fields such as:

  * `resolved_language`
  * `concrete_name`
  * `realization.resolved_language`

Example:

```json
{
  "lang_code": "fr",
  "resolved_language": "WikiFre",
  "concrete_name": "WikiFre"
}
```

---

## 13. Relationship to `SurfaceResult`

At the runtime/renderer boundary, `debug_info` belongs to `SurfaceResult`.

The shared contract assumes canonical `SurfaceResult` results expose:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `tokens`
* `debug_info`
* `generation_time_ms`

and may additionally expose:

* `warnings`
* `confidence`

Rules:

* `debug_info` MUST remain separate from the top-level result fields,
* top-level result fields MUST NOT be hidden only inside `debug_info`,
* top-level optional fields such as `warnings` or `confidence` do not disappear just because related diagnostics also exist in `debug_info`,
* `SurfaceResult` is the canonical runtime result object before API mapping,
* API response mapping happens only after `SurfaceResult` already contains its canonical nominal metadata.

If a public boundary chooses not to expose some additional top-level field beyond the canonical success envelope, that choice must be documented by the relevant public contract.

---

## 14. Relationship to public HTTP responses

For canonical public HTTP generation success responses:

* `debug_info` is diagnostics, not the main payload,
* top-level fields such as `text`, `lang_code`, `construction_id`, `renderer_backend`, `fallback_used`, `tokens`, and `generation_time_ms` remain authoritative,
* `debug_info` SHOULD mirror the stable shared keys for observability,
* public HTTP serializers MUST preserve shared keys that already exist on the runtime result,
* public HTTP serializers MUST NOT invent missing nominal planner-first metadata,
* public HTTP serializers MUST NOT strip `slot_keys` if they are already available on the runtime result.

This document does not redefine the full public envelope.
It only defines the diagnostics object inside that envelope.

---

## 15. Relationship to frontend `nlg.api.GenerationResult`

`nlg.api.GenerationResult` is a separate frontend convenience wrapper.

It uses fields such as:

* `text`
* `sentences`
* `lang`
* `frame`
* `debug_info`

Rules:

* it is not the canonical public HTTP response contract,
* it MAY omit `debug_info` unless `debug=True`,
* when it exposes `debug_info`, shared keys such as `construction_id`, `renderer_backend`, `lang_code`, `slot_keys`, `fallback_used`, and `runtime_path` keep the same meaning,
* frontend wrappers MUST NOT redefine shared keys with a different meaning.

---

## 16. Legacy key compatibility

Older parts of the system may emit ad hoc debug fields such as:

* `backend`
* `engine`
* `resolved_language`
* `ast`
* `template_used`
* `source`

These remain accepted for backward compatibility.

### 16.1 Reader requirements

Readers MUST accept payloads like:

```json
{
  "ast": "mkCopulaEquativeSimple (...)",
  "resolved_language": "WikiFre"
}
```

or:

```json
{
  "engine": "safe_mode",
  "template_used": "{name} is a {profession}"
}
```

or:

```json
{
  "source": "dummy-test"
}
```

### 16.2 Normalized interpretation

When consuming legacy payloads, map them conceptually as follows:

| Legacy key          | Canonical meaning                                    |
| ------------------- | ---------------------------------------------------- |
| `backend`           | `renderer_backend`                                   |
| `engine`            | `renderer_backend` or `realization.renderer_backend` |
| `source`            | `producer`                                           |
| `resolved_language` | `realization.resolved_language`                      |
| `ast`               | `realization.ast`                                    |
| `template_used`     | `realization.template_used`                          |

### 16.3 Producer guidance

During migration, producers MAY emit both canonical shared keys and legacy extras, but the stable shared keys in this document remain the long-term contract.

New canonical producers MUST NOT omit canonical shared keys merely because legacy extras are also present.

---

## 17. Backend-specific guidance

### 17.1 GF backend

GF-based producers SHOULD normally include:

* `renderer_backend = "gf"`
* `construction_id`
* `lang_code`
* `slot_keys`
* `fallback_used`
* `runtime_path`
* `resolved_language`
* `concrete_name`
* `ast`

### 17.2 Family renderer backend

Family renderers SHOULD normally include:

* `renderer_backend = "family"`
* `construction_id`
* `lang_code`
* `slot_keys`
* `fallback_used`
* `runtime_path`
* `family`
* `template_id` or equivalent
* `backend_trace`

### 17.3 Safe-mode backend

Safe-mode producers SHOULD normally include:

* `renderer_backend = "safe_mode"`
* `construction_id`
* `lang_code`
* `slot_keys`
* `fallback_used`
* `runtime_path`
* `template_used`
* `fallback_reason`
* `backend_trace`

---

## 18. Fallback rules

If fallback occurs, `debug_info` MUST make it explicit.

Fallback diagnostics SHOULD include:

* `fallback_used = true`
* `fallback_reason`
* original/requested backend where known
* final selected backend
* backend trace when available

Fallback MUST NOT silently change:

* `construction_id`
* intended semantic role structure
* result language code

Fallback MUST NOT be used to make a nominal planner-first success appear complete when required canonical metadata is missing.

---

## 19. Warnings, errors, and confidence

### 19.1 `warnings`

`warnings` MAY appear in `debug_info` as an array of stable warning codes or compact machine-readable messages.

### 19.2 `errors`

`errors` MAY appear in `debug_info` for non-fatal diagnostic issues.

Fatal failures belong in the error response contract, not only in `debug_info`.

### 19.3 `confidence`

`confidence` MAY appear inside nested diagnostic sections such as `lexical_resolution`.

It MUST NOT be treated as a universally required top-level shared debug key unless a separate contract decision makes it so.

---

## 20. Size, stability, and determinism

### 20.1 Size budget

`debug_info` should stay reasonably small for API responses and frontend rendering.

Recommended soft limit:

* target: under 4 KB
* hard warning threshold: 16 KB

### 20.2 Stable identifiers over prose

Prefer stable identifiers/codes over descriptive prose.

### 20.3 Deterministic ordering

When practical, emit keys in a stable order for snapshot testing and log diffing.

Suggested order:

1. `construction_id`
2. `renderer_backend`
3. `lang_code`
4. `slot_keys`
5. `fallback_used`
6. `runtime_path`
7. `selected_backend`
8. `attempted_backends`
9. `dispatch_policy`
10. `lexical_resolution`
11. `backend_trace`
12. `warnings`
13. `errors`

---

## 21. Privacy and security

`debug_info` must never contain:

* API keys
* auth headers
* full env dumps
* raw secret-bearing exception context
* internal filesystem paths in public production responses unless explicitly allowed in development mode
* full upstream payloads if they may contain sensitive data

Safe examples include:

* language codes
* construction IDs
* slot names
* template IDs
* AST strings
* concrete grammar names
* backend family names
* non-sensitive trace IDs

---

## 22. JSON Schema sketch

This is an informal sketch for implementers.

```json
{
  "type": "object",
  "additionalProperties": true,
  "properties": {
    "construction_id": { "type": ["string", "null"] },
    "renderer_backend": { "type": ["string", "null"] },
    "lang_code": { "type": ["string", "null"] },
    "slot_keys": {
      "type": "array",
      "items": { "type": "string" }
    },
    "fallback_used": { "type": "boolean" },
    "runtime_path": { "type": ["string", "null"] },

    "selected_backend": { "type": ["string", "null"] },
    "requested_backend": { "type": ["string", "null"] },
    "attempted_backends": {
      "type": "array",
      "items": { "type": "string" }
    },
    "producer": { "type": ["string", "null"] },
    "input_kind": { "type": ["string", "null"] },
    "trace_id": { "type": ["string", "null"] },
    "dispatch_policy": { "type": "object" },
    "lexical_resolution": { "type": "object" },
    "realization": { "type": "object" },
    "backend_trace": {
      "type": "array",
      "items": { "type": "string" }
    },
    "timings_ms": { "type": "object" },
    "warnings": {
      "type": "array",
      "items": { "type": "string" }
    },
    "errors": {
      "type": "array",
      "items": {}
    },

    "backend": { "type": ["string", "null"] },
    "engine": { "type": ["string", "null"] },
    "source": { "type": ["string", "null"] },
    "ast": { "type": ["string", "null"] },
    "resolved_language": { "type": ["string", "null"] },
    "concrete_name": { "type": ["string", "null"] },
    "template_used": { "type": ["string", "null"] }
  }
}
```

---

## 23. Examples

### 23.1 Canonical public HTTP success response

```json
{
  "text": "Alan Turing is a British mathematician.",
  "lang_code": "en",
  "construction_id": "copula_equative_classification",
  "renderer_backend": "gf",
  "fallback_used": false,
  "tokens": ["Alan", "Turing", "is", "a", "British", "mathematician."],
  "debug_info": {
    "construction_id": "copula_equative_classification",
    "renderer_backend": "gf",
    "lang_code": "en",
    "slot_keys": ["subject", "profession", "nationality"],
    "fallback_used": false,
    "runtime_path": "planner_first",
    "selected_backend": "gf",
    "attempted_backends": ["gf"]
  },
  "generation_time_ms": 12.5
}
```

### 23.2 Frontend `nlg.api` response when `debug=True`

```json
{
  "text": "Alan Turing is a British mathematician.",
  "sentences": ["Alan Turing is a British mathematician."],
  "lang": "en",
  "frame": {
    "frame_type": "bio",
    "subject": {
      "name": "Alan Turing"
    }
  },
  "debug_info": {
    "construction_id": "copula_equative_classification",
    "renderer_backend": "family",
    "lang_code": "en",
    "slot_keys": ["subject", "profession", "nationality"],
    "fallback_used": false,
    "runtime_path": "planner_first"
  }
}
```

### 23.3 Canonical rich runtime debug payload

```json
{
  "construction_id": "copula_equative_classification",
  "renderer_backend": "gf",
  "lang_code": "fr",
  "slot_keys": ["subject", "profession", "nationality"],
  "fallback_used": false,
  "runtime_path": "planner_first",
  "selected_backend": "gf",
  "attempted_backends": ["gf"],
  "dispatch_policy": {
    "allow_fallback": true,
    "forced_backend": null
  },
  "lexical_resolution": {
    "profession": {
      "source": "wikidata",
      "confidence": 0.93
    },
    "nationality": {
      "source": "wikidata",
      "confidence": 0.89
    }
  },
  "resolved_language": "WikiFre",
  "concrete_name": "WikiFre",
  "ast": "mkBioFull (...)",
  "backend_trace": [
    "validated slots",
    "resolved lexical bindings",
    "mapped plan to GF AST",
    "linearized with WikiFre"
  ],
  "warnings": []
}
```

---

## 24. Conformance requirements

A producer is conformant if:

1. it emits `debug_info` on new canonical internal runtime/renderer results,
2. emitted `debug_info` is always an object,
3. it never includes secrets,
4. it uses the stable shared keys with their documented meanings,
5. for canonical planner-first runtime results, it includes at least:

   * `construction_id`
   * `renderer_backend`
   * `lang_code`
   * `slot_keys`
   * `fallback_used`
   * `runtime_path`
6. backend-specific details do not replace shared keys,
7. it does not rely on the API mapper to invent nominal planner-first metadata.

A reader is conformant if:

1. it accepts missing `debug_info` on legacy payloads,
2. it accepts unknown keys,
3. it accepts legacy top-level keys,
4. it does not crash on partial payloads,
5. it does not reinterpret shared keys with backend-specific meaning.

---

## 25. Migration policy

### Phase 1

Allow legacy and canonical keys side by side.

### Phase 2

Update frontend, tools, and tests to prefer the stable shared keys.

### Phase 3

Require the stable shared keys for all new canonical runtime/renderer producers.

### Phase 4

Require public HTTP serializers to preserve shared keys consistently.

### Phase 5

Keep legacy extras only where compatibility is still required.

### Phase 6

Do not remove legacy keys without explicit release-note coverage and regression validation.

---

## 26. Final rule

`debug_info` is the stable diagnostics object for runtime generation.

It must be:

* structured,
* machine-readable,
* safe,
* comparable across backends,
* backward-compatible for legacy readers,
* aligned with canonical `SurfaceResult`,
* explicit about fallback,
* explicit about runtime path,
* and centered on stable shared keys.

If two active generation paths use the same key names in `debug_info` but with different meanings, the contract is broken.

If a canonical planner-first path appears successful while required nominal metadata exists only in `debug_info` or is first invented by the API mapper, the contract is broken.


# Public Generation Response Contract

Status: normative  
Owner: API / Runtime  
Scope: canonical HTTP success response returned by SemantiK Architect generation endpoints

---

## 1. Purpose

This document defines the authoritative **public HTTP success response** for text generation in SemantiK Architect.

It covers the response returned by generation endpoints such as:

- `POST /api/v1/generate/{lang}`
- any future HTTP generation endpoint that exposes the same generation runtime outcome

This contract exists to ensure that:

- API clients receive one stable success shape,
- runtime migration does not leak backend-specific response drift,
- planner-first and compatibility paths serialize to the same public envelope,
- diagnostics remain machine-readable,
- frontend and backend teams do not drift into different “public” response definitions.

This is the **public transport contract**.  
It is not the full internal planning contract and it is not the renderer-facing `ConstructionPlan` contract.

---

## 2. Scope

This document defines:

- the top-level JSON fields of a successful generation response,
- required field semantics,
- normalization rules,
- debug and fallback observability rules,
- tokenization transport rules,
- compatibility behavior during migration,
- precedence against adjacent contracts.

This document does **not** define:

- request payload shape,
- planner input/output shape,
- lexical binding internals,
- error response envelopes,
- multi-sentence discourse serialization,
- frontend-local result objects outside the HTTP API.

---

## 3. Contract boundary and precedence

There are three distinct layers that MUST NOT be conflated:

1. **Public HTTP success envelope**  
   Defined by this document.

2. **Internal runtime result contract**  
   Defined by runtime-facing contracts such as `construction_runtime_contract.md`.

3. **Frontend or helper-library result shapes**  
   Any UI-facing or convenience result object is not automatically the public HTTP contract.

Precedence rules:

- if the issue is about **HTTP success serialization**, this document wins;
- if the issue is about **renderer input/output inside runtime**, runtime contracts win;
- if the issue is about **debug structure**, this document and `debug_info_contract.md` must agree;
- if any helper API or frontend model differs from this document, that helper/model MUST adapt to this contract, not the reverse.

---

## 4. Canonical success response

A successful generation response MUST serialize as a JSON object with the following top-level fields:

```json
{
  "text": "Alan Turing is a British mathematician.",
  "lang_code": "en",
  "construction_id": "copula_equative_classification",
  "renderer_backend": "gf",
  "fallback_used": false,
  "tokens": [
    "Alan",
    "Turing",
    "is",
    "a",
    "British",
    "mathematician."
  ],
  "debug_info": {
    "construction_id": "copula_equative_classification",
    "renderer_backend": "gf",
    "lang_code": "en",
    "fallback_used": false,
    "slot_keys": [
      "subject",
      "profession",
      "nationality"
    ],
    "selected_backend": "gf",
    "attempted_backends": ["gf"]
  },
  "generation_time_ms": 12.5
}
````

There is exactly one canonical public success envelope.

The following legacy public shapes are deprecated and non-canonical:

* `surface_text`
* `meta`
* backend-local ad hoc top-level envelopes

---

## 5. Top-level fields

### 5.1 `text`

Type: `string`
Required: yes

The realized surface text.

Rules:

* MUST be a non-empty string after trimming.
* MUST represent the surface realization actually returned to the caller.
* MUST NOT be nested under another field such as `surface_text`.
* MUST be the authoritative public text output.

---

### 5.2 `lang_code`

Type: `string`
Required: yes

The public API language code for the generated surface text.

Rules:

* MUST identify the language of the returned surface text.
* MUST use the public API normalization convention: lowercase short language codes such as `en`, `fr`, `pt`.
* MUST NOT use alternative runtime-internal spellings such as `eng` at the public boundary.
* MUST remain stable across fallback.
* MUST match the realized language, not merely the originally requested raw payload spelling.

Notes:

* Internal runtime layers may temporarily use other normalized forms.
* Those internal forms MUST NOT leak into the public HTTP envelope.

---

### 5.3 `construction_id`

Type: `string`
Required: yes

The canonical runtime construction identifier used for realization.

Rules:

* MUST be present as a top-level field.
* MUST be a non-empty canonical runtime identifier.
* SHOULD be a canonical runtime identifier such as:

  * `copula_equative_simple`
  * `copula_equative_classification`
  * `copula_attributive_np`
  * `topic_comment_copular`
* MUST be preserved across fallback.
* MUST NOT be replaced by backend-local naming at the public boundary.

Migration note:

* If any active serializer still emits `null` here, that serializer is non-conformant and MUST be fixed.
* `null` is not part of the normative public contract.

---

### 5.4 `renderer_backend`

Type: `string`
Required: yes

The backend that produced the final surface text.

Expected values include:

* `gf`
* `family`
* `safe_mode`

Rules:

* MUST identify the backend that produced the final response.
* MUST reflect the final selected backend, not merely the preferred backend.
* SHOULD match `debug_info.renderer_backend`.
* MUST be non-empty.

Migration note:

* If any active serializer still emits `null` here, that serializer is non-conformant and MUST be fixed.
* `null` is not part of the normative public contract.

---

### 5.5 `fallback_used`

Type: `boolean`
Required: yes

Whether fallback occurred anywhere on the path that produced the returned text.

Rules:

* MUST be explicit.
* MUST be `false` when the primary intended backend produced the result directly.
* MUST be `true` when the system had to fall back to another backend, raw lexical fallback, or another explicitly defined compatibility fallback path.
* MUST be machine-readable and MUST NOT rely only on logs or free text.

---

### 5.6 `tokens`

Type: `array<string>`
Required: yes

A tokenized transport representation of the returned surface text.

Rules:

* MUST be an array of strings.
* MUST preserve the left-to-right order of the returned text.
* MUST correspond to the final returned text, not to an intermediate AST or slot map.
* MAY be provided directly by the backend.
* If not provided by the backend, it SHOULD be derived from the final `text`.
* MUST remain lightweight and transport-oriented.

Tokenization transport policy:

* `tokens` is not a full linguistic annotation layer.
* Clients MUST NOT assume morphology, lemma, POS, or syntactic segmentation.
* Punctuation MAY remain attached to adjacent tokens if that matches the concrete serializer behavior.
* Whitespace is represented implicitly by token order, not as separate tokens.
* Test suites MAY validate token order and string equality, but SHOULD NOT assume language-universal tokenization sophistication.

---

### 5.7 `debug_info`

Type: `object`
Required: yes

Structured diagnostic metadata for the returned generation result.

Rules:

* MUST be an object.
* MUST remain separate from user-facing text.
* MUST contain stable machine-readable diagnostics.
* MUST NOT replace core top-level public fields.
* MUST NOT become a second public response envelope.
* MUST be present even when verbose debug tracing is disabled.

Debug visibility policy:

* The public HTTP success envelope MUST always include `debug_info`.
* When verbose diagnostics are disabled, `debug_info` MAY be minimal.
* Minimal `debug_info` still MUST contain the required keys listed below.

Minimum required debug keys:

* `construction_id`
* `renderer_backend`
* `lang_code`
* `fallback_used`
* `slot_keys`

`slot_keys` rules:

* MUST be an array of strings.
* MUST list the semantic/planner-facing slot names materially used to produce the result.
* MAY be an empty array when no such slots are applicable.

Recommended additional keys:

* `selected_backend`
* `attempted_backends`
* `runtime_path`
* `backend_trace`
* `dispatch_policy`
* `lexical_resolution`
* `resolved_language`
* `gf_function`
* `ast`
* `warnings`
* `timings_ms`

Backend-specific diagnostics MAY be included under `debug_info`, but these fields are optional and MUST NOT replace the stable required diagnostics.

---

### 5.8 `generation_time_ms`

Type: `number`
Required: yes

The generation duration in milliseconds for the returned result.

Rules:

* MUST be numeric.
* SHOULD be serialized as a float-compatible number.
* MAY be `0.0` when timing is unavailable.
* MUST refer to the generated response returned to the caller.

---

## 6. Explicit exclusions from the public top level

The following fields are **not** part of the canonical public success envelope and MUST NOT appear as top-level public fields unless this document is versioned and updated explicitly:

* `surface_text`
* `meta`
* `slot_map`
* `lexical_bindings`
* raw planner metadata
* raw renderer payloads
* frontend-only fields such as `sentences`
* frontend-only fields such as `frame`
* internal confidence bundles not explicitly promoted to the public contract
* internal warnings bundles not explicitly promoted to the public contract

Notes:

* `warnings` MAY appear under `debug_info`.
* `confidence` is currently reserved for internal/runtime use unless and until explicitly promoted by a future version of this public contract.

---

## 7. Canonical JSON schema shape

The public success response MUST conform to the following conceptual schema:

```json
{
  "type": "object",
  "required": [
    "text",
    "lang_code",
    "construction_id",
    "renderer_backend",
    "fallback_used",
    "tokens",
    "debug_info",
    "generation_time_ms"
  ],
  "properties": {
    "text": { "type": "string", "minLength": 1 },
    "lang_code": {
      "type": "string",
      "pattern": "^[a-z]{2,3}$"
    },
    "construction_id": {
      "type": "string",
      "minLength": 1
    },
    "renderer_backend": {
      "type": "string",
      "minLength": 1
    },
    "fallback_used": { "type": "boolean" },
    "tokens": {
      "type": "array",
      "items": { "type": "string" }
    },
    "debug_info": {
      "type": "object",
      "required": [
        "construction_id",
        "renderer_backend",
        "lang_code",
        "fallback_used",
        "slot_keys"
      ],
      "properties": {
        "construction_id": { "type": "string", "minLength": 1 },
        "renderer_backend": { "type": "string", "minLength": 1 },
        "lang_code": { "type": "string", "pattern": "^[a-z]{2,3}$" },
        "fallback_used": { "type": "boolean" },
        "slot_keys": {
          "type": "array",
          "items": { "type": "string" }
        }
      },
      "additionalProperties": true
    },
    "generation_time_ms": { "type": "number" }
  },
  "additionalProperties": false
}
```

---

## 8. Invariants

The following invariants are mandatory.

### 8.1 Surface text invariant

`text` MUST be the final surface text returned to the caller.

### 8.2 Language invariant

`lang_code` MUST identify the language of `text`.

### 8.3 Construction invariant

`construction_id` MUST describe the construction that the runtime claims to have realized.

Fallback MUST NOT silently change construction identity.

### 8.4 Backend invariant

`renderer_backend` MUST name the backend that produced the returned text.

### 8.5 Fallback invariant

If fallback happened anywhere relevant to the returned result, `fallback_used` MUST be `true`.

### 8.6 Debug parity invariant

The following top-level fields MUST be reflected consistently in `debug_info`:

* `construction_id`
* `renderer_backend`
* `lang_code`
* `fallback_used`

### 8.7 Slot visibility invariant

`debug_info.slot_keys` MUST be present and MUST describe the slot names materially used by the generation path, or be an empty array when no slots apply.

### 8.8 Token invariant

`tokens` MUST correspond to the final text returned to the caller.

---

## 9. Serialization guarantees across runtime paths

The public envelope MUST remain stable across:

* planner-first success,
* legacy direct-frame success,
* compatibility-shim success,
* success after backend fallback.

Across all successful paths, the following fields MUST always be present and comparable:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `tokens`
* `debug_info`
* `generation_time_ms`

Path-specific diagnostic detail MAY vary inside `debug_info`, but the top-level public envelope MUST NOT vary.

---

## 10. Example: planner-first success

```json
{
  "text": "Alan Turing is a British mathematician.",
  "lang_code": "en",
  "construction_id": "copula_equative_classification",
  "renderer_backend": "family",
  "fallback_used": false,
  "tokens": [
    "Alan",
    "Turing",
    "is",
    "a",
    "British",
    "mathematician."
  ],
  "debug_info": {
    "construction_id": "copula_equative_classification",
    "renderer_backend": "family",
    "lang_code": "en",
    "fallback_used": false,
    "slot_keys": [
      "subject",
      "profession",
      "nationality"
    ],
    "selected_backend": "family",
    "attempted_backends": ["family"],
    "runtime_path": "planner_first",
    "backend_trace": [
      "planned construction",
      "resolved lexical bindings",
      "assembled equative clause"
    ]
  },
  "generation_time_ms": 12.5
}
```

---

## 11. Example: legacy-compatible success

```json
{
  "text": "Marie Curie is a Polish physicist",
  "lang_code": "fr",
  "construction_id": "copula_equative_classification",
  "renderer_backend": "gf",
  "fallback_used": true,
  "tokens": [
    "Marie",
    "Curie",
    "is",
    "a",
    "Polish",
    "physicist"
  ],
  "debug_info": {
    "construction_id": "copula_equative_classification",
    "renderer_backend": "gf",
    "lang_code": "fr",
    "fallback_used": true,
    "slot_keys": [
      "subject",
      "profession",
      "nationality"
    ],
    "selected_backend": "gf",
    "attempted_backends": ["family", "gf"],
    "runtime_path": "legacy_direct_frame",
    "fallback_reason": "planner_runtime_unavailable",
    "resolved_language": "WikiFre",
    "ast": "mkBioFull (mkEntityStr \"Marie Curie\") (strProf \"physicist\") (strNat \"Polish\")"
  },
  "generation_time_ms": 0.0
}
```

Note: this example demonstrates envelope shape and observability, not linguistic quality.

---

## 12. Error boundary

This document defines only the **success response**.

Failure responses:

* MUST use explicit HTTP error semantics,
* MUST NOT masquerade as success envelopes,
* MUST NOT return partial success objects with missing required top-level success fields.

Error-contract details belong in `public_generation_error_contract.md`, not here.

---

## 13. Acceptance criteria

This contract is considered implemented when:

1. generation endpoints return the same top-level success shape regardless of backend,
2. `text` is always the authoritative public surface field,
3. `lang_code`, `construction_id`, `renderer_backend`, and `fallback_used` are explicit and non-null,
4. `debug_info` is always present,
5. `debug_info` contains the required stable keys, including `slot_keys`,
6. planner-first and compatibility paths serialize to the same public envelope,
7. legacy response shapes such as `surface_text` and `meta` are fully deprecated,
8. clients can compare generation outcomes across backends without inspecting internal runtime objects.

---

## 14. Relationship to other docs

This document is aligned with:

* `construction_runtime_contract.md`
* `debug_info_contract.md`
* `frame_to_construction_mapping.md`
* `lexical_resolution_contract.md`
* `construction_renderer_contract.md`
* `public_generation_error_contract.md`
* `public_vs_runtime_vs_frontend_boundaries.md`
* `tokenization_contract.md`
* `generation_path_serialization_matrix.md`

Conflict rule:

* if the issue is about renderer input or planning handoff, runtime contract docs win;
* if the issue is about public HTTP success serialization, this document wins;
* if the issue is about debug structure, this document and `debug_info_contract.md` must agree;
* if the issue is about token transport semantics, this document and `tokenization_contract.md` must agree;
* if the issue is about path-specific serialization guarantees, this document and `generation_path_serialization_matrix.md` must agree.

Any disagreement must be corrected immediately.

---

## 15. Final rule

There is exactly one canonical public generation success envelope.

If two generation paths return different public top-level shapes for the same class of success result, the contract is broken.



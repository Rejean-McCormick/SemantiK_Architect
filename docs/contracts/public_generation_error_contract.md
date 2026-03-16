# Public Generation Error Contract

Status: normative  
Owner: API / Runtime  
Scope: canonical HTTP error response returned by SemantiK Architect generation endpoints

---

## 1. Purpose

This document defines the authoritative **public HTTP error contract** for generation endpoints in SemantiK Architect.

It exists so that:

- clients can handle generation failures deterministically,
- auth, validation, routing, and runtime failures do not produce ad hoc response shapes,
- migration from legacy/direct generation paths to planner-first runtime does not leak transport inconsistency,
- logs, UI clients, tests, and observability tools can rely on stable machine-readable error data.

This document defines the **public transport error envelope**.  
It does **not** define the internal exception hierarchy or backend-specific failure classes.

---

## 2. Scope

This contract applies to generation endpoints such as:

- `POST /api/v1/generate/{lang_code}`
- `POST /api/v1/generate`

It covers:

- authentication failures,
- request-shape and request-language failures,
- frame normalization failures,
- unsupported frame or construction failures,
- language resolution failures,
- runtime realization failures,
- internal server failures.

It does **not** define:

- success responses,
- tool endpoints,
- management/onboarding error contracts,
- frontend-local adapter errors,
- WebSocket or async worker event failures.

---

## 3. Relationship to other contracts

This document must be read together with:

- `public_generation_response_contract.md`
- `construction_runtime_contract.md`
- `debug_info_contract.md`

Boundary rule:

- if the response is a successful generation result, `public_generation_response_contract.md` governs;
- if the response is an HTTP failure for generation, this document governs;
- if the issue is internal runtime object shape, runtime contracts govern, not this document.

The public API error response is a mapped external view of failures.  
It must not be documented as if it were the runtime contract itself.

---

## 4. Design principles

The generation error contract must satisfy all of the following:

1. **One public error envelope** for generation failures.
2. **Machine-readable error code** independent of free-text detail.
3. **Stable HTTP status semantics** across migration paths.
4. **Safe transport behavior**: no secrets, raw stack traces, or backend-private objects in public responses.
5. **Actionable messages** for operators and clients.
6. **Compatibility-aware migration**: legacy errors may still occur internally, but must map to this envelope at the API boundary.

---

## 5. Canonical public error envelope

All non-2xx generation failures MUST serialize to this top-level shape:

```json
{
  "error": {
    "code": "invalid_frame",
    "message": "Missing required field: frame_type",
    "status": 422,
    "category": "request_validation",
    "retryable": false,
    "details": {
      "field": "frame_type"
    }
  }
}
````

### Top-level rule

The canonical public generation error response contains exactly one top-level field:

* `error`

No successful response fields such as `text` or `lang_code` may appear in an error response.

---

## 6. Error object fields

### 6.1 `error.code`

Type: `string`
Required: yes

A stable machine-readable identifier for the failure.

Rules:

* MUST be snake_case.
* MUST be stable across wording changes in the free-text message.
* MUST be the primary programmatic key used by clients.

Examples:

* `missing_api_key`
* `invalid_api_key`
* `server_misconfiguration`
* `missing_language`
* `language_mismatch`
* `invalid_frame`
* `unsupported_frame_type`
* `language_not_found`
* `unsupported_construction`
* `generation_failed`
* `internal_error`

---

### 6.2 `error.message`

Type: `string`
Required: yes

A human-readable explanation of the failure.

Rules:

* MUST be safe to expose publicly.
* MUST NOT contain secrets, access tokens, raw headers, or stack traces.
* SHOULD be specific enough for debugging and UI display.
* MAY reuse a normalized message derived from internal exceptions.

---

### 6.3 `error.status`

Type: `integer`
Required: yes

The HTTP status code returned with the response.

Rules:

* MUST match the actual HTTP response status.
* MUST be duplicated inside the body for easier client handling and logging.

---

### 6.4 `error.category`

Type: `string`
Required: yes

A coarse-grained classification of the error.

Allowed values:

* `authentication`
* `request_validation`
* `language_resolution`
* `frame_normalization`
* `construction_selection`
* `runtime`
* `server`

Rules:

* MUST remain broader and more stable than `error.code`.
* MUST help clients group failures without parsing the free-text message.

---

### 6.5 `error.retryable`

Type: `boolean`
Required: yes

Whether retrying the same request without modification is likely to succeed.

Rules:

* MUST be `false` for auth failures, invalid input, unsupported frame types, and language mismatches.
* MAY be `true` for transient runtime/infrastructure failures.
* SHOULD be conservative: when unsure, use `false`.

---

### 6.6 `error.details`

Type: `object`
Required: yes

Additional machine-readable structured details about the failure.

Rules:

* MUST be an object.
* MAY be empty.
* MUST remain JSON-safe.
* MUST NOT contain secrets.
* MUST NOT contain raw Python exception objects or stack traces.
* SHOULD expose field-level or mapping-level context where it helps clients recover.

Possible keys include:

* `field`
* `path_lang_code`
* `payload_lang_code`
* `normalized_frame_type`
* `requested_lang_code`
* `resolved_lang_code`
* `construction_id`
* `backend`
* `reason`
* `missing_fields`
* `expected`
* `received`

---

## 7. Canonical JSON schema shape

```json
{
  "type": "object",
  "required": ["error"],
  "properties": {
    "error": {
      "type": "object",
      "required": [
        "code",
        "message",
        "status",
        "category",
        "retryable",
        "details"
      ],
      "properties": {
        "code": { "type": "string", "minLength": 1 },
        "message": { "type": "string", "minLength": 1 },
        "status": { "type": "integer", "minimum": 400, "maximum": 599 },
        "category": { "type": "string", "minLength": 1 },
        "retryable": { "type": "boolean" },
        "details": { "type": "object" }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

---

## 8. Status code mapping

The generation API must use the following public status semantics.

### 8.1 `403 Forbidden`

Used for authentication failures at the API boundary.

Cases include:

* missing `X-API-Key` header,
* invalid API key credentials.

Canonical codes:

* `missing_api_key`
* `invalid_api_key`

Category:

* `authentication`

Retryable:

* `false`

---

### 8.2 `422 Unprocessable Entity`

Used when the request is syntactically accepted as JSON/HTTP input but cannot be processed as a valid generation request.

Cases include:

* missing required generation fields,
* missing `frame_type`,
* missing required language when no path language is provided,
* mismatch between path language and payload language,
* invalid frame normalization,
* invalid Ninai parsing,
* unsupported frame shape or unusable generation payload.

Canonical codes may include:

* `missing_language`
* `language_mismatch`
* `invalid_frame`
* `invalid_ninai_payload`
* `unsupported_frame_type`
* `request_validation_error`

Category:

* `request_validation`
* `frame_normalization`

Retryable:

* `false`

Notes:

* Existing tests already expect `422` for invalid generation payloads.
* FastAPI request/body validation may also surface here.

---

### 8.3 `404 Not Found`

Used when the requested generation target cannot be resolved as an available language/runtime target.

Cases include:

* requested language is not available,
* requested language is not present in the currently loaded grammar/runtime.

Canonical code:

* `language_not_found`

Category:

* `language_resolution`

Retryable:

* `false`

---

### 8.4 `500 Internal Server Error`

Used for server-side or runtime failures that are not attributable to client input.

Cases include:

* server misconfiguration (for example missing API secret in production),
* internal realization failure,
* unmapped exception,
* unexpected runtime failure.

Canonical codes may include:

* `server_misconfiguration`
* `generation_failed`
* `internal_error`

Category:

* `server`
* `runtime`

Retryable:

* usually `false`
* MAY be `true` for explicitly classified transient runtime failures

---

## 9. Canonical error code taxonomy

### 9.1 Authentication

| Code                      | Status | Category         | Retryable | Meaning                                            |
| ------------------------- | ------ | ---------------- | --------- | -------------------------------------------------- |
| `missing_api_key`         | 403    | `authentication` | false     | No API key was provided                            |
| `invalid_api_key`         | 403    | `authentication` | false     | API key was provided but rejected                  |
| `server_misconfiguration` | 500    | `server`         | false     | Required auth configuration is missing server-side |

---

### 9.2 Request / input

| Code                       | Status | Category              | Retryable | Meaning                                         |
| -------------------------- | ------ | --------------------- | --------- | ----------------------------------------------- |
| `request_validation_error` | 422    | `request_validation`  | false     | Generic request/body validation failed          |
| `missing_language`         | 422    | `request_validation`  | false     | No language was supplied where required         |
| `language_mismatch`        | 422    | `request_validation`  | false     | Path language and payload language conflict     |
| `invalid_frame`            | 422    | `frame_normalization` | false     | Payload cannot be normalized into a valid frame |
| `invalid_ninai_payload`    | 422    | `frame_normalization` | false     | Ninai payload parsing failed                    |
| `unsupported_frame_type`   | 422    | `frame_normalization` | false     | Frame type is missing, empty, or unsupported    |

---

### 9.3 Runtime / resolution

| Code                       | Status | Category                 | Retryable | Meaning                                                                    |
| -------------------------- | ------ | ------------------------ | --------- | -------------------------------------------------------------------------- |
| `language_not_found`       | 404    | `language_resolution`    | false     | Requested language/runtime target cannot be resolved                       |
| `unsupported_construction` | 422    | `construction_selection` | false     | Construction exists semantically but cannot be realized by the active path |
| `generation_failed`        | 500    | `runtime`                | false     | Generation failed unexpectedly after request normalization                 |
| `internal_error`           | 500    | `server`                 | false     | Catch-all internal failure                                                 |

---

## 10. Mapping from current code paths

This section documents how current repo behavior maps into the public contract.

### 10.1 API key dependency

The API key dependency currently raises transport-level `HTTPException` failures for:

* missing `X-API-Key` header,
* invalid API key credentials,
* missing server auth config in production.

Public mapping:

* missing header -> `403` / `missing_api_key`
* invalid credentials -> `403` / `invalid_api_key`
* missing required server auth configuration -> `500` / `server_misconfiguration`

---

### 10.2 Generation request mapper

The generation request mapper currently raises `InvalidFrameError` for conditions such as:

* payload is not a JSON object,
* missing language when required,
* path language / payload language mismatch,
* missing `frame_type`,
* invalid frame format,
* invalid Ninai parsing,
* bio/person payload without a recoverable subject name.

Public mapping:

* missing language -> `422` / `missing_language`
* path/payload mismatch -> `422` / `language_mismatch`
* malformed/invalid frame normalization -> `422` / `invalid_frame`
* invalid Ninai payload -> `422` / `invalid_ninai_payload`

---

### 10.3 Generation endpoint tests

Existing endpoint tests already establish two important transport expectations:

* missing or invalid API key returns `403`,
* invalid generation payload returns `422`.

This contract preserves those transport semantics and standardizes the body shape.

---

### 10.4 Legacy and migration-era runtime failures

Planner-first, legacy direct-frame, compatibility shim, GF, family, and safe-mode paths may currently fail with different internal exceptions or result-mapping behavior.

At the public HTTP boundary, those failures MUST still normalize to this contract.

The internal exception source MUST NOT determine a different public envelope.

---

## 11. Public body examples

### 11.1 Missing API key

```json
{
  "error": {
    "code": "missing_api_key",
    "message": "Missing X-API-Key header",
    "status": 403,
    "category": "authentication",
    "retryable": false,
    "details": {}
  }
}
```

---

### 11.2 Invalid API key

```json
{
  "error": {
    "code": "invalid_api_key",
    "message": "Invalid X-API-Key credentials",
    "status": 403,
    "category": "authentication",
    "retryable": false,
    "details": {}
  }
}
```

---

### 11.3 Missing language in payload-driven generation

```json
{
  "error": {
    "code": "missing_language",
    "message": "Missing language. Provide `lang` (top-level) or `inputs.language`.",
    "status": 422,
    "category": "request_validation",
    "retryable": false,
    "details": {
      "field": "language"
    }
  }
}
```

---

### 11.4 Path language / payload language mismatch

```json
{
  "error": {
    "code": "language_mismatch",
    "message": "Language mismatch between URL and payload.",
    "status": 422,
    "category": "request_validation",
    "retryable": false,
    "details": {
      "path_lang_code": "en",
      "payload_lang_code": "fr"
    }
  }
}
```

---

### 11.5 Invalid frame payload

```json
{
  "error": {
    "code": "invalid_frame",
    "message": "Missing required field: frame_type",
    "status": 422,
    "category": "frame_normalization",
    "retryable": false,
    "details": {
      "field": "frame_type"
    }
  }
}
```

---

### 11.6 Language not found

```json
{
  "error": {
    "code": "language_not_found",
    "message": "Requested language is not available.",
    "status": 404,
    "category": "language_resolution",
    "retryable": false,
    "details": {
      "requested_lang_code": "zul"
    }
  }
}
```

---

### 11.7 Internal generation failure

```json
{
  "error": {
    "code": "generation_failed",
    "message": "Generation failed unexpectedly.",
    "status": 500,
    "category": "runtime",
    "retryable": false,
    "details": {}
  }
}
```

---

## 12. Error-body invariants

The following invariants are mandatory.

### 12.1 No success fields in error responses

An error response MUST NOT include:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `tokens`
* `debug_info`

Those belong to successful generation responses only.

---

### 12.2 No secret leakage

Public error responses MUST NOT expose:

* API secrets or API keys,
* `Authorization` headers,
* raw bearer tokens,
* stack traces,
* internal filesystem paths unless explicitly reviewed for safety,
* backend-private exception repr strings if they reveal unsafe internals.

---

### 12.3 Stable code/message separation

Clients MUST be able to rely on `error.code` without parsing `error.message`.

Changing message wording must not change programmatic handling.

---

### 12.4 JSON-safe details only

`error.details` MUST contain only JSON-safe material.

No Python exceptions, dataclasses, object reprs, or raw Pydantic/traceback dumps may appear.

---

## 13. Debug and observability policy

This public error contract is intentionally smaller than internal observability.

Rules:

* rich internal logs MAY contain exception classes, stack traces, backend traces, and runtime context;
* the public response MUST expose only safe normalized error data;
* correlation identifiers MAY be added later, but only as reviewed explicit fields.

If a future correlation field is added, it SHOULD be:

* `error.request_id` or
* `error.correlation_id`

and it MUST be safe for public exposure.

---

## 14. Migration policy

Current repo behavior still contains a mixture of:

* legacy route/test expectations,
* mapper-level normalization errors,
* runtime migration between direct-frame and planner-first paths,
* older docs that describe ad hoc error tables instead of a stable public envelope.

This document defines the target public contract that all generation paths must converge on.

Migration rules:

1. legacy/internal exceptions may continue temporarily,
2. the API boundary must map them into this public envelope,
3. tests must assert public shape, not internal exception classes,
4. old ad hoc error tables or body shapes are deprecated for generation endpoints.

---

## 15. Acceptance criteria

This contract is considered implemented when:

1. generation auth failures return the canonical `error` envelope,
2. generation validation failures return the canonical `error` envelope,
3. language-not-found failures return the canonical `error` envelope,
4. unexpected runtime failures return the canonical `error` envelope,
5. no generation error response leaks success-only fields,
6. no generation error response leaks secrets or stack traces,
7. endpoint tests assert both status code and canonical body shape.

---

## 16. Final rule

There is exactly one canonical public generation error envelope.

If two generation failure paths return different public top-level error shapes for the same class of failure, the contract is broken.



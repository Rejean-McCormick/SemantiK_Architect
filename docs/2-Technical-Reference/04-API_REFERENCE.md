# 🔌 API Reference & Semantic Frames

**SemantiK Architect — Canonical Public HTTP Contract**

Status: normative for the public HTTP generation surface  
Applies to: `/api/v1/generate/{lang_code}` and closely related public utility endpoints  
Related contracts:
- `docs/contracts/public_generation_response_contract.md`
- `docs/contracts/construction_runtime_contract.md`
- `docs/contracts/debug_info_contract.md`
- `docs/contracts/public_vs_runtime_vs_frontend_boundaries.md`
- `docs/architecture/multilingual_runtime_target.md`
- `docs/architecture/EN_FR_FINAL_PARALLEL_LOCKDOWN.md`

---

## 1. Overview

SemantiK Architect exposes its text-generation runtime through a REST API.

The canonical backend API is served under:

- **Base path:** `/api/v1`
- **Local dev default:** `http://localhost:8000/api/v1`
- **Encoding:** UTF-8
- **Transport:** JSON over HTTP

This reference defines the **canonical public HTTP contract** for generation and related utility endpoints.

### Canonical generation model

The primary generation route is:

**`POST /api/v1/generate/{lang_code}`**

This route accepts a JSON object, normalizes it into the canonical internal semantic/frame shape, executes the planner-first runtime, and returns a structured JSON success response.

### Architectural notes

- The backend is canonically mounted at `/api/v1/...`.
- Health is intentionally available at both:
  - `/health/live`, `/health/ready`
  - `/api/v1/health/live`, `/api/v1/health/ready`
- The canonical runtime path for successful generation is **planner-first**.
- The canonical public success response is a structured JSON envelope centered on:
  - `text`
  - `lang_code`
  - `construction_id`
  - `renderer_backend`
  - `fallback_used`
  - `tokens`
  - `debug_info`
  - `generation_time_ms`
- Older clients that depend primarily on `surface_text` / `meta` are not aligned with the canonical public contract.
- Legacy input aliases may still be accepted at the request boundary, but they do not change the canonical public response shape.

---

## 2. Authentication

This reference documents the API surface and payload/response contracts only.

Authentication and authorization may be deployment-specific, for example:

- reverse proxy enforcement,
- API gateway enforcement,
- protected admin/tooling routes,
- environment-specific access policies.

Do not assume that generation requires a built-in `X-API-Key` unless your deployment explicitly adds that requirement.

---

## 3. Primary Endpoint

## Generate Text

**`POST /api/v1/generate/{lang_code}`**

Generate natural-language text from a semantic payload.

### Path Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `lang_code` | `string` | Yes | Authoritative language code for the request. The router normalizes supported variants. |

### Request Headers

| Header | Value | Required | Description |
| --- | --- | --- | --- |
| `Content-Type` | `application/json` | Yes | Request body must be a JSON object. |
| `Accept` | `application/json` | Recommended | The canonical public response contract is JSON. |

### Request Body

The request body must be a **single JSON object**.

Rules enforced by the request boundary:

- the URL path language is authoritative;
- if both URL language and payload language are provided, they must match after normalization;
- if no path language is provided by some internal caller or alternate mounting path, the payload must carry a recognized language field;
- transport-level language fields are normalized at the API boundary before semantic/frame parsing;
- request compatibility aliases are a boundary concern only and do not redefine the internal runtime contract.

Recognized payload language aliases may include:

- `lang`
- `language`
- `lang_code`
- `inputs.language`
- `inputs.lang`
- `inputs.lang_code`

---

## 4. Supported Input Modes

The public request boundary supports multiple input styles that converge to one internal semantic/frame model.

The stable public rule is:

**JSON object in, canonical JSON success envelope out.**

### A. Bio / person payloads

The following frame types are treated as bio/person-compatible inputs and normalized through the same compatibility boundary:

- `bio`
- `biography`
- `entity.person`
- `entity_person`
- `person`
- `entity.person.v1`
- `entity.person.v2`

### Canonical bio example

```json
{
  "frame_type": "bio",
  "name": "Alan Turing",
  "profession": "mathematician",
  "nationality": "British",
  "gender": "m"
}
````

### Compatibility bio example

```json
{
  "frame_type": "entity.person.v2",
  "subject": {
    "name": "Alan Turing",
    "profession": "mathematician",
    "nationality": "British"
  }
}
```

### Common bio fields

| Field         | Type             | Required     | Notes                                                |
| ------------- | ---------------- | ------------ | ---------------------------------------------------- |
| `frame_type`  | `string`         | Yes          | Prefer `bio` for new clients.                        |
| `name`        | `string`         | Usually yes  | Common top-level compatibility field.                |
| `profession`  | `string`         | Commonly yes | May be normalized through lexical resolution.        |
| `nationality` | `string`         | No           | Optional.                                            |
| `gender`      | `string \| null` | No           | Optional compatibility field.                        |
| `subject`     | `object`         | Sometimes    | Used by some newer or compatibility person payloads. |

### B. Generic semantic frame payloads

Non-bio semantic payloads are also accepted when they match supported internal frame/domain semantics.

Example:

```json
{
  "frame_type": "event",
  "subject": "Marie Curie",
  "event_type": "award",
  "date": "1903"
}
```

### C. Ninai / function-style payloads

The request boundary may also accept Ninai-style or function-oriented payloads through the Ninai adapter.

Example:

```json
{
  "function": "ninai.constructors.Statement",
  "args": [
    { "function": "ninai.types.Bio" },
    { "function": "ninai.constructors.List", "args": ["physicist"] },
    { "function": "ninai.constructors.Entity", "args": ["Q7186"] }
  ]
}
```

This is a parsing/adapter concern only.
The stable public generation contract remains the same.

---

## 5. Semantic Frame Rules

Semantic frames are the canonical public input abstraction.

### Core rule

Clients send semantic intent, not renderer-specific instructions.

That means:

* clients describe the meaning to be generated;
* the planner/runtime selects the construction;
* lexical resolution binds language-appropriate material;
* the realizer/backend produces the final surface text.

### Public input boundary rules

Public clients must not rely on:

* GF-specific ASTs as the public contract,
* backend-specific surface templates as the public contract,
* direct renderer selection as a semantic requirement,
* debug-only fields to carry required meaning.

### Practical guidance

For new API clients:

* prefer stable frame-style JSON objects;
* prefer `frame_type: "bio"` for person/bio generation;
* treat compatibility aliases as tolerated inputs, not as the long-term design center.

---

## 6. Success Response

The canonical public success response is a JSON object with this top-level shape:

| Field                | Type       | Required | Description                                                 |
| -------------------- | ---------- | -------- | ----------------------------------------------------------- |
| `text`               | `string`   | Yes      | Final generated surface text.                               |
| `lang_code`          | `string`   | Yes      | Language code of the returned text.                         |
| `construction_id`    | `string`   | Yes      | Explicit construction identifier for the returned result.   |
| `renderer_backend`   | `string`   | Yes      | Backend that produced the final text.                       |
| `fallback_used`      | `boolean`  | Yes      | Whether fallback was used in producing the returned result. |
| `tokens`             | `string[]` | Yes      | Tokenized representation of the returned text.              |
| `debug_info`         | `object`   | Yes      | Structured diagnostics object.                              |
| `generation_time_ms` | `number`   | Yes      | Authoritative top-level generation time in milliseconds.    |

### Canonical success response example

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
    "lang_code": "en",
    "slot_keys": ["subject", "profession", "nationality"],
    "fallback_used": false,
    "selected_backend": "family",
    "attempted_backends": ["family"]
  },
  "generation_time_ms": 12.5
}
```

### Response rules

* `text` is the authoritative public text field.
* `lang_code` identifies the returned surface language.
* `construction_id` is explicit on the canonical nominal path.
* `renderer_backend` is explicit on the canonical nominal path.
* `fallback_used` is explicit.
* `tokens` correspond to the final text.
* `generation_time_ms` is top-level and authoritative.
* `debug_info` must not contradict top-level fields.
* top-level nominal facts must not exist **only** inside `debug_info`.

### Parity rules

When both top-level fields and `debug_info` carry the same fact, they must agree:

* `lang_code == debug_info.lang_code`
* `fallback_used == debug_info.fallback_used`
* `renderer_backend == debug_info.renderer_backend` when both are present
* `construction_id == debug_info.construction_id` when both are present

---

## 7. Diagnostics (`debug_info`)

`debug_info` is the canonical structured diagnostics object carried in successful generation responses.

### Minimum stable shared diagnostics

Canonical planner-first results preserve these stable shared keys when available:

* `construction_id`
* `renderer_backend`
* `lang_code`
* `slot_keys`
* `fallback_used`
* `runtime_path`

### Common recommended diagnostics

Depending on runtime/backend availability, `debug_info` may also include:

* `selected_backend`
* `requested_backend`
* `attempted_backends`
* `dispatch_policy`
* `fallback_reason`
* `resolved_language`
* `concrete_name`
* `family`
* `template_id`
* `template_used`
* `ast`
* `lexical_resolution`
* `backend_trace`
* `warnings`
* `errors`
* `timings_ms`

### Diagnostics rules

* `debug_info` is diagnostics only.
* It is not a replacement for top-level public response fields.
* It must be a JSON object.
* It must be machine-readable first.
* It must not contain secrets, credentials, or raw sensitive payload dumps.
* Public serializers preserve diagnostics; they do not invent missing nominal planner-first facts.

---

## 8. Health Endpoints

### Live

**`GET /health/live`**
**`GET /api/v1/health/live`**

Used for basic liveness checks.

### Ready

**`GET /health/ready`**
**`GET /api/v1/health/ready`**

Used for readiness checks.

Typical readiness response:

```json
{
  "broker": "up",
  "storage": "up",
  "engine": "up"
}
```

---

## 9. Other Mounted Public Endpoints

The app also mounts additional public API areas under `/api/v1`, including:

* `/api/v1/languages`
* `/api/v1/entities`
* `/api/v1/frames`
* `/api/v1/generate/{lang_code}`

It may also mount protected, admin, or developer-oriented areas, including:

* management endpoints under `/api/v1/...`
* tools under `/api/v1/tools/...`

This document focuses on the canonical generation contract.

---

## 10. Error Handling

The generation route expects a JSON object and may reject invalid requests before generation starts.

### Common error situations

| Status        | Condition                                                                    |
| ------------- | ---------------------------------------------------------------------------- |
| `400` / `422` | Invalid JSON object, invalid payload shape, or validation/parsing failure    |
| `400`         | URL language and payload language do not match after normalization           |
| `400`         | Missing language when no authoritative path language is provided             |
| `5xx`         | Internal planner, lexical-resolution, realization, or infrastructure failure |

### Error-handling notes

* Validation/parsing failures may occur before generation begins.
* Runtime failures must not be smuggled through a success response.
* Older error tables tied to exporter-specific behavior or obsolete transport assumptions must not be treated as authoritative for `POST /api/v1/generate/{lang_code}` unless they are explicitly reintroduced and implemented on this route.

---

## 11. Integration Guide (Python Client)

```python
import requests

API_BASE = "http://localhost:8000/api/v1"

def generate_text(frame: dict, lang_code: str = "en") -> dict:
    url = f"{API_BASE}/generate/{lang_code}"
    response = requests.post(
        url,
        json=frame,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()

result = generate_text(
    {
        "frame_type": "bio",
        "name": "Alan Turing",
        "profession": "mathematician",
        "nationality": "British"
    },
    lang_code="en",
)

print(result["text"])
print(result["lang_code"])
print(result["construction_id"])
```

---

## 12. Compatibility Notes

### Input compatibility

Compatibility aliases may still be accepted at the request boundary, especially for bio/person-style payloads.

Examples include:

* alternate `frame_type` values for person/bio inputs,
* nested `subject` forms,
* Ninai-style parsing adapters,
* transport-level language aliases.

### Output compatibility

The canonical public response is the structured JSON envelope documented above.

Clients should not depend on older assumptions such as:

* top-level `surface_text` as the main success field,
* top-level `meta` as the primary contract carrier,
* text/plain as the canonical response contract for this route,
* backend-specific internal fields as the public success contract.

Compatibility handling may exist in code for migration-safe readers, but it does not redefine the public contract.

---

## 13. Deprecated Assumptions

The following should be considered outdated for the canonical public generation route unless explicitly reintroduced and implemented:

* response bodies centered only on `surface_text` / `meta`
* `Accept: text/plain` as the primary documented contract
* `Accept: text/x-conllu` as the documented contract for this route
* `style` query parameter as part of the stable generation API contract
* `X-Session-ID` as part of the stable generation API contract
* legacy direct-frame execution as the canonical public runtime model

---

## 14. Summary

The authoritative public generation contract is:

* **Route:** `POST /api/v1/generate/{lang_code}`
* **Input:** one JSON object carrying semantic/frame intent
* **Runtime:** planner-first nominal generation
* **Output:** one canonical JSON success envelope centered on:

  * `text`
  * `lang_code`
  * `construction_id`
  * `renderer_backend`
  * `fallback_used`
  * `tokens`
  * `debug_info`
  * `generation_time_ms`
* **Diagnostics:** structured, machine-readable, and non-authoritative relative to top-level response fields
* **Compatibility:** accepted at the request boundary where needed, but not allowed to redefine the canonical public contract


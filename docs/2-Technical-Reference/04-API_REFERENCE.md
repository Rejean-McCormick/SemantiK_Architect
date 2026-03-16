# 🔌 API Reference & Semantic Frames

**SemantiK Architect v2.1**

## 1. Overview

SemantiK Architect exposes its text-generation runtime through a REST API.

The canonical backend API is served under:

- **Base path:** `/api/v1`
- **Local dev default:** `http://localhost:8000/api/v1`
- **Encoding:** UTF-8
- **Transport:** JSON over HTTP

This reference describes the **current public HTTP contract** for generation and related utility endpoints.

### Current generation model

The primary generation route is:

**`POST /api/v1/generate/{lang_code}`**

This route accepts a JSON object, normalizes it into an internal frame/domain object, and returns a structured JSON success response.

### Important current-state notes

- The backend is canonically mounted at `/api/v1/...`.
- Health is intentionally available at both:
  - `/health/live`, `/health/ready`
  - `/api/v1/health/live`, `/api/v1/health/ready`
- Older docs or clients expecting only `surface_text` / `meta` are not aligned with the current public response shape.
- The live runtime may still use compatibility shims and, depending on configuration, may pass through a legacy direct-frame path before full planner-first convergence.

---

## 2. Authentication

This reference documents the API surface and payload/response contracts only.

Authentication and authorization may be deployment-specific (for example, enforced at a reverse proxy, gateway, or on protected admin/tooling routes). Do not assume that generation requires a built-in `X-API-Key` unless your deployment explicitly adds that requirement.

---

## 3. Primary Endpoint

## Generate Text

**`POST /api/v1/generate/{lang_code}`**

Generate natural-language text from a semantic payload.

### Path Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `lang_code` | `string` | Yes | Authoritative language code for the request. The router normalizes common variants. |

### Request Headers

| Header | Value | Required | Description |
| --- | --- | --- | --- |
| `Content-Type` | `application/json` | Yes | Request body must be a JSON object. |
| `Accept` | `application/json` | Recommended | Current public contract is JSON. |

### Request Body

The request body must be a **single JSON object**.

Rules enforced by the request mapper:

- If `lang_code` is present in the path, it is authoritative.
- If both URL language and payload language are provided, they must match after normalization.
- If no path language is provided, the payload must include one of:
  - `lang`
  - `language`
  - `lang_code`
  - `inputs.language`
  - `inputs.lang`
  - `inputs.lang_code`
- Transport-level language fields are stripped before frame parsing.

---

## 4. Supported Input Modes

The current request mapper supports two broad input styles:

1. **Bio/person payloads** with legacy compatibility aliases
2. **Generic / Ninai / frame payloads** parsed into domain objects

### A. Bio/person-compatible payloads

The following frame types are treated as bio-like and normalized through the same compatibility path:

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

### Compatibility example

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

| Field         | Type             | Required     | Notes                                                   |
| ------------- | ---------------- | ------------ | ------------------------------------------------------- |
| `frame_type`  | `string`         | Yes          | Prefer `bio` for new clients.                           |
| `name`        | `string`         | Usually yes  | Common top-level compatibility field.                   |
| `profession`  | `string`         | Commonly yes | May be resolved through lexical normalization/fallback. |
| `nationality` | `string`         | No           | Optional.                                               |
| `gender`      | `string \| null` | No           | Optional compatibility field.                           |
| `subject`     | `object`         | Sometimes    | Used by some newer/compat person payloads.              |

### B. Generic frame payloads

Non-bio semantic payloads are also accepted and parsed into internal frame/domain objects when they match supported internal semantics.

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

The mapper also supports Ninai-style or function-oriented payload parsing through the Ninai adapter.

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

This path is supported as an adapter/parsing concern, but the stable public generation contract remains the same: **JSON in, structured JSON out**.

---

## 5. Success Response

The current public success response is a JSON object centered on the following fields:

| Field                | Type             | Required | Description                                               |
| -------------------- | ---------------- | -------- | --------------------------------------------------------- |
| `text`               | `string`         | Yes      | Final generated surface text.                             |
| `lang_code`          | `string`         | Yes      | Language code of the returned text.                       |
| `construction_id`    | `string \| null` | Yes      | Runtime construction identifier, when available.          |
| `renderer_backend`   | `string \| null` | Yes      | Backend that produced the final text.                     |
| `fallback_used`      | `boolean`        | Yes      | Whether fallback was used in producing the result.        |
| `tokens`             | `string[]`       | Yes      | Tokenized representation of the returned text.            |
| `debug_info`         | `object`         | Yes      | Structured diagnostics.                                   |
| `generation_time_ms` | `number`         | Optional | Present when propagated by the underlying runtime result. |

### Example success response

```json
{
  "text": "Alan Turing is a British mathematician",
  "lang_code": "en",
  "construction_id": null,
  "renderer_backend": null,
  "fallback_used": false,
  "tokens": [],
  "debug_info": {
    "runtime_path": "legacy_direct_frame",
    "fallback_used": false,
    "fallback_reason": null,
    "legacy_engine": "GFGrammarEngine",
    "planner_runtime_configured": false,
    "renderer_backend": "gf",
    "compatibility_shim": true,
    "ast": "mkBioFull (mkEntityStr \"Alan Turing\") (strProf \"mathematician\") (strNat \"British\")",
    "resolved_language": "WikiEng"
  },
  "generation_time_ms": 0.0
}
```

### Response notes

* `text` is the authoritative public text field.
* Clients should no longer depend on `surface_text` as the primary public response field.
* `debug_info` is structured and intended for observability and QA.
* `tokens` may be provided directly by the runtime or derived from the final text.
* Some compatibility paths may still return `construction_id` or `renderer_backend` as `null` even though the target-state contract expects them to be explicit.

---

## 6. Health Endpoints

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

## 7. Other Mounted Public Endpoints

The app currently mounts additional public API areas under `/api/v1`, including:

* `/api/v1/languages`
* `/api/v1/entities`
* `/api/v1/frames`
* `/api/v1/generate/{lang_code}`

It also mounts protected/admin or developer-oriented areas, including:

* management endpoints under `/api/v1/...`
* tools under `/api/v1/tools/...`

This document focuses on the generation contract.

---

## 8. Error Handling

The generation route expects a JSON object and may reject invalid requests before generation starts.

### Common error situations

| Status        | Condition                                                                 |
| ------------- | ------------------------------------------------------------------------- |
| `400` / `422` | Invalid JSON object, invalid payload shape, or validation/parsing failure |
| `400`         | URL language and payload language do not match after normalization        |
| `400`         | Missing language when no path language is provided                        |
| `5xx`         | Internal runtime, realization, or infrastructure failure                  |

### Important note

Older error tables that describe specialized transport formats or exporter-specific HTTP semantics should not be treated as the authoritative current contract for `POST /api/v1/generate/{lang_code}` unless they are explicitly reintroduced and implemented on this route.

---

## 9. Integration Guide (Python Client)

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
```

---

## 10. Migration / Compatibility Notes

Current runtime behavior is mixed:

* the target architecture is planner-centered,
* the public generation route is stable,
* compatibility shims still normalize legacy bio/person payloads,
* and live generation may still run through a legacy direct-frame path depending on runtime configuration.

For API consumers, the practical rule is:

* send a JSON object,
* prefer `frame_type: "bio"` for new bio requests,
* treat the returned JSON envelope documented above as the public success contract.

---

## 11. Deprecated assumptions

The following should be considered outdated for the current public generation route unless reintroduced explicitly:

* response body centered only on `surface_text` / `meta`
* `Accept: text/plain` as the primary documented contract
* `Accept: text/x-conllu` as the documented contract for this route
* `style` query parameter as part of the current stable generation API
* `X-Session-ID` as part of the current stable generation API contract

---

## 12. Summary

For the current SemantiK Architect API, the authoritative generation contract is:

* **Route:** `POST /api/v1/generate/{lang_code}`
* **Input:** one JSON object
* **Output:** one JSON object centered on `text` and structured runtime metadata
* **Bio compatibility:** legacy person/bio aliases still supported
* **Runtime status:** stable public route, mixed internal generation paths



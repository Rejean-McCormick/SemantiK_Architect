# API Overview

Status: normative overview  
Owner: API / Runtime  
Scope: high-level integration reference for the public SemantiK Architect HTTP API

SemantiK Architect is exposed through a **versioned HTTP API**.

The canonical application-facing prefix is:

- **`/api/v1`**

This page is the high-level integration overview.

For the canonical public success envelope returned by generation endpoints, see:

- `docs/contracts/public_generation_response_contract.md`

For the boundary between public HTTP responses, internal runtime results, and frontend/helper models, see:

- `docs/contracts/public_vs_runtime_vs_frontend_boundaries.md`

---

## 1. API prefix and route mounting

The FastAPI application mounts its primary public routes under **`/api/v1`**.

Mounted route families include:

- generation
- languages
- entities
- frames
- AI helper endpoints
- management endpoints
- tools endpoints

Health is mounted in two places:

- **`/health/...`**
- **`/api/v1/health/...`**

Use the `/api/v1/...` form for client integrations unless you explicitly need probe-style health endpoints.

---

## 2. Core generation endpoints

## `POST /api/v1/generate/{lang_code}`

This is the canonical text-generation endpoint for stable clients.

Rules:

- `lang_code` is provided as a **path parameter**
- the request body carries the **meaning payload**
- if a language is also present in the body, it must normalize to the same value
- the response returns the generated surface text plus structured runtime metadata
- the path language is authoritative

### Canonical request pattern

Use:

- path language in the URL
- raw semantic payload in the JSON body

Example:

```json
{
  "frame_type": "bio",
  "name": "Marie Curie",
  "profession": "physicist",
  "nationality": "Polish",
  "gender": "f"
}
````

This is the preferred contract for new integrations.

---

## 3. Compatibility generation endpoint

## `POST /api/v1/generate`

A compatibility form is also supported.

In this form, the target language is carried in the request body rather than in the path.

Accepted language aliases include:

* `lang`
* `language`
* `lang_code`
* `target_language`
* `targetLanguage`

Use the path-based endpoint for new integrations unless you specifically need compatibility behavior.

Important note:

* compatibility support exists for migration and adapter tolerance
* it is **not** the nominal target-state integration contract
* clients should prefer `POST /api/v1/generate/{lang_code}`

---

## 4. Accepted request shapes

The generation layer accepts multiple request styles during migration.

### 4.1 Raw semantic payload

This is the preferred shape for current clients.

Post the semantic payload directly as the JSON body.

Examples include:

* flat bio-style payloads using `frame_type`
* normalized semantic frame payloads
* other frame families routed through frame normalization

Bio-like frame types are normalized through the bio/person compatibility path.

Recognized bio-like aliases include forms such as:

* `bio`
* `biography`
* `entity.person`
* `entity_person`
* `person`
* `entity.person.v1`
* `entity.person.v2`

### 4.2 Wrapped compatibility payload

Some callers wrap the frame instead of posting the raw payload directly.

Accepted frame wrapper aliases include:

* `semantic_frame`
* `frame`

Accepted language wrapper aliases include:

* `target_language`
* `targetLanguage`
* `lang`
* `lang_code`
* `language`

Example:

```json
{
  "frame": {
    "frame_type": "bio",
    "subject": { "name": "Ada Lovelace", "qid": "Q7259" },
    "properties": { "profession": "mathematician" }
  },
  "target_language": "en"
}
```

This remains supported for compatibility, but direct raw payloads are preferred for new clients.

### 4.3 Ninai / recursive meaning payload

If the payload contains a top-level `function` field, the request is treated as a Ninai-style recursive meaning payload and routed through the Ninai adapter path.

This path remains compatibility/prototype-oriented and should not be treated as the default production contract.

---

## 5. Request normalization rules

Before generation, the API normalizes requests into a stable internal command.

Key rules:

* if the URL contains a language, it wins
* if both URL and payload contain a language, they must match after normalization
* transport-only language fields are stripped from the semantic payload
* recognized bio/person aliases are normalized before generation
* Ninai payloads are parsed through the adapter path
* invalid or non-object payloads are rejected

At the public boundary, language codes must normalize to the API-facing form such as:

* `en`
* `fr`
* `pt`

Internal runtime spellings must not leak into the public HTTP envelope.

---

## 6. Public success response shape

The stable public success response uses one canonical top-level envelope.

The required top-level fields are:

* `text` — generated surface text
* `lang_code` — normalized output language code
* `construction_id` — realized construction identifier
* `renderer_backend` — backend that produced the final text
* `fallback_used` — whether fallback was used for the returned result
* `tokens` — tokenized surface output
* `debug_info` — structured runtime diagnostics and provenance
* `generation_time_ms` — top-level timing metadata

Example:

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
    "fallback_used": false,
    "slot_keys": ["subject", "profession", "nationality"],
    "selected_backend": "family",
    "attempted_backends": ["family"]
  },
  "generation_time_ms": 12.5
}
```

### Important response notes

* `text` is the authoritative public surface field
* clients must not depend on legacy public names such as `surface_text` or `meta`
* `construction_id` and `renderer_backend` are part of the canonical top level
* `generation_time_ms` is top-level and authoritative
* `debug_info` is observability data, not a substitute for the public top-level fields
* the same public envelope applies across supported languages
* clients must not branch by language or backend to interpret successful generation results

### Debug notes

`debug_info` always belongs to the public success envelope.

Stable debug keys include:

* `runtime_path`
* `construction_id`
* `renderer_backend`
* `lang_code`
* `fallback_used`
* `slot_keys`

Additional runtime diagnostics may also appear there, including:

* `selected_backend`
* `attempted_backends`
* `dispatch_policy`
* `backend_trace`
* `resolved_language`
* `lexical_resolution`
* `gf_function`
* `ast`
* `warnings`
* `fallback_reason`

Clients should use top-level fields for integration logic and treat `debug_info` as diagnostics.

---

## 7. Runtime model and migration note

The architectural target is a **planner-first runtime**:

1. canonical input is normalized into one internal frame/domain shape
2. the planner builds or selects the construction payload
3. lexical resolution may enrich the plan
4. the realizer returns the final surface result
5. the API serializes that result into the public success envelope

The nominal target-state runtime path is:

* **`planner_first`**

A compatibility path may still exist during migration windows, including:

* compatibility shims
* explicit fallback paths
* temporary legacy generation flows

Important rules:

* compatibility success still serializes to the same public envelope
* compatibility success is **not** the nominal target-state success path
* `fallback_used` must remain explicit
* path-specific observability belongs in `debug_info`
* clients should rely on the stable top-level fields, not on path-specific internals

---

## 8. Languages discovery

## `GET /api/v1/languages`

Used by the UI, smoke tooling, and validation utilities to discover available languages.

Client code in this repo already tolerates multiple response shapes, including:

* `{"supported_languages": ["en", "fr"]}`
* `{"languages": [{"code": "en"}, {"code": "fr"}]}`
* `{"langs": ["en", "fr"]}`
* `[{"code": "en"}, {"code": "fr"}]`
* `["en", "fr"]`

Clients should normalize these shapes rather than assuming a single historical payload form.

The existence of a language in this endpoint does not, by itself, imply full language readiness.

---

## 9. Entity and frame discovery endpoints

Entity-related browsing endpoints are mounted under:

* **`/api/v1/entities/...`**

Frame-related endpoints are mounted under:

* **`/api/v1/frames/...`**

These endpoints support schema/entity browsing and editor-style UI flows.

They are not the canonical meaning-to-text generation contract.

---

## 10. AI helper endpoints

AI helper endpoints are mounted under the same API prefix:

* **`/api/v1/ai/...`**

These are helper endpoints and are not the canonical generation contract.

Use `POST /api/v1/generate/{lang_code}` for stable meaning-to-text integration.

---

## 11. Session / discourse header

Some scripts, clients, and discourse-oriented flows use:

* `X-Session-ID`

This header may be used to preserve contextual continuity across calls when the active deployment/runtime path supports it.

Treat it as optional integration metadata, not as part of the semantic payload itself.

---

## 12. Tools API

Developer/system tools are mounted under:

* **`/api/v1/tools/...`**

### `GET /api/v1/tools/registry`

Returns metadata for registered tools.

### `POST /api/v1/tools/run`

Executes a registered tool and returns a structured execution envelope.

The tools router is the canonical owner of:

* request validation
* allowlist enforcement
* argument policy checks
* lifecycle envelope generation
* timeout behavior
* truncation behavior

### Security note

Do not place secrets in tool arguments.

Tool arguments may be:

* validated
* logged
* echoed
* truncated
* surfaced in operator-facing UIs

---

## 13. Health endpoints

Health endpoints are available at both:

* **`/health/live`**
* **`/health/ready`**
* **`/api/v1/health/live`**
* **`/api/v1/health/ready`**

Use the `/api/v1/health/...` form when you want the canonical API namespace.

Use the root-mounted `/health/...` form for deployment probes if your environment expects that layout.

---

## 14. Practical guidance for new clients

For new integrations:

1. call `GET /api/v1/languages`
2. choose a supported public language code
3. call `POST /api/v1/generate/{lang_code}` with a raw semantic payload
4. read `text` as the final output
5. use `lang_code`, `construction_id`, `renderer_backend`, `fallback_used`, and `generation_time_ms` as the stable public metadata
6. treat `debug_info` as diagnostics only

Prefer:

* `text` over legacy field names
* path language over body language
* raw semantic payloads over wrapped compatibility payloads
* planner-compatible stable fields over backend-specific internals
* the canonical public success envelope over any helper-library or frontend-local result shape

Do not build new integrations around:

* `surface_text`
* `meta`
* backend-specific ad hoc envelopes
* frontend-only result objects
* compatibility-only request forms when the canonical path endpoint is available

---

## 15. Final integration rule

There is exactly one canonical public success envelope for successful generation responses.

If two successful generation paths expose different top-level public shapes, the API contract is broken.

If a client can only understand generation success by inspecting backend-specific internals instead of the stable top-level public fields, the integration boundary is wrong.


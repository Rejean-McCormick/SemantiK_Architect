# API Overview

SemantiK Architect is exposed through a **versioned HTTP API**. The canonical application-facing prefix is:

- **`/api/v1`**

This page is the high-level integration overview. For the canonical success envelope returned by generation endpoints, see:

- `docs/contracts/public_generation_response_contract.md`

---

## API prefix and route mounting

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

## Core generation endpoints

## `POST /api/v1/generate/{lang}`

This is the canonical text-generation endpoint for stable clients.

Rules:

- `lang` is provided as a **path parameter**
- the request body carries the **meaning payload**
- if a language is also present in the body, it must normalize to the same value
- the response returns the generated surface text plus structured runtime metadata

The path language is authoritative.

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

---

## Compatibility generation endpoint

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

---

## Accepted request shapes

The generation layer accepts multiple request styles during migration.

### 1. Raw semantic payload

This is the preferred shape for current clients.

Post the semantic payload directly as the JSON body.

Examples include:

* flat bio-style payloads using `frame_type`
* normalized semantic frame payloads
* other frame families routed through frame normalization

Bio-like frame types are normalized through the bio compatibility path.

Recognized bio-like aliases include forms such as:

* `bio`
* `biography`
* `entity.person`
* `entity_person`
* `person`
* `entity.person.v1`
* `entity.person.v2`

### 2. Wrapped compatibility payload

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

### 3. Ninai / recursive meaning payload

If the payload contains a top-level `function` field, the request is treated as a Ninai-style recursive meaning payload and routed through the Ninai adapter path.

This path is still compatibility/prototype-oriented and should not be treated as the default production contract.

---

## Request normalization rules

Before generation, the API normalizes requests into a stable internal command.

Key rules:

* if the URL contains a language, it wins
* if both URL and payload contain a language, they must match after normalization
* transport-only language fields are stripped from the semantic payload
* recognized bio/person aliases are normalized before generation
* Ninai payloads are parsed through the adapter path
* invalid or non-object payloads are rejected

---

## Public success response shape

The stable public success response is centered on these top-level fields:

* `text` — generated surface text
* `lang_code` — normalized output language code
* `construction_id` — realized construction identifier when available
* `renderer_backend` — backend that produced the final text
* `fallback_used` — whether fallback was used for the returned result
* `tokens` — tokenized surface output
* `debug_info` — structured runtime diagnostics and provenance
* `generation_time_ms` — timing metadata when available on the active path

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
    "construction_id": "copula_equative_classification",
    "renderer_backend": "family",
    "lang_code": "en",
    "fallback_used": false,
    "selected_backend": "family",
    "attempted_backends": ["family"]
  },
  "generation_time_ms": 12.5
}
```

### Important response notes

* `text` is the authoritative public surface field
* clients should not depend on older names such as `surface_text` or `meta`
* `debug_info` is observability data, not a substitute for the public top-level fields
* legacy code may still refer internally to `Sentence`, while planner-runtime code prefers `SurfaceResult`; both converge on the same public HTTP shape

---

## Runtime status and migration note

The architectural target is a **planner-first runtime**:

1. planner builds or selects the construction payload
2. lexical resolution may enrich the plan
3. the realizer returns the final surface result
4. the API serializes that result into the public success envelope

A compatibility path still exists for migration-era flows, including legacy direct frame-based generation.

Because of that, clients may still observe runtime metadata such as:

* `runtime_path`
* `selected_backend`
* `attempted_backends`
* `dispatch_policy`
* `backend_trace`
* `resolved_language`
* `ast`

Those belong in `debug_info`.

Clients should rely on the top-level public fields for integration logic.

---

## Languages discovery

## `GET /api/v1/languages`

Used by the UI, smoke tooling, and validation utilities to discover available languages.

Clients in this repo already tolerate multiple response shapes, including:

* `{"supported_languages": ["en", "fr"]}`
* `{"languages": [{"code": "en"}, {"code": "fr"}]}`
* `{"langs": ["en", "fr"]}`
* `[{"code": "en"}, {"code": "fr"}]`
* `["en", "fr"]`

Client code should normalize these shapes rather than assuming a single historical payload form.

---

## Entity and frame discovery endpoints

Entity-related browsing endpoints are mounted under:

* **`/api/v1/entities/...`**

Frame-related endpoints are mounted under:

* **`/api/v1/frames/...`**

These endpoints support schema/entity browsing and editor-style UI flows.

---

## AI helper endpoints

AI helper endpoints are mounted under the same API prefix:

* **`/api/v1/ai/...`**

These are helper endpoints and are not the canonical generation contract.

Use `/api/v1/generate/{lang}` for stable meaning-to-text integration.

---

## Session / discourse header

Some scripts, clients, and discourse-oriented flows use:

* `X-Session-ID`

This header may be used to preserve contextual continuity across calls when the active deployment/runtime path supports it.

Treat it as optional integration metadata, not as part of the semantic payload itself.

---

## Tools API

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
* timeout / truncation behavior

### Security note

Do not place secrets in tool arguments.

Tool arguments may be:

* validated
* logged
* echoed
* truncated
* surfaced in operator-facing UIs

---

## Health endpoints

Health endpoints are available at both:

* **`/health/live`**
* **`/health/ready`**
* **`/api/v1/health/live`**
* **`/api/v1/health/ready`**

Use the `/api/v1/health/...` form when you want the canonical API namespace.
Use the root-mounted `/health/...` form for deployment probes if your environment expects that layout.

---

## Practical guidance for new clients

For new integrations:

1. call `GET /api/v1/languages`
2. choose a supported language code
3. call `POST /api/v1/generate/{lang}` with a raw semantic payload
4. read `text` as the final output
5. treat `debug_info` as diagnostics only

Prefer:

* `text` over legacy field names
* path language over body language
* raw semantic payloads over wrapped compatibility payloads
* planner-compatible stable fields over backend-specific internals


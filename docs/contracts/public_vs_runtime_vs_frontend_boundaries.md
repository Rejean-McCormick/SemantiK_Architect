# Public vs Runtime vs Frontend Boundaries

Status: normative  
Owner: API / Runtime / Frontend  
Scope: boundary rules between internal runtime contracts, the public HTTP generation contract, and the frontend-facing generation API

---

## 1. Purpose

This document defines the boundary between three different contract layers in SemantiK Architect:

1. **internal runtime contracts**
2. **public HTTP generation contracts**
3. **frontend-facing generation API contracts**

These layers are related, but they are **not the same object model** and they must not drift into each other.

This document exists to prevent the following recurring failure modes:

- documenting internal runtime objects as if they were public HTTP payloads,
- letting frontend convenience models become the canonical API contract,
- leaking planner or renderer internals across the HTTP boundary,
- creating incompatible success shapes across API, runtime, and frontend code.

---

## 2. Final rule

There are three distinct boundary layers:

- **runtime** = internal generation contracts used inside the planning and realization pipeline
- **public API** = canonical HTTP transport contract returned by `/api/v1/generate...`
- **frontend API** = higher-level client/session API used by frontend-oriented callers such as `nlg.api`

If a field, shape, or responsibility belongs to one layer, it does not automatically belong to the others.

---

## 3. Why this distinction exists

The repository already documents and implements a planner-first runtime centered on:

```text
frame -> PlannedSentence -> ConstructionPlan -> SurfaceResult
````

The repository also maps internal generation results to a stable public API response, and separately exposes frontend-friendly generation helpers that return a different object model.   

Therefore:

* `SurfaceResult` is a **runtime object**
* the `/api/v1/generate...` response is a **public transport object**
* `nlg.api.GenerationResult` is a **frontend/client convenience object**

They may be derived from one another, but they are not interchangeable.

---

## 4. Layer definitions

## 4.1 Runtime layer

The runtime layer is the internal planner/realizer contract space.

Typical runtime objects include:

* `PlannedSentence`
* `ConstructionPlan`
* `slot_map`
* `lexical_bindings`
* `SurfaceResult`
* runtime `debug_info`

The runtime layer is responsible for:

* interpreting normalized semantic intent,
* selecting and preserving canonical `construction_id`,
* carrying `lang_code`,
* resolving lexical material,
* selecting or attempting renderer backends,
* producing realized surface text plus runtime metadata.

The runtime layer is **not** the HTTP transport contract.  

---

## 4.2 Public HTTP API layer

The public HTTP API layer is the canonical transport contract returned by generation routes such as:

```text
POST /api/v1/generate/{lang_code}
POST /api/v1/generate
```

This layer is the stable client-facing envelope.

Its job is to expose a clean mapped view of generation results without leaking the full internal runtime model.

The public API response is an external serialization boundary. It is not the planner contract, not the renderer contract, and not the frontend session object.  

---

## 4.3 Frontend-facing generation API layer

The frontend-facing generation API layer is the higher-level developer/client interface represented by `nlg.api`.

Its `GenerationResult` is designed for frontend or client use and includes fields such as:

* `text`
* `sentences`
* `lang`
* `frame`
* `debug_info`

It is a convenience/session-facing object, not the canonical HTTP transport contract. Debug payload exposure is also conditional there via `debug=True`.  

---

## 5. Source of truth and precedence

If two documents or code paths disagree, precedence is:

1. **runtime contract docs** for internal planning/realization ownership
2. **public generation response contract** for HTTP success serialization
3. **this document** for layer separation and ownership
4. **frontend convenience APIs** for frontend/client usage only

More explicitly:

* if the issue is about `ConstructionPlan`, `SurfaceResult`, lexical bindings, or planner/realizer responsibilities, the runtime contracts win;
* if the issue is about HTTP success payload shape, the public generation response contract wins;
* if the issue is about whether a field belongs to runtime vs HTTP vs frontend, this document wins;
* if a frontend helper returns a different shape, that does not redefine the public HTTP contract.

---

## 6. Canonical flow across boundaries

The intended end-to-end flow is:

```text
HTTP request
  -> request normalization
  -> frame/domain form
  -> planning
  -> lexical resolution
  -> realization
  -> SurfaceResult
  -> public response mapping
  -> HTTP JSON response
```

Separately, a frontend/session caller may use:

```text
frame
  -> nlg.api generate(...)
  -> engine/session adapter
  -> text/sentences/debug convenience result
```

These are related flows, but they terminate in different object models.  

---

## 7. Boundary table

| Layer        | Canonical object(s)                                    | Primary audience                                | Stable purpose                 | Must not be confused with                          |
| ------------ | ------------------------------------------------------ | ----------------------------------------------- | ------------------------------ | -------------------------------------------------- |
| Runtime      | `PlannedSentence`, `ConstructionPlan`, `SurfaceResult` | planner, lexical resolver, renderers, use cases | internal generation ownership  | HTTP payloads, frontend helper results             |
| Public API   | public generation response JSON                        | external clients, integrations, tests           | stable HTTP transport envelope | internal runtime objects, frontend session objects |
| Frontend API | `nlg.api.GenerationResult`                             | frontend/client code, CLI-style callers         | convenience/session model      | canonical HTTP success envelope                    |

---

## 8. What belongs to the runtime layer

The following belong to the runtime layer and are not public top-level HTTP fields by default:

* `PlannedSentence`
* `ConstructionPlan`
* `slot_map`
* `lexical_bindings`
* planner-specific metadata
* renderer-dispatch internals beyond approved debug exposure
* entity/lexeme references as runtime objects
* backend-specific realizer inputs

The runtime layer may carry these internally even when the public API only exposes a mapped summary.  

---

## 9. What belongs to the public HTTP layer

The public HTTP success contract is centered on a stable mapped envelope, including fields such as:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `tokens`
* `debug_info`
* `generation_time_ms`

These are transport-facing fields intended for clients and integration tests.

This layer exists precisely so clients do not need to know the full runtime object graph.  

---

## 10. What belongs to the frontend-facing layer

The frontend-facing `nlg.api.GenerationResult` contains convenience-oriented fields such as:

* `text`
* `sentences`
* `lang`
* `frame`
* `debug_info`

This object is appropriate for:

* UI/session code,
* CLI helpers,
* higher-level local callers that want sentence splitting fallback and request options attached to debug output.

It is not appropriate to document this object as the public HTTP generation response.  

---

## 11. Field ownership matrix

| Field                | Runtime layer | Public HTTP layer | Frontend layer | Notes                                                                   |
| -------------------- | ------------- | ----------------- | -------------- | ----------------------------------------------------------------------- |
| `text`               | yes           | yes               | yes            | shared concept across all layers                                        |
| `lang_code`          | yes           | yes               | no             | frontend convenience API uses `lang` instead                            |
| `lang`               | no            | no                | yes            | frontend/client convenience field                                       |
| `construction_id`    | yes           | yes               | no             | frontend layer does not define it as a stable top-level field           |
| `renderer_backend`   | yes           | yes               | no             | may be exposed through debug in frontend flows only if carried through  |
| `fallback_used`      | yes           | yes               | no             | not a canonical top-level frontend field                                |
| `tokens`             | yes           | yes               | no             | frontend convenience API prefers `sentences`, not tokens                |
| `sentences`          | no            | no                | yes            | frontend/session convenience field                                      |
| `frame`              | no            | no                | yes            | convenience echo for frontend/session callers                           |
| `slot_map`           | yes           | no                | no             | runtime-only                                                            |
| `lexical_bindings`   | yes           | no                | no             | runtime-only unless summarized in debug                                 |
| `debug_info`         | yes           | yes               | yes            | but rules differ by layer                                               |
| `generation_time_ms` | yes           | yes               | no             | frontend convenience API does not define it as a stable top-level field |

---

## 12. Debug information boundary rules

## 12.1 Runtime debug

Runtime `debug_info` may contain rich internal provenance, including:

* selected backend
* attempted backends
* construction identity
* dispatch policy
* fallback reason
* lexical resolution metadata
* backend-specific details such as AST or resolved GF language

This is an internal diagnostic structure first. 

## 12.2 Public API debug

Public API `debug_info` is a mapped client-visible diagnostic object.

It should expose stable keys required by the public response contract while avoiding arbitrary leakage of internal transport-irrelevant structures.

The public boundary may surface selected runtime diagnostics, but only as deliberate mapped output.

## 12.3 Frontend debug

In `nlg.api`, `debug_info` is included only when the caller enables `debug=True`.

Therefore, frontend debug visibility is conditional, even if runtime and HTTP layers may always carry debug metadata internally. 

---

## 13. Language code boundary rules

Language code handling differs by layer and must be kept explicit.

### Runtime

The runtime and some tests may use normalized internal codes such as `eng` or other internal conventions where appropriate. 

### Public API

The public API should expose one stable client-facing `lang_code` convention, such as `en`, `fr`, etc., regardless of internal normalization details. 

### Frontend

The frontend-facing generation API uses `lang`, not `lang_code`, because it is a convenience/session-facing interface rather than the public HTTP transport contract. 

---

## 14. Request boundary rules

Boundary separation applies to requests as well as responses.

### 14.1 External HTTP compatibility ends at normalization

The request mapper may accept compatibility shapes, aliases, and legacy input forms, including multiple language-field spellings and bio-like frame aliases.

That compatibility is an API-ingest concern.

It ends at normalization. Downstream runtime code must not consume transport quirks as if they were runtime contracts.  

### 14.2 Frontend inputs do not redefine runtime contracts

A frontend/session caller may pass a `frame` object and a `lang` string into `nlg.api.generate(...)`.

That convenience signature does not redefine the HTTP request contract or the runtime planner contract. 

---

## 15. Anti-drift rules

The following are prohibited:

### 15.1 Runtime leakage into HTTP top level

Do not expose these as top-level public response fields unless a specific public contract is adopted for them:

* `slot_map`
* `lexical_bindings`
* raw planner structures
* raw entity/lexeme refs
* backend-local intermediate objects

### 15.2 Frontend leakage into HTTP top level

Do not redefine the public HTTP success envelope around frontend convenience fields such as:

* `sentences`
* `frame`
* `lang`

### 15.3 HTTP transport leakage into runtime ownership

Do not let public transport concerns dictate runtime object ownership, naming, or planner/realizer boundaries.

### 15.4 Compatibility leakage past normalization

Legacy payload quirks and wrapper variants must stop at API normalization.

---

## 16. Examples

## 16.1 Internal runtime result

```python
SurfaceResult(
    text="Alan Turing est un mathématicien britannique.",
    lang_code="fr",
    construction_id="copula_equative_classification",
    renderer_backend="gf",
    fallback_used=False,
    debug_info={
        "construction_id": "copula_equative_classification",
        "renderer_backend": "gf",
        "lang_code": "fr",
        "fallback_used": False,
        "resolved_language": "WikiFre",
    },
)
```

This is a runtime object, not the HTTP contract. 

## 16.2 Public HTTP response

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
    "slot_keys": ["subject", "predicate_nominal"]
  },
  "generation_time_ms": 12.5
}
```

This is the client-facing transport envelope.  

## 16.3 Frontend-facing generation result

```python
GenerationResult(
    text="Alan Turing is a British mathematician.",
    sentences=["Alan Turing is a British mathematician."],
    lang="en",
    frame=<frame object>,
    debug_info={"options": {"register": "formal"}}
)
```

This is a frontend/client convenience object, not the public HTTP success shape. 

---

## 17. Directory map

| Path                                                       | Boundary role                                      |
| ---------------------------------------------------------- | -------------------------------------------------- |
| `app/adapters/api/contracts/generation_request_mapper.py`  | HTTP ingest normalization boundary                 |
| `app/adapters/api/contracts/generation_response_mapper.py` | runtime-to-public response mapping boundary        |
| `app/adapters/api/routers/generation.py`                   | public HTTP entry point                            |
| `app/adapters/engines/construction_realizer.py`            | runtime realization and `SurfaceResult` production |
| `docs/contracts/construction_runtime_contract.md`          | runtime contract authority                         |
| `docs/contracts/public_generation_response_contract.md`    | public HTTP success contract authority             |
| `nlg/api.py`                                               | frontend/client convenience API                    |
| `architect_frontend/src/lib/api.ts`                        | browser-side API client/type layer                 |
| `architect_frontend/src/components/GenerationResult.tsx`   | UI rendering of frontend-side generation data      |

---

## 18. Change policy

Any change must answer this question first:

**Which boundary layer owns this field or behavior?**

If the answer is unclear, the change must not proceed until ownership is documented.

### 18.1 If adding a runtime field

Update runtime contracts and decide whether it:

* stays internal,
* appears only in `debug_info`,
* or is promoted into the public HTTP contract.

### 18.2 If adding a public HTTP field

Update:

* `public_generation_response_contract.md`
* API docs
* response mapper
* tests for the public envelope

### 18.3 If adding a frontend convenience field

Update:

* frontend/client types
* `nlg.api` docs
* UI consumers

Do not silently add it to the HTTP contract unless explicitly approved.

---

## 19. Acceptance criteria

This document is considered adopted when:

1. the runtime contract is documented as internal,
2. the public HTTP success envelope is documented separately,
3. the frontend-facing `GenerationResult` is documented separately,
4. no doc presents `SurfaceResult` as the public HTTP response object,
5. no doc presents frontend convenience fields as canonical HTTP fields,
6. compatibility payload handling is explicitly limited to normalization,
7. tests and examples respect the boundary between `lang_code` and `lang`.

---

## 20. Summary

SemantiK Architect has three valid but different views of generation output:

* an **internal runtime view**,
* a **public HTTP transport view**,
* a **frontend/client convenience view**.

They must stay aligned in meaning, but they must not collapse into one undifferentiated contract.

That separation is what keeps planner-first runtime architecture, public API stability, and frontend ergonomics all possible at the same time.



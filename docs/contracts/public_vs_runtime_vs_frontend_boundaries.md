Voici la version mise à jour.

# Public vs Runtime vs Frontend Boundaries

Status: normative
Owner: API / Runtime / Frontend
Scope: boundary rules between internal runtime contracts, the public HTTP generation contract, and frontend-facing generation APIs and clients

---

## 1. Purpose

This document defines the boundary between three distinct contract layers in SemantiK Architect:

1. **internal runtime contracts**
2. **public HTTP generation contracts**
3. **frontend-facing generation APIs and client models**

These layers are related, but they are **not the same object model** and they must not drift into each other.

This document exists to prevent the following failure modes:

* documenting internal runtime objects as if they were public HTTP payloads,
* letting frontend convenience models become the canonical API contract,
* leaking planner, lexical, or renderer internals across the HTTP boundary,
* creating incompatible success shapes across runtime, API, frontend, and tests,
* and allowing the response mapper to become the place where nominal planner-first truth is invented for the first time.

---

## 2. Final rule

There are three distinct boundary layers:

* **runtime** = internal generation contracts used inside the planner-first planning and realization pipeline,
* **public API** = canonical HTTP transport contract returned by `/api/v1/generate...`,
* **frontend layer** = frontend/client-facing models, typed clients, and convenience APIs used by browser code, session helpers, or local developer-facing wrappers.

If a field, shape, or responsibility belongs to one layer, it does not automatically belong to the others.

A layer may derive from another layer, but derivation does not erase ownership.

---

## 3. Why this distinction exists

The final runtime architecture is planner-first and centered on:

```text
canonical input
  -> normalized frame/domain shape
  -> planner
  -> lexical resolution
  -> realizer
  -> SurfaceResult
```

The public API then serializes a stable HTTP success envelope from that runtime result.

Separately, frontend and client-facing code may either:

* consume the canonical public HTTP envelope directly, or
* map it into local convenience objects for UI/session use.

Therefore:

* `ConstructionPlan` and `SurfaceResult` are **runtime objects**,
* the `/api/v1/generate...` success payload is the **public transport object**,
* frontend/client models may mirror or adapt the public payload, but they are **not automatically the canonical public contract**.

---

## 4. Boundary model

## 4.1 Runtime layer

The runtime layer is the internal planner/realizer contract space.

Typical runtime objects include:

* `PlannedSentence`
* `ConstructionPlan`
* `slot_map`
* `lexical_bindings`
* runtime `debug_info`
* `SurfaceResult`

The runtime layer is responsible for:

* interpreting normalized semantic intent,
* selecting and preserving canonical `construction_id`,
* carrying canonical `lang_code`,
* resolving lexical material,
* selecting or attempting renderer backends,
* producing realized surface text plus runtime metadata,
* and returning a complete runtime result on the nominal planner-first path.

The runtime layer is **not** the HTTP transport contract.

## 4.2 Public HTTP API layer

The public HTTP API layer is the canonical transport contract returned by generation routes such as:

```text
POST /api/v1/generate/{lang_code}
POST /api/v1/generate
```

This layer is the stable client-facing envelope.

Its job is to expose a clean mapped view of generation results without leaking the full internal runtime model.

The public API response is an external serialization boundary. It is not:

* the planner contract,
* the renderer contract,
* the lexical resolver contract,
* or a frontend session convenience object.

## 4.3 Frontend/client layer

The frontend/client layer is the developer-facing or UI-facing consumption layer.

It includes two legitimate patterns:

1. **thin clients** that consume the canonical public HTTP contract as-is, and
2. **convenience models** that adapt public results into session/UI-oriented objects.

Examples include:

* browser-side typed clients,
* UI rendering components,
* local helper APIs such as `nlg.api`,
* CLI-style or session-style convenience wrappers.

This layer may expose convenience fields such as:

* `lang`
* `sentences`
* `frame`
* request options
* UI/session-local debug structures

These convenience fields do not redefine the public HTTP generation contract.

---

## 5. Source of truth and precedence

If two documents or code paths disagree, precedence is:

1. **runtime architecture and runtime contract docs** for internal planning/realization ownership,
2. **public generation response contract** for HTTP success serialization,
3. **this document** for layer separation and field ownership,
4. **frontend/client models and helpers** for frontend/client usage only.

More explicitly:

* if the issue is about `ConstructionPlan`, `SurfaceResult`, planner responsibilities, lexical resolution, renderer ownership, or runtime metadata ownership, the runtime contract layer wins;
* if the issue is about the HTTP success envelope, the public generation response contract wins;
* if the issue is about whether a field belongs to runtime vs public HTTP vs frontend/client, this document wins;
* if a frontend helper returns a different shape, that does not redefine the public HTTP contract.

---

## 6. Canonical flow across boundaries

The intended end-to-end public flow is:

```text
HTTP request
  -> request normalization
  -> canonical frame/domain form
  -> planning
  -> lexical resolution
  -> realization
  -> SurfaceResult
  -> public response mapping
  -> HTTP JSON response
```

The critical boundary rule is:

> On the nominal planner-first path, runtime truth must already exist before public response mapping.

That means:

* the planner/realizer path must produce a complete runtime result,
* the response mapper serializes and normalizes public output,
* the response mapper must not be the place where nominal `construction_id`, `renderer_backend`, or `fallback_used` first become true.

Separately, a frontend/client flow may be:

```text
public HTTP response
  -> typed browser/client layer
  -> optional frontend/session adaptation
  -> UI/session object
```

Or, for local convenience APIs:

```text
frame
  -> local helper API
  -> runtime or HTTP adapter
  -> convenience result
```

These flows are related, but they terminate in different object models.

---

## 7. Boundary table

| Layer           | Canonical object(s)                                           | Primary audience                                  | Stable purpose                 | Must not be confused with                          |
| --------------- | ------------------------------------------------------------- | ------------------------------------------------- | ------------------------------ | -------------------------------------------------- |
| Runtime         | `PlannedSentence`, `ConstructionPlan`, `SurfaceResult`        | planner, lexical resolver, renderers, use cases   | internal generation ownership  | HTTP payloads, frontend/client convenience objects |
| Public API      | public generation response JSON                               | external clients, integrations, API tests         | stable HTTP transport envelope | internal runtime objects, frontend session objects |
| Frontend/client | typed API clients, UI/session models, `nlg.api`-style helpers | browser code, UI components, local client callers | consumption convenience        | canonical HTTP success envelope, runtime contracts |

---

## 8. What belongs to the runtime layer

The following belong to the runtime layer and are not public top-level HTTP fields by default:

* `PlannedSentence`
* `ConstructionPlan`
* `slot_map`
* `lexical_bindings`
* planner-specific metadata
* lexical-resolution internals
* renderer-dispatch internals beyond approved public debug exposure
* entity or lexeme references as runtime objects
* backend-specific realizer inputs
* backend-local intermediate objects

The runtime layer may carry these internally even when the public API exposes only a mapped summary.

---

## 9. What belongs to the public HTTP layer

The public HTTP success contract is centered on a stable mapped envelope, including:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `tokens`
* `debug_info`
* `generation_time_ms`

These are transport-facing fields intended for clients and integration tests.

This layer exists so clients do not need to know the full runtime object graph.

---

## 10. What belongs to the frontend/client layer

Frontend/client-facing models may contain convenience-oriented fields such as:

* `text`
* `sentences`
* `lang`
* `frame`
* request options
* UI/session-local status fields
* conditionally exposed `debug_info`

These objects are appropriate for:

* browser-side state,
* UI rendering,
* session wrappers,
* CLI helpers,
* local convenience APIs.

They are not appropriate to document as the canonical public HTTP generation response unless they exactly mirror that public envelope without adding ownership drift.

---

## 11. Field ownership matrix

| Field                | Runtime layer | Public HTTP layer | Frontend/client layer | Notes                                                                              |
| -------------------- | ------------- | ----------------- | --------------------- | ---------------------------------------------------------------------------------- |
| `text`               | yes           | yes               | yes                   | shared concept across all layers                                                   |
| `lang_code`          | yes           | yes               | optional              | frontend thin clients may mirror it; convenience layers may adapt it               |
| `lang`               | no            | no                | yes                   | convenience field, not the public HTTP canonical name                              |
| `construction_id`    | yes           | yes               | optional              | frontend may carry it only if explicitly mirroring the public contract             |
| `renderer_backend`   | yes           | yes               | optional              | frontend may carry it only if explicitly mirroring the public contract             |
| `fallback_used`      | yes           | yes               | optional              | not a required convenience field unless mirroring public transport                 |
| `tokens`             | yes           | yes               | optional              | frontend may consume them, but must not replace the HTTP contract with `sentences` |
| `sentences`          | no            | no                | yes                   | convenience/session field                                                          |
| `frame`              | no            | no                | yes                   | convenience echo for local callers                                                 |
| `slot_map`           | yes           | no                | no                    | runtime-only                                                                       |
| `lexical_bindings`   | yes           | no                | no                    | runtime-only unless deliberately summarized                                        |
| `debug_info`         | yes           | yes               | optional              | rules differ by layer                                                              |
| `generation_time_ms` | yes           | yes               | optional              | frontend may mirror it, but it is not a frontend-owned convenience concept         |

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

It must expose stable keys required by the public response contract while avoiding arbitrary leakage of internal structures that do not belong at the transport boundary.

Public `debug_info` must never contradict top-level public fields.

## 12.3 Frontend/client debug

Frontend/client debug exposure is a consumption concern.

A frontend/client helper may:

* pass public `debug_info` through,
* suppress it,
* conditionally expose it,
* or augment it with client-local metadata.

That convenience behavior does not redefine runtime ownership or the public contract.

---

## 13. Top-level vs debug parity rules

Where the public contract exposes a field at top level and also echoes it in `debug_info`, the top-level field is authoritative.

At minimum:

* top-level `lang_code` and `debug_info.lang_code` must not conflict,
* top-level `fallback_used` and `debug_info.fallback_used` must not conflict,
* top-level `construction_id` and `debug_info.construction_id` must not conflict when both are present,
* top-level `renderer_backend` and `debug_info.renderer_backend` must not conflict when both are present,
* top-level `generation_time_ms` is authoritative and must not be displaced by a debug-only value.

This parity rule applies to public serialization, tests, and acceptance validation.

---

## 14. Language code boundary rules

Language code handling differs by layer and must be kept explicit.

### Runtime

The runtime owns canonical internal language identity for planning and realization and returns canonical runtime `lang_code`.

### Public API

The public API exposes one stable client-facing `lang_code` convention, such as `en`, `fr`, etc.

Internal routing or GF-specific details do not redefine the public field name or shape.

### Frontend/client

Frontend/client convenience layers may expose `lang`, but that is a convenience adaptation, not the public HTTP canonical field name.

Thin clients that mirror the public HTTP envelope may also keep `lang_code` unchanged.

---

## 15. Request boundary rules

Boundary separation applies to requests as well as responses.

## 15.1 External HTTP compatibility ends at normalization

The request mapper may accept compatibility shapes, aliases, and legacy input forms, including:

* multiple language-field spellings,
* compatibility wrapper forms,
* legacy bio-like aliases,
* transport-specific quirks.

That compatibility is an API-ingest concern.

It ends at normalization.

Downstream runtime code must not consume transport quirks as if they were runtime contracts.

## 15.2 Frontend/client inputs do not redefine runtime contracts

A frontend/session caller may pass a convenience `frame` object and a `lang` string into a helper API.

That convenience signature does not redefine:

* the HTTP request contract,
* the runtime planner contract,
* or the canonical normalized internal shape.

---

## 16. Anti-drift rules

The following are prohibited.

## 16.1 Runtime leakage into HTTP top level

Do not expose these as top-level public response fields unless a specific public contract is explicitly adopted for them:

* `slot_map`
* `lexical_bindings`
* raw planner structures
* raw entity or lexeme refs
* backend-local intermediate objects
* raw realizer inputs

## 16.2 Frontend leakage into HTTP top level

Do not redefine the public HTTP success envelope around frontend convenience fields such as:

* `sentences`
* `frame`
* `lang`
* UI/session-local request options

## 16.3 HTTP transport leakage into runtime ownership

Do not let transport concerns dictate runtime object ownership, planner boundaries, or renderer boundaries.

## 16.4 Compatibility leakage past normalization

Legacy payload quirks and wrapper variants must stop at API normalization.

## 16.5 Mapper-created nominal truth

Do not treat the response mapper as the place where nominal planner-first success becomes structurally valid for the first time.

On the nominal path, required public fields must already exist in the runtime result before mapping.

The mapper may normalize and serialize. It must not silently invent missing nominal truth.

---

## 17. Examples

## 17.1 Internal runtime result

```python
SurfaceResult(
    text="Alan Turing est un mathématicien britannique.",
    lang_code="fr",
    construction_id="copula_equative_classification",
    renderer_backend="gf",
    fallback_used=False,
    tokens=["Alan", "Turing", "est", "un", "mathématicien", "britannique."],
    debug_info={
        "runtime_path": "planner_first",
        "construction_id": "copula_equative_classification",
        "renderer_backend": "gf",
        "lang_code": "fr",
        "fallback_used": False,
        "resolved_language": "WikiFre",
    },
    generation_time_ms=12.5,
)
```

This is a runtime object, not the HTTP contract.

## 17.2 Public HTTP response

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

This is the client-facing transport envelope.

## 17.3 Frontend/client convenience result

```python
GenerationResult(
    text="Alan Turing is a British mathematician.",
    sentences=["Alan Turing is a British mathematician."],
    lang="en",
    frame=<frame object>,
    debug_info={"options": {"register": "formal"}}
)
```

This is a frontend/client convenience object, not the canonical HTTP success shape.

---

## 18. Directory map

| Path                                                         | Boundary role                                      |
| ------------------------------------------------------------ | -------------------------------------------------- |
| `app/adapters/api/contracts/generation_request_mapper.py`    | HTTP ingest normalization boundary                 |
| `app/adapters/api/contracts/generation_response_mapper.py`   | runtime-to-public response mapping boundary        |
| `app/adapters/api/routers/generation.py`                     | public HTTP entry point                            |
| `app/core/use_cases/generate_text.py`                        | planner-first orchestration boundary               |
| `app/core/use_cases/realize_text.py`                         | runtime realization boundary                       |
| `app/adapters/engines/construction_realizer.py`              | runtime realization and `SurfaceResult` production |
| `docs/contracts/construction_runtime_contract.md`            | runtime contract authority                         |
| `docs/contracts/public_generation_response_contract.md`      | public HTTP success contract authority             |
| `docs/contracts/public_vs_runtime_vs_frontend_boundaries.md` | boundary ownership authority                       |
| `nlg/api.py`                                                 | frontend/client convenience API                    |
| `architect_frontend/src/lib/api.ts`                          | browser-side API client/type layer                 |
| `architect_frontend/src/components/GenerationResult.tsx`     | UI rendering of frontend-side generation data      |

---

## 19. Change policy

Any change must answer this question first:

**Which boundary layer owns this field or behavior?**

If the answer is unclear, the change must not proceed until ownership is documented.

## 19.1 If adding a runtime field

Update runtime contracts and decide whether it:

* stays internal,
* appears only in mapped public `debug_info`,
* is mirrored by frontend thin clients,
* or is promoted into the public HTTP contract.

## 19.2 If adding a public HTTP field

Update:

* `public_generation_response_contract.md`
* API reference docs
* response mapper
* public HTTP tests
* acceptance/evaluator checks when relevant

## 19.3 If adding a frontend/client convenience field

Update:

* frontend/client types
* `nlg.api` or equivalent helper docs
* UI consumers

Do not silently add it to the HTTP contract unless explicitly approved.

---

## 20. Acceptance criteria

This document is considered adopted when:

1. the runtime contract is documented as internal,
2. the public HTTP success envelope is documented separately,
3. frontend/client convenience models are documented separately,
4. no doc presents `SurfaceResult` as the public HTTP response object,
5. no doc presents frontend convenience fields as canonical HTTP fields,
6. compatibility payload handling is explicitly limited to normalization,
7. the mapper is documented as a serialization boundary rather than the source of nominal planner-first truth,
8. public top-level fields and `debug_info` parity rules are documented,
9. tests and examples respect the boundary between `lang_code` and `lang`.

---

## 21. Summary

SemantiK Architect has three valid but different views of generation output:

* an **internal runtime view**,
* a **public HTTP transport view**,
* a **frontend/client consumption view**.

They must stay aligned in meaning, but they must not collapse into one undifferentiated contract.

That separation is what keeps planner-first runtime architecture, public API stability, and frontend ergonomics simultaneously possible.

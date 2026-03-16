# Generation Path Serialization Matrix

Status: normative  
Owner: Runtime / API  
Scope: how each generation runtime path MUST serialize into the public success response envelope

---

## 1. Purpose

This document defines the **path-by-path serialization matrix** for successful text generation.

It exists to make one thing explicit:

> Different runtime paths may exist during migration, but they must still serialize into one stable public success envelope.

This document complements:

- `public_generation_response_contract.md`
- `construction_runtime_contract.md`
- `debug_info_contract.md`

This document does **not** define the error envelope.  
It covers only **successful generation results**.

---

## 2. Core rule

There is exactly one canonical public success envelope for generation results.

Every successful path MUST serialize the following top-level fields:

- `text`
- `lang_code`
- `construction_id`
- `renderer_backend`
- `fallback_used`
- `tokens`
- `debug_info`
- `generation_time_ms`

No successful path may replace this envelope with:

- `surface_text`
- `meta`
- backend-local ad hoc payloads
- legacy one-off transport shapes

---

## 3. What counts as a “generation path”

For this document, a generation path is the runtime route by which a successful sentence reaches the public API boundary.

The relevant success-path classes are:

1. planner-first direct success
2. planner-first success with runtime backend fallback
3. planner configured, but planner runtime falls back to legacy engine
4. legacy engine direct success when planner runtime is not configured
5. migration-era direct-frame / compatibility-shim success

These paths may differ internally, but not at the public envelope level.

---

## 4. Serialization dimensions

Each success path is evaluated against the following dimensions:

- **public envelope shape**
- **`debug_info.runtime_path`**
- **backend identity**
- **fallback visibility**
- **attempt trace**
- **construction identity**
- **language normalization**
- **token behavior**
- **timing behavior**
- **path-specific debug requirements**

---

## 5. Canonical matrix

| Path class | Typical runtime condition | Required public top-level shape | Required `debug_info.runtime_path` | `renderer_backend` | `fallback_used` | `attempted_backends` | `generation_time_ms` | Path-specific required debug markers |
|---|---|---|---|---|---|---|---|---|
| Planner-first direct / family | planner + realizer succeed; selected backend is family | canonical success envelope | `planner_first` | `family` | `false` unless child fallback is explicitly reported | exactly `["family"]` when no dispatch fallback occurred | numeric; SHOULD be real measured elapsed time | `selected_backend`, `attempted_backends`, `backend_trace`, `dispatch_policy` |
| Planner-first direct / GF | planner + realizer succeed; selected backend is GF | canonical success envelope | `planner_first` | `gf` | `false` unless child fallback is explicitly reported | exactly `["gf"]` when no dispatch fallback occurred | numeric; SHOULD be real measured elapsed time | `selected_backend`, `attempted_backends`, `backend_trace`, optional GF-specific fields such as `resolved_language`, `gf_function`, `ast` |
| Planner-first direct / safe mode | planner + realizer succeed; selected backend is safe mode | canonical success envelope | `planner_first` | `safe_mode` | `false` only if safe mode was the explicitly selected non-fallback runtime; otherwise `true` | MUST reflect actual attempted order | numeric; MAY be `0.0` if precise timing is unavailable | `selected_backend`, `attempted_backends`, `backend_trace`, safe-mode strategy markers when available |
| Planner-first dispatch fallback | planner succeeded, but backend dispatch selected a different backend after support/capability failure or runtime failure | canonical success envelope | `planner_first` | final backend actually used | `true` | MUST contain more than one entry when a different backend was tried before the final backend | numeric | `selected_backend`, `attempted_backends`, `backend_trace`, `dispatch_policy`; SHOULD include reason/context for fallback in debug metadata |
| Legacy-engine fallback | planner runtime was configured but failed; system fell back to legacy engine | canonical success envelope | `legacy_engine_fallback` | final backend exposed by legacy result or inferred serializer | `true` | MAY be absent in older shims, but SHOULD be present | numeric; MAY default to `0.0` during migration | `fallback_reason`, `planner_runtime_configured`, `legacy_engine`; SHOULD also preserve construction/backend identity where possible |
| Legacy-engine direct | planner runtime not configured; success came directly from legacy engine | canonical success envelope | `legacy_engine` | final backend exposed by legacy result or inferred serializer | `false` unless the legacy engine itself explicitly reports fallback | MAY be absent in older shims, but SHOULD be present | numeric; MAY default to `0.0` during migration | `planner_runtime_configured: false` SHOULD be exposed when available; `legacy_engine` SHOULD be exposed |
| Legacy direct-frame compatibility shim | migration-era direct frame-to-renderer success exposed through a compatibility serializer | canonical success envelope | `legacy_direct_frame` | final backend actually used, commonly `gf` in current compatibility flows | `false` or `true` depending on explicit shim/runtime fallback | MAY be absent in older compatibility payloads; SHOULD be present where possible | numeric; MAY default to `0.0` | `compatibility_shim`, `legacy_engine` when relevant, and any bridge diagnostics needed to explain why planner-first was not used |

---

## 6. Top-level invariants across all rows

The matrix above varies by path, but the following invariants never change for successful responses.

### 6.1 `text`

- MUST be the final surface text returned to the caller.
- MUST be non-empty after trimming.

### 6.2 `lang_code`

- MUST describe the language of the returned surface text.
- MUST be normalized at the public boundary.
- SHOULD be lowercase API-facing form such as `en` or `fr`, even if some internal runtime layers still use other forms during migration.

### 6.3 `construction_id`

- MUST identify the construction actually realized.
- MUST be preserved across fallback.
- MUST NOT silently change because a different backend produced the final output.

### 6.4 `renderer_backend`

- MUST identify the backend that produced the final surface text.
- MUST reflect the final selected backend, not merely the preferred backend.

### 6.5 `fallback_used`

- MUST be explicit.
- MUST be `true` whenever fallback materially affected the returned result.
- MUST NOT rely on logs alone.

### 6.6 `tokens`

- MUST correspond to the final returned `text`.
- MAY be provided by the producing backend.
- If absent, they MAY be derived from the final `text`.
- Token derivation MUST happen from final surface text, not from an intermediate AST or slot map.

### 6.7 `debug_info`

- MUST be an object.
- MUST contain stable machine-readable diagnostics.
- MUST at minimum preserve:
  - `construction_id`
  - `renderer_backend`
  - `lang_code`
  - `fallback_used`

### 6.8 `generation_time_ms`

- MUST be numeric in the public success envelope.
- SHOULD represent actual elapsed generation time.
- MAY temporarily default to `0.0` in migration-era compatibility paths.

---

## 7. Runtime-path marker normalization

The following runtime-path markers are currently accepted by this document:

- `planner_first`
- `legacy_engine_fallback`
- `legacy_engine`
- `legacy_direct_frame`

Interpretation:

- `planner_first` = the request was realized through the planner-first construction runtime
- `legacy_engine_fallback` = planner-first was attempted but the final result came from legacy engine fallback
- `legacy_engine` = no planner-first runtime was available/configured for that execution path
- `legacy_direct_frame` = migration-era compatibility path that realized a direct frame or frame-like payload outside the canonical planner-first path

These markers are not interchangeable.

A response MUST NOT claim `planner_first` if the final sentence came from a direct legacy engine path.

---

## 8. Path-by-path requirements

### 8.1 Planner-first direct success

A planner-first direct success MUST satisfy all of the following:

- `debug_info.runtime_path == "planner_first"`
- `construction_id` is explicit
- `renderer_backend` matches the selected backend
- `fallback_used == false` unless a child backend explicitly reports its own fallback
- `attempted_backends` contains exactly the selected backend when no dispatch fallback occurred
- `backend_trace` is present
- `dispatch_policy` is present

### 8.2 Planner-first dispatch fallback success

A planner-first dispatch fallback success MUST satisfy all of the following:

- `debug_info.runtime_path == "planner_first"`
- `fallback_used == true`
- `attempted_backends` reflects all attempted backends in order
- `renderer_backend` equals the final selected backend
- the final returned `construction_id` remains stable
- path diagnostics make it possible to understand that fallback happened

### 8.3 Legacy-engine fallback success

A legacy-engine fallback success MUST satisfy all of the following:

- `debug_info.runtime_path == "legacy_engine_fallback"`
- `fallback_used == true`
- `fallback_reason` is present
- planner configuration status is visible
- the legacy engine identity is visible when available
- the response still uses the canonical public envelope

### 8.4 Legacy-engine direct success

A legacy-engine direct success MUST satisfy all of the following:

- `debug_info.runtime_path == "legacy_engine"`
- `fallback_used == false`, unless the legacy engine itself explicitly declares fallback
- the legacy engine path is visible in debug metadata
- the response still uses the canonical public envelope

### 8.5 Legacy direct-frame compatibility-shim success

A compatibility-shim success MUST satisfy all of the following:

- `debug_info.runtime_path == "legacy_direct_frame"`
- compatibility-only status is explicit
- the backend that actually produced the surface text is explicit
- planner-first acceptance MUST NOT be inferred from this row
- the response still uses the canonical public envelope

---

## 9. Compatibility policy

During migration, older serializers may still produce incomplete metadata.

Allowed temporary gaps:

- `attempted_backends` missing in some legacy shims
- `generation_time_ms` defaulting to `0.0`
- compatibility-only debug fields coexisting with canonical debug fields
- legacy backend-specific diagnostics such as GF AST metadata

Not allowed:

- changing the top-level success envelope by path
- omitting `fallback_used`
- hiding the final backend identity
- returning `surface_text` / `meta` as if they were canonical
- labeling a legacy path as `planner_first`

---

## 10. Matrix interpretation rules

### 10.1 Public envelope wins

If a path-specific serializer disagrees with the canonical public envelope, the serializer is wrong.

### 10.2 Final backend wins

If multiple backends were attempted, `renderer_backend` MUST name the one that actually produced the returned `text`.

### 10.3 Final language wins

`lang_code` MUST describe the final returned text.

### 10.4 Final fallback truth wins

If fallback influenced the returned result at any point, `fallback_used` MUST be `true`.

### 10.5 Debug parity wins

The following top-level fields MUST be mirrored consistently in `debug_info`:

- `construction_id`
- `renderer_backend`
- `lang_code`
- `fallback_used`

---

## 11. Examples

### 11.1 Planner-first direct success

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
    "selected_backend": "family",
    "attempted_backends": ["family"],
    "backend_trace": [
      "planned construction",
      "resolved lexical bindings",
      "assembled equative clause"
    ],
    "dispatch_policy": {
      "allow_fallback": true,
      "forced_backend": null
    }
  },
  "generation_time_ms": 12.5
}
````

### 11.2 Planner configured, fell back to legacy engine

```json
{
  "text": "Alan Turing is a Mathematician.",
  "lang_code": "en",
  "construction_id": "copula_equative_classification",
  "renderer_backend": "gf",
  "fallback_used": true,
  "tokens": ["Alan", "Turing", "is", "a", "Mathematician."],
  "debug_info": {
    "runtime_path": "legacy_engine_fallback",
    "construction_id": "copula_equative_classification",
    "renderer_backend": "gf",
    "lang_code": "en",
    "fallback_used": true,
    "fallback_reason": "planner exploded",
    "planner_runtime_configured": true,
    "legacy_engine": "GFGrammarEngine"
  },
  "generation_time_ms": 0.0
}
```

### 11.3 Direct-frame compatibility-shim success

```json
{
  "text": "Marie Curie is a Polish physicist",
  "lang_code": "fr",
  "construction_id": "copula_equative_classification",
  "renderer_backend": "gf",
  "fallback_used": false,
  "tokens": ["Marie", "Curie", "is", "a", "Polish", "physicist"],
  "debug_info": {
    "runtime_path": "legacy_direct_frame",
    "construction_id": "copula_equative_classification",
    "renderer_backend": "gf",
    "lang_code": "fr",
    "fallback_used": false,
    "compatibility_shim": true,
    "legacy_engine": "GFGrammarEngine",
    "resolved_language": "WikiFre",
    "ast": "mkBioFull (mkEntityStr \"Marie Curie\") (strProf \"physicist\") (strNat \"Polish\")"
  },
  "generation_time_ms": 0.0
}
```

---

## 12. Testing requirements

The serialization matrix is considered implemented only when tests verify:

* planner-first direct success serializes correctly
* planner-first fallback success serializes correctly
* legacy-engine fallback serializes correctly
* legacy-engine direct success serializes correctly
* compatibility-shim success serializes correctly
* public top-level shape remains identical across all successful rows
* runtime path is explicit and truthful
* fallback is explicit and machine-readable
* backend identity remains visible
* construction identity remains visible

Strong assertions SHOULD be used for:

* `construction_id`
* `renderer_backend`
* `fallback_used`
* `debug_info.runtime_path`
* metadata shape
* required debug markers

Flexible assertions MAY be used for:

* allowable surface variation
* punctuation differences that are not semantically important
* backend-specific debug fields beyond documented requirements

---

## 13. Acceptance rule

A generation path is not considered serialized correctly unless all of the following are true:

1. the result uses the canonical public success envelope,
2. the path identity is visible in `debug_info.runtime_path`,
3. the final backend is explicit,
4. fallback truth is explicit,
5. construction identity is explicit,
6. language identity is explicit,
7. tokens correspond to final text,
8. timing is numeric,
9. compatibility paths remain observable as compatibility paths.

If two successful runtime paths return different top-level response shapes, the contract is broken.



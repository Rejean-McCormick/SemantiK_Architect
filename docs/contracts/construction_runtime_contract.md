# Construction Runtime Contract

Status: normative  
Owner: Architecture / Runtime  
Last updated: 2026-03-16

---

## 1. Purpose

This document defines the authoritative **internal runtime contract** for single-sentence generation in SemantiK Architect.

It governs the canonical handoff between:

1. frame normalization,
2. construction selection,
3. sentence-level planning,
4. construction-plan building,
5. lexical resolution,
6. renderer realization,
7. API response mapping.

It exists to prevent architectural drift.

This contract is intentionally **construction-centric**, not biography-centric.

That means:

- biography lead generation is one consumer of this contract,
- locatives, equatives, existentials, possession, topic-comment, eventive clauses, relative clauses, and future constructions must use the same runtime shape,
- no backend is allowed to invent a competing planner-facing sentence contract,
- no renderer is allowed to become the hidden owner of construction semantics.

---

## 2. Scope

This contract governs all **single-sentence runtime generation paths** that start from normalized semantic input and end in a canonical `SurfaceResult`.

It applies to:

- planner output,
- construction-plan output,
- lexical resolution input/output,
- renderer input,
- renderer output,
- structured debug metadata,
- backend selection,
- fallback semantics,
- the internal boundary before public API response mapping.

It does **not** define:

- the full external request schema for every frame family,
- GF abstract or concrete grammar internals,
- family-specific morphology internals,
- multi-sentence discourse policy beyond sentence-level metadata,
- the public HTTP success envelope,
- the public HTTP error envelope.

The public HTTP success envelope is defined separately in `public_generation_response_contract.md`.

---

## 3. Source-of-truth rule

This document is the authoritative contract for the **internal runtime boundary**.

Boundary ownership is as follows:

- this document governs the internal runtime objects and flow,
- `slot_map_contract.md` governs slot naming and slot payload rules,
- `lexical_resolution_contract.md` governs lexicalization semantics,
- `construction_renderer_contract.md` governs renderer-facing behavior,
- `debug_info_contract.md` governs structured runtime trace keys,
- `public_generation_response_contract.md` governs the public HTTP success envelope.

Conflict rule:

- if the issue is about planner/runtime object shape, this document wins,
- if the issue is about slot naming, the slot-map contract wins,
- if the issue is about renderer-facing behavior, the renderer contract wins,
- if the issue is about HTTP serialization, the public generation response contract wins.

Any disagreement must be corrected immediately.

---

## 4. Core architectural rule

The canonical runtime flow is:

```text
normalized frame(s)
  -> construction selection
  -> planner
  -> planned sentence
  -> construction-plan builder
  -> construction plan
  -> lexical resolution
  -> renderer backend
  -> surface result
  -> API response mapping
````

No component may bypass this contract and become a second source of truth for sentence structure.

In particular:

* routers must not decide wording,
* renderers must not invent semantics,
* lexical resolvers must not choose discourse packaging,
* GF adapters must not become the primary semantic contract,
* family engines must not redefine construction meaning,
* direct `/generate` shortcuts must remain compatibility shims only during migration.

---

## 5. Design goals

This contract must satisfy all of the following.

### 5.1 Generic across constructions

It must support more than biography.

### 5.2 Backend-agnostic

It must work for GF, family engines, and safe-mode fallback.

### 5.3 Language-scalable

It must support family-level and language-level specialization without duplicating planning logic.

### 5.4 Debuggable

Every material runtime decision must be traceable.

### 5.5 Backward-compatible at the boundary

Existing API payloads may remain tolerated, but must normalize into this contract.

### 5.6 Deterministic

The same validated `ConstructionPlan` under the same backend and configuration should produce stable output.

### 5.7 Explicit about migration

Compatibility shims may exist temporarily, but must not become the authoritative architecture.

---

## 6. Normative keywords

The words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are used normatively in this document.

---

## 7. Canonical runtime objects

## 7.1 `PlannedSentence`

`PlannedSentence` is the canonical planner output.

It represents one sentence-level planning decision before renderer-facing realization packaging is finalized.

### Required fields

* `construction_id: str`
* `lang_code: str`
* `topic_entity_id: str | None`
* `focus_role: str | None`
* `discourse_mode: str | None`
* `generation_options: dict[str, Any]`

### Optional fields

* `metadata: dict[str, Any]`
* `source_frame_ids: list[str] | None`
* `priority: int | None`

### Rules

* `construction_id` MUST identify a registered construction.
* `lang_code` MUST be normalized before renderer selection.
* `generation_options` MUST contain planner-approved realization options.
* `metadata` MAY carry planner diagnostics and provenance, but MUST NOT be the only place where required renderer behavior is encoded.
* planner-local notes MUST NOT become a hidden renderer contract.

---

## 7.2 `ConstructionPlan`

`ConstructionPlan` is the canonical renderer-facing handoff.

It represents one validated construction ready for lexical resolution and realization.

### Required fields

* `construction_id: str`
* `lang_code: str`
* `slot_map: SlotMap`
* `generation_options: dict[str, Any]`

### Optional fields

* `topic_entity_id: str | None`
* `focus_role: str | None`
* `discourse_mode: str | None`
* `lexical_bindings: dict[str, Any] | None`
* `metadata: dict[str, Any]`
* `provenance: dict[str, Any] | None`

### Rules

* `construction_id` MUST identify a registered construction.
* `slot_map` MUST be the only semantic-role payload consumed by renderers.
* `generation_options` is the canonical renderer-safe options object.
* `metadata` MAY exist for planner diagnostics or provenance, but renderers MUST NOT depend on undocumented keys hidden inside `metadata`.
* `lexical_bindings` MAY be attached before or after lexical resolution, but if present they are authoritative for lexical identity.
* plan-level fields MUST stay at plan level and MUST NOT be duplicated into `slot_map`.

---

## 7.3 `SlotMap`

`SlotMap` is the canonical role/value payload for one construction.

### Shape

```python
SlotMap = dict[str, Any]
```

### Rules

* keys MUST be semantic or constructional roles, not backend-specific names,
* values MUST be normalized objects or scalars accepted by the slot contract,
* renderers MUST read from `slot_map` rather than raw frames,
* plan-level fields such as `construction_id`, `lang_code`, `generation_options`, `topic_entity_id`, `focus_role`, and `lexical_bindings` MUST NOT be treated as slot keys.

### Examples of shared semantic slot names

* `subject`
* `predicate`
* `predicate_nominal`
* `predicate_adjective`
* `object`
* `agent`
* `patient`
* `recipient`
* `theme`
* `location`
* `time`
* `quantity`
* `topic`
* `comment`
* `profession`
* `nationality`

---

## 7.4 `EntityRef`

`EntityRef` is the canonical entity reference object.

### Minimum shape

```python
{
  "label": "Alan Turing",
  "entity_id": "Q7251",
  "entity_type": "person",
  "gender": "m"
}
```

### Required fields

* `label: str`

### Optional fields

* `entity_id: str | None`
* `qid: str | None`
* `entity_type: str | None`
* `gender: str | None`
* `number: str | None`
* `person: str | None`
* `surface_hint: str | None`
* `features: dict[str, Any]`

### Rules

* `label` MUST be human-readable.
* `entity_id` SHOULD be stable when available.
* `qid` MAY be used as an external identity reference.
* `features` MAY carry renderer-relevant information, but MUST remain semantic or lexical rather than backend-internal.

---

## 7.5 `LexemeRef`

`LexemeRef` is the canonical lexical reference object.

### Minimum shape

```python
{
  "lemma": "mathematician",
  "lexeme_id": null,
  "pos": "NOUN",
  "source": "raw",
  "confidence": 0.0
}
```

### Required fields

* `lemma: str`

### Optional fields

* `lexeme_id: str | None`
* `qid: str | None`
* `pos: str | None`
* `surface_hint: str | None`
* `source: str`
* `confidence: float`
* `features: dict[str, Any]`

### Rules

* `lemma` MUST be backend-agnostic.
* `source` SHOULD identify lexical provenance such as `raw`, `local_lexicon`, `wikidata`, `bridge`, or `resolver`.
* `confidence` SHOULD be in `[0.0, 1.0]`.
* lexical references MUST preserve semantic intent and MUST NOT silently change construction meaning.

---

## 7.6 `SurfaceResult`

`SurfaceResult` is the canonical renderer result before API serialization.

### Minimum shape

```python
{
  "text": "Alan Turing is a British mathematician.",
  "lang_code": "en",
  "construction_id": "copula_equative_classification",
  "renderer_backend": "gf",
  "debug_info": {}
}
```

### Required fields

* `text: str`
* `lang_code: str`
* `construction_id: str`
* `renderer_backend: str`
* `debug_info: dict[str, Any]`

### Optional fields

* `tokens: list[str] | None`
* `warnings: list[str] | None`
* `fallback_used: bool`
* `confidence: float | None`

### Rules

* `text` MUST be non-empty on successful realization.
* `lang_code` MUST equal the normalized input language code for the realized sentence.
* `construction_id` MUST equal the validated input construction.
* `renderer_backend` MUST identify the backend actually used.
* `debug_info` MUST be machine-readable.
* `fallback_used` MAY appear top-level and SHOULD also be reflected in `debug_info`.
* `SurfaceResult` is an internal runtime object; transport-specific fields such as `generation_time_ms` belong to the public response mapping layer, not to this contract.

### Compatibility note

Older code may still use a broader `Sentence` domain object. At the renderer/runtime boundary, the canonical output shape is `SurfaceResult`.

---

## 8. Canonical variable names

The following names are mandatory across new runtime code and documentation.

### 8.1 Required names

* `lang_code`
* `planned_sentence`
* `construction_plan`
* `construction_id`
* `slot_map`
* `generation_options`
* `entity_ref`
* `lexeme_ref`
* `renderer_backend`
* `surface_result`
* `debug_info`
* `fallback_used`

### 8.2 Preferred names

* `normalized_frame`
* `topic_entity_id`
* `focus_role`
* `discourse_mode`
* `lexical_bindings`
* `provenance`

### 8.3 Compatibility names

The following names MAY remain as compatibility terms during migration, but must not define competing contracts:

* `sentence` as a compatibility wrapper for `SurfaceResult`
* `metadata` as a general diagnostics or provenance bag

### 8.4 Disallowed drift names

The following MUST NOT become top-level canonical runtime names:

* `bio_payload`
* `gf_payload`
* `engine_payload`
* `template_payload`
* `render_input`
* `surface_text` as the canonical runtime output field name
* `metadata` as the only renderer-facing options bag
* `sentence_spec` as a generic replacement for `construction_plan`

These names may exist locally, but not as the authoritative shared contract.

---

## 9. Construction registry contract

Every runtime construction MUST declare:

* `construction_id`
* required roles
* optional roles
* cardinality rules
* supported sentence kinds
* validation rules
* lexical requirements
* renderer capability expectations
* fallback behavior if applicable

### Minimum registry entry

```python
{
  "construction_id": "copula_equative_classification",
  "required_roles": ["subject", "predicate_nominal"],
  "optional_roles": ["modifier", "time", "manner"],
  "sentence_kind": "definition",
  "domain_tags": ["generic", "entity"],
  "supports_topic_comment": True
}
```

### Rules

* planner output MUST reference only registered constructions,
* renderers MUST reject unknown `construction_id` values explicitly,
* construction validation MUST happen before surface realization.

### Construction ID rule

Canonical `construction_id` values MUST use snake_case runtime identifiers, for example:

* `copula_equative_simple`
* `copula_equative_classification`
* `copula_locative`
* `possession_have`
* `topic_comment_eventive`

Legacy dotted or backend-local forms MAY be tolerated as migration aliases in normalization, but MUST NOT become the canonical runtime IDs.

---

## 10. Planner contract

## 10.1 Planner responsibilities

The planner MUST decide:

* which construction is used,
* whether a wrapper construction is used,
* topic/focus metadata,
* discourse packaging,
* sentence ordering at the sentence level,
* planner-level generation options,
* fallback construction selection where needed.

The planner MUST NOT decide:

* final wording,
* morphology,
* GF AST internals,
* backend-specific formatting,
* backend dispatch.

## 10.2 Planner output requirements

For every sentence plan, the planner MUST emit a `PlannedSentence` containing at least:

* `construction_id`
* `lang_code`
* `topic_entity_id`
* `focus_role`
* `discourse_mode`
* `generation_options`

The planner MAY emit:

* `metadata`
* `priority`
* `sentence_kind`
* `source_frame_ids`

## 10.3 Construction-plan builder responsibilities

The construction-plan builder, bridge, or equivalent runtime step MUST:

* convert `PlannedSentence` into `ConstructionPlan`,
* produce a valid canonical `slot_map`,
* normalize slot values into `EntityRef`, `LexemeRef`, literals, or other contract-approved slot objects,
* attach realization-relevant metadata,
* validate construction completeness before realization.

## 10.4 Generic planner entrypoint

The authoritative planner entrypoint SHOULD follow this signature:

```python
def plan_text(
    frames: Iterable[Any],
    *,
    lang_code: str,
    domain: str = "auto",
) -> list[PlannedSentence]:
    ...
```

## 10.5 Construction-plan builder entrypoint

The authoritative renderer-facing bridge SHOULD follow this signature:

```python
def build_construction_plan(
    planned_sentence: PlannedSentence,
    *,
    normalized_frame: Any | None = None,
) -> ConstructionPlan:
    ...
```

---

## 11. Lexical resolution contract

## 11.1 Purpose

Lexical resolution converts semantic slot values into stable lexical references usable by renderers.

## 11.2 Lexical resolver responsibilities

The lexical resolver MUST:

* preserve semantic intent,
* normalize raw strings when possible,
* produce `LexemeRef` and `EntityRef` objects where applicable,
* annotate provenance,
* provide confidence and fallback information,
* return a lexicalized `ConstructionPlan` or equivalent normalized slot payload.

The lexical resolver MUST NOT:

* choose sentence structure,
* choose topic/focus,
* silently drop required semantic content,
* silently replace one construction with another.

## 11.3 Canonical lexical resolver interface

Preferred interface:

```python
class LexicalResolverPort(Protocol):
    def resolve(
        self,
        construction_plan: ConstructionPlan,
        *,
        lang_code: str,
    ) -> ConstructionPlan:
        ...
```

Allowed helper interface:

```python
class LexicalResolverHelpers(Protocol):
    def resolve_entity(
        self,
        value: object,
        *,
        lang_code: str,
    ) -> EntityRef:
        ...

    def resolve_lexeme(
        self,
        value: object,
        *,
        lang_code: str,
        pos: str | None = None,
    ) -> LexemeRef:
        ...
```

### Rules

* the canonical runtime effect is lexicalized `ConstructionPlan` output,
* helper methods MAY work at entity or lexeme level,
* renderers MUST NOT become the hidden lexical resolver,
* no renderer should have to guess whether a raw input is an entity, profession, adjective, or event label.

---

## 12. Renderer contract

## 12.1 Renderer responsibilities

A renderer backend MUST:

* accept a validated `ConstructionPlan`,
* consume the canonical `slot_map`,
* realize one sentence,
* return `SurfaceResult`,
* expose backend-specific debug data through `debug_info`.

A renderer backend MUST NOT:

* redefine construction semantics,
* bypass slot validation,
* rewrite planner meaning silently,
* change `construction_id`,
* silently hide fallback behavior.

## 12.2 Canonical renderer interface

Preferred interface:

```python
class RealizerPort(Protocol):
    async def realize(
        self,
        construction_plan: ConstructionPlan,
    ) -> SurfaceResult:
        ...
```

## 12.3 Backend adapter constraints

### GF adapter

Additional responsibilities:

* map `construction_id` and `slot_map` to backend-specific ASTs,
* report backend concrete selection in `debug_info["resolved_language"]`,
* report AST when available in `debug_info["ast"]`.

GF is a backend. GF-specific data MAY appear in debug output but may not be required by the planner contract.

### Family-engine adapter

Additional responsibilities:

* use family config and language-card data,
* apply morphology through the registered family engine,
* remain construction-driven rather than frame-driven.

Family backends MUST NOT expose `render_bio(...)`-style interfaces as their public runtime surface.

### Safe-mode adapter

Additional responsibilities:

* produce deterministic fallback output,
* remain contract-faithful even when realization depth is low.

Safe-mode output must still honor `construction_id` and the shared slot contract.

## 12.4 Renderer backend names

Canonical steady-state values are:

* `gf`
* `family`
* `safe_mode`

A migration-only wrapper MAY surface `compat` in debug traces or temporary compatibility layers, but it MUST NOT become the canonical steady-state backend identity for renderer contracts.

## 12.5 Backend selection

Backend selection policy MUST be explicit.

Selection MAY consider:

* language capability,
* construction capability,
* engine availability,
* configuration flags,
* forced backend override,
* degraded mode.

Selection result MUST be reflected in `renderer_backend` and `debug_info`.

---

## 13. Runtime orchestrator contract

The preferred end-to-end runtime orchestration surface is:

```python
class TextRuntimePort(Protocol):
    async def generate(
        self,
        frames: Sequence[object],
        *,
        lang_code: str,
        domain: str = "auto",
    ) -> list[SurfaceResult]:
        ...
```

The runtime orchestrator MUST:

1. normalize and validate frames,
2. invoke the planner,
3. build construction plans,
4. resolve lexical items,
5. select realization backend(s),
6. return final `SurfaceResult` values.

This is the preferred successor to direct `GenerateText -> engine.generate(frame)` for construction-based generation.

---

## 14. API boundary rule

## 14.1 Router behavior

Routers MAY accept legacy or ergonomic payloads.

Routers MUST normalize them into internal frames and then hand off to planner-centered runtime generation.

Routers MUST NOT directly encode sentence wording.

## 14.2 Runtime vs public response mapping

The canonical internal renderer/runtime output is `SurfaceResult`.

The canonical public HTTP success envelope is defined separately and MUST be derived from `SurfaceResult`.

This means:

* runtime code returns `SurfaceResult`,
* API mappers serialize public fields such as `text`, `lang_code`, `construction_id`, `renderer_backend`, `fallback_used`, `tokens`, and `debug_info`,
* transport-specific response details belong in the public response contract, not in this runtime contract.

## 14.3 Backward compatibility

The runtime MAY continue to support current `bio`-style payloads during migration.

However:

* legacy input-shape compatibility MUST terminate at normalization,
* downstream runtime logic MUST consume `PlannedSentence` and `ConstructionPlan`, not raw payload quirks.

---

## 15. Debug info contract

`debug_info` is required for all runtime surfaces.

### Required shared keys

* `construction_id`
* `renderer_backend`
* `lang_code`
* `slot_keys`
* `fallback_used`

### Recommended shared keys

* `selected_backend`
* `attempted_backends`
* `backend_trace`
* `lexical_resolution`
* `warnings`
* `fallback_reason`
* `timings_ms`

### Backend-specific keys MAY include

* GF:

  * `resolved_language`
  * `concrete_name`
  * `ast`
* family:

  * `family`
  * `template_id`
* safe mode:

  * `safe_mode_strategy`

### Rules

* `debug_info` MUST be machine-readable.
* Shared keys SHOULD remain stable across backends.
* Backend-specific keys MAY be added, but MUST NOT replace shared keys.
* Fallback reasons MUST be explicit when fallback occurs.
* `debug_info` is separate from `slot_map`; it is derived from the plan, slot state, lexical-resolution metadata, backend selection, and fallback behavior.

### Example

```json
{
  "construction_id": "copula_equative_simple",
  "renderer_backend": "family",
  "lang_code": "fr",
  "slot_keys": ["subject", "predicate_nominal"],
  "fallback_used": false,
  "family": "romance",
  "backend_trace": [
    "validated slots",
    "resolved predicate lexical bindings",
    "assembled equative clause"
  ]
}
```

---

## 16. Validation rules

## 16.1 Construction validation

Before realization, the runtime MUST validate:

* construction is registered,
* required roles are present,
* role value types are acceptable,
* multiplicity rules are respected,
* `lang_code` is normalized,
* renderer can attempt this construction.

## 16.2 Failure behavior

Validation failures MUST be explicit.

Preferred failure classes:

* unknown construction,
* missing required role,
* invalid slot type,
* lexical resolution failure,
* renderer unsupported,
* runtime generation failure.

These MUST be distinguishable in logs and SHOULD be distinguishable in tests.

---

## 17. Fallback policy

Fallback must be explicit, not silent.

## 17.1 Allowed fallback sequence

Preferred order:

1. primary backend for language/construction
2. alternate deterministic backend
3. safe-mode backend
4. explicit failure

## 17.2 Fallback invariants

Fallback MUST preserve:

* `construction_id`
* semantic role intent
* `lang_code`

Fallback MUST annotate:

* `fallback_used`
* original backend or requested backend where available
* final backend
* reason

Fallback MUST NOT silently reinterpret the construction into a different construction.

---

## 18. Capability tier integration

The runtime contract is compatible with tiered language support.

Recommended interpretation:

* **Tier 1** — high-road realization
* **Tier 2** — family renderer with strong morphology support
* **Tier 3** — safe-mode deterministic fallback
* **Tier 4** — unsupported / fail closed

Capability tier MUST NOT change planner semantics. It only changes realization strategy.

---

## 19. Migration rule

During migration, existing direct runtime paths MAY remain temporarily.

But they MUST be treated as compatibility paths, not architectural peers.

Target end state:

* planner and construction runtime contract are authoritative,
* all renderers consume the same `ConstructionPlan`,
* direct frame-to-renderer generation is removed or reduced to an internal adapter,
* `Sentence` remains at most a compatibility wrapper around `SurfaceResult`.

### Current-state rule

If the live system still uses a compatibility path for some requests, that is a current-state deviation, not a new contract. Current-state deviations MUST be documented separately in `CURRENT_RUNTIME_STATUS.md` and MUST NOT redefine the contract specified here.

---

## 20. Initial construction coverage

The following construction families are expected to conform to this contract:

* `copula_equative_simple`
* `copula_equative_classification`
* `copula_attributive_adj`
* `copula_attributive_np`
* `copula_locative`
* `copula_existential`
* `possession_have`
* `possession_existential`
* `topic_comment_copular`
* `topic_comment_eventive`
* `intransitive_event`
* `transitive_event`
* `ditransitive_event`
* `passive_event`
* `relative_clause_subject_gap`
* `relative_clause_object_gap`
* `coordination_clauses`

Biography lead constructions remain one specialization within this generic system.

This document does not require all of them to migrate at once, but it defines the target runtime contract for all of them.

---

## 21. Non-goals

This contract does not attempt to:

* formalize every linguistic category,
* force all backends to share identical internal mechanics,
* replace language-specific morphology logic,
* define full multi-sentence discourse generation,
* make GF the required system core.

---

## 22. Acceptance criteria

The runtime contract is successfully implemented when:

1. planner output is represented as `PlannedSentence`,
2. renderer-facing handoff is represented as `ConstructionPlan`,
3. all new generation code consumes `slot_map`,
4. `generation_options` is the canonical renderer-safe options object,
5. renderers expose `renderer_backend`, `fallback_used`, and structured `debug_info`,
6. `debug_info` contains the required shared keys, including `slot_keys`,
7. lexical resolution is explicit and testable,
8. the API runtime no longer treats one construction family as architecturally special,
9. at least two backends can realize the same construction plan,
10. direct payload quirks no longer leak below normalization,
11. API response mapping happens only after `SurfaceResult`.

---

## 23. Final rule

The system’s runtime source of truth is:

* construction-centered,
* planner-first,
* bridge-to-plan explicit,
* slot-map based,
* lexicon-aware,
* backend-agnostic,
* debuggable.

Everything else must align to that.

If two backends require different planner-facing inputs, the contract is broken.


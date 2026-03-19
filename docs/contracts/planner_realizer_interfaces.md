Voici la version mise à jour.
Je l’ai réalignée sur les verrous déjà fixés ailleurs dans la doc du repo sur quatre points qui avaient dérivé dans ta version : le contrat cible `ConstructionPlan -> SurfaceResult`, la règle “planner-first nominal”, `generation_options` comme objet cross-boundary canonique au niveau du plan, et le fait que le mapper public sérialise le nominal au lieu de créer ses champs pour la première fois. Le lock doc, le contrat runtime, le contrat public et le code actuel du mapper convergent tous sur ces besoins.

````md
# Planner / Realizer Interfaces Contract

Status: normative  
Owner: SKA runtime maintainers  
Scope: canonical runtime interfaces between semantic planning and surface realization  
Applies to: API generation path, discourse planner, construction modules, construction-plan builders, lexical resolvers, family engines, GF adapter, safe-mode renderer

---

## 1. Purpose

This document defines the canonical interfaces between:

* semantic/frame normalization,
* discourse and sentence planning,
* construction-plan building,
* lexical resolution,
* realization backends,
* runtime-to-public response handoff.

It establishes one canonical runtime contract so that:

1. planning is the authoritative source of sentence intent,
2. all renderers consume the same `ConstructionPlan`,
3. all renderers return the same `SurfaceResult`,
4. GF is one backend rather than the runtime contract itself,
5. family engines and safe-mode remain first-class backends,
6. direct `frame -> renderer` generation is compatibility-only,
7. planner-first nominal success arrives mapper-ready before public serialization.

---

## 2. Architectural position

The canonical target runtime flow is:

```text
canonical input
  -> planner
  -> construction-plan building
  -> lexical resolution
  -> realizer
  -> SurfaceResult
  -> public response
````

The planner decides **what sentence is to be said**.
The realizer decides **how the target language says it**.

The runtime contract is therefore:

```text
PlannedSentence -> ConstructionPlan -> SurfaceResult
```

`PlannedSentence` is planner-facing.
`ConstructionPlan` is renderer-facing.
`SurfaceResult` is the canonical runtime result object handed to public response serialization.

---

## 3. Non-goals

This contract does **not** define:

* the full external HTTP request schema,
* individual construction semantics,
* GF abstract/concrete grammar design,
* family-specific morphology internals,
* lexicon storage implementation,
* evaluator acceptance gates in full.

Those are specified in separate documents.

---

## 4. Design principles

### 4.1 Planner-first

No renderer may invent sentence structure that the planner did not authorize.

### 4.2 Renderer-agnostic planning

Planner output must be valid for GF, family engines, and safe-mode.

### 4.3 Construction-centered runtime

The runtime contract is expressed in terms of constructions, slot maps, lexical bindings, and realization options, not renderer-specific ASTs.

### 4.4 Typed lexical boundary

Raw values may enter the system, but renderer-facing payloads must use normalized `EntityRef` / `LexemeRef` values where possible.

### 4.5 Stable debug surface

All backends must emit a common minimum `debug_info` shape.

### 4.6 Explicit fallback

Fallback between backends is allowed only through explicit runtime policy and must be visible in result metadata.

### 4.7 Compatibility isolation

Backward compatibility may exist at the boundary, but compatibility shims must not redefine the canonical runtime contract.

### 4.8 Mapper is not a hidden runtime

The public response mapper may normalize and serialize results.
It must not be the place where nominal planner-first metadata becomes real for the first time.

---

## 5. Canonical terminology

### 5.1 Core runtime objects

* **Frame**
  Semantic/domain input object.

* **PlannedSentence**
  Sentence-level planning object carrying discourse and construction metadata.

* **ConstructionPlan**
  Canonical runtime handoff from planner-side logic to renderer-side realization.

* **SlotMap**
  Canonical semantic role/value payload for one construction.

* **EntityRef**
  Normalized entity reference for a discourse participant or topic.

* **LexemeRef**
  Normalized lexical reference for a noun, adjective, predicate, modifier, or other lexicalized slot value.

* **SurfaceResult**
  Canonical runtime surface result returned before public-response serialization.

### 5.2 Canonical field names

These names are canonical across planner and realizer code:

* `lang_code`
* `construction_id`
* `slot_map`
* `generation_options`
* `lexical_bindings`
* `topic_entity_id`
* `focus_role`
* `discourse_mode`
* `provenance`
* `metadata`
* `renderer_backend`
* `fallback_used`
* `tokens`
* `debug_info`
* `text`
* `generation_time_ms`

Use these preferred runtime variable names where applicable:

* `planned_sentence`
* `construction_plan`
* `surface_result`

Avoid drift names as authoritative shared runtime names:

* `lang`
* `language`
* `resolved_lang`
* `construction`
* `template_id`
* `pattern_id`
* `slots`
* `args`
* `payload_slots`
* `engine_name`
* `backend_name`
* `surface_text`
* `sentence` as the canonical renderer contract object
* `metadata` as a generic replacement for `generation_options`

---

## 6. Runtime object contracts

## 6.1 EntityRef

```python
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class EntityRef:
    entity_id: Optional[str]
    label: str
    entity_type: Optional[str] = None
    qid: Optional[str] = None
    gender: Optional[str] = None
    number: Optional[str] = None
    person: Optional[str] = None
    animacy: Optional[str] = None
    features: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
```

### Semantics

* `entity_id` is the internal stable identifier when available.
* `label` is the preferred canonical display label.
* `entity_type` is an optional semantic type such as `person`, `place`, or `organization`.
* `qid` is optional external identity.
* discourse-relevant and morphology-relevant features may be attached.

### Invariants

* `label` is required.
* `entity_id` is optional but recommended when available.
* renderer backends must not mutate `EntityRef`.

---

## 6.2 LexemeRef

```python
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class LexemeRef:
    lexeme_id: Optional[str]
    lemma: str
    pos: Optional[str] = None
    qid: Optional[str] = None
    lang_code: Optional[str] = None
    features: Mapping[str, Any] = field(default_factory=dict)
    source: str = "raw"
    confidence: float = 0.0
```

### Semantics

* `lemma` is the canonical lexical content seen by the realizer.
* `pos` is optional but recommended.
* `features` may include gender, countability, definiteness constraints, adjective-position class, agreement hints, or inflection hints.
* `source` identifies provenance such as `raw`, `lexicon`, `wikidata`, or `resolved`.

### Invariants

* `lemma` is required.
* `confidence` is a float in `[0.0, 1.0]`.
* unresolved raw input is allowed only when fallback policy permits it.

---

## 6.3 SlotMap

```python
from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class SlotMap:
    values: Mapping[str, Any] = field(default_factory=dict)
```

### Semantics

`SlotMap.values` is the normalized mapping from semantic slot name to typed slot value.

Allowed slot value types include:

* `EntityRef`
* `LexemeRef`
* plain scalar literals (`str`, `int`, `float`, `bool`, `None`)
* ordered sequences only where the construction explicitly allows them

### Invariants

* slot names must be stable lower_snake_case strings.
* slot semantics are defined by the construction, not by the backend.
* renderers must reject unsupported required/forbidden slot combinations.
* `slot_map` must not contain plan-level fields such as `construction_id`, `lang_code`, `generation_options`, `topic_entity_id`, `focus_role`, `lexical_bindings`, `provenance`, or `debug_info`.

---

## 6.4 PlannedSentence

```python
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence


@dataclass(frozen=True)
class PlannedSentence:
    construction_id: str
    lang_code: str
    topic_entity_id: Optional[str] = None
    focus_role: Optional[str] = None
    discourse_mode: Optional[str] = None
    generation_options: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    source_frame_ids: Optional[Sequence[str]] = None
    priority: Optional[int] = None
```

### Semantics

`PlannedSentence` is the canonical planner output.
It represents one sentence-level planning decision before renderer-facing packaging is finalized.

### Required fields

* `construction_id`
* `lang_code`
* `generation_options`

### Optional fields

* `topic_entity_id`
* `focus_role`
* `discourse_mode`
* `metadata`
* `source_frame_ids`
* `priority`

### Invariants

* `construction_id` must identify a registered construction.
* `lang_code` must be normalized before renderer selection.
* `generation_options` must contain planner-approved realization options.
* planner-local notes may exist in `metadata`, but they must not become a hidden renderer contract.

### Rule

`PlannedSentence` is planner-facing.
It is not renderer-ready until converted into a `ConstructionPlan`.

---

## 6.5 ConstructionPlan

```python
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class ConstructionPlan:
    construction_id: str
    lang_code: str
    slot_map: SlotMap
    generation_options: Mapping[str, Any] = field(default_factory=dict)
    topic_entity_id: Optional[str] = None
    focus_role: Optional[str] = None
    discourse_mode: Optional[str] = None
    lexical_bindings: Mapping[str, Any] = field(default_factory=dict)
    provenance: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
```

### Semantics

`ConstructionPlan` is the canonical renderer-facing handoff.

It is the authoritative planner/build-step -> realizer contract.

### Required fields

* `construction_id`
* `lang_code`
* `slot_map`
* `generation_options`

### Optional fields

* `topic_entity_id`
* `focus_role`
* `discourse_mode`
* `lexical_bindings`
* `provenance`
* `metadata`

### Field rules

* `slot_map` is the only semantic role/value payload consumed by renderers.
* `generation_options` is the canonical renderer-safe options object.
* `lexical_bindings` may be attached before or after lexical resolution; when present they are authoritative for lexical identity.
* `metadata` may carry planner diagnostics or provenance, but renderers must not depend on undocumented behavior hidden inside `metadata`.
* plan-level fields must stay at plan level and must not be duplicated inside `slot_map`.

### Typical `generation_options` keys

Typical keys include:

* `tense`
* `aspect`
* `polarity`
* `register`
* `definiteness`
* `voice`
* `style`
* `allow_fallback`
* `force_backend`
* `debug`

### Invariants

* `construction_id` is globally stable and backend-independent.
* `lang_code` is normalized before realization.
* all semantic content required for realization must already be present in `slot_map` and/or `lexical_bindings`.
* `generation_options` may refine realization behavior but may not silently change construction semantics.

---

## 6.6 SurfaceResult

```python
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class SurfaceResult:
    text: str
    lang_code: str
    construction_id: str
    renderer_backend: str
    fallback_used: bool
    tokens: Sequence[str] = field(default_factory=tuple)
    debug_info: Mapping[str, Any] = field(default_factory=dict)
    generation_time_ms: float = 0.0
```

### Semantics

This is the canonical runtime result object returned by realization and handed to public-response mapping.

### Required fields

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `debug_info`
* `generation_time_ms`

### Conditionally required field

* `tokens` should be present on nominal success.
  It may be omitted only when the runtime intentionally relies on deterministic fallback tokenization downstream.

### Invariants

* `text` is authoritative.
* `lang_code` is the returned surface language.
* `construction_id` must be explicit on the nominal path.
* `renderer_backend` must be explicit on the nominal path.
* `fallback_used` must be explicit and truthful.
* `generation_time_ms` is top-level and authoritative.
* `debug_info` must not contradict top-level fields.

### Compatibility note

A legacy internal `Sentence` type may remain temporarily as a compatibility alias or wrapper, but the canonical runtime contract name is `SurfaceResult`.

---

## 7. Planner interface

```python
from __future__ import annotations
from typing import Protocol, Sequence


class PlannerPort(Protocol):
    def plan(
        self,
        frames: Sequence[object],
        *,
        lang_code: str,
        domain: str = "auto",
    ) -> list[PlannedSentence]:
        """
        Produce sentence-level discourse plans from semantic frames.
        """
        ...
```

### Responsibilities

The planner must:

* preserve or intentionally reorder semantic content,
* choose `construction_id`,
* set `lang_code`,
* set `topic_entity_id`,
* set `focus_role`,
* set `discourse_mode` where relevant,
* attach planner-approved `generation_options`,
* attach sentence-level metadata and provenance where useful.

The planner must **not**:

* choose renderer backends,
* build GF ASTs,
* inflect morphology directly,
* generate final strings.

---

## 8. Construction-plan builder interface

```python
from __future__ import annotations
from typing import Protocol


class ConstructionPlanBuilder(Protocol):
    def build_plan(
        self,
        planned_sentence: PlannedSentence,
        *,
        lang_code: str,
    ) -> ConstructionPlan:
        """
        Convert a PlannedSentence into a renderer-ready ConstructionPlan.
        """
        ...
```

### Responsibilities

The construction-plan builder must:

* map sentence-level intent into a stable slot contract,
* normalize slot values into `EntityRef` / `LexemeRef` / literals,
* produce canonical `generation_options`,
* attach lexical bindings when already known,
* attach provenance where useful,
* validate construction completeness.

This is the authoritative bridge between planning and realization.

---

## 9. Lexical resolver interface

```python
from __future__ import annotations
from typing import Protocol


class LexicalResolverPort(Protocol):
    def resolve_plan(
        self,
        construction_plan: ConstructionPlan,
        *,
        lang_code: str,
    ) -> ConstructionPlan:
        """
        Resolve slot values and/or lexical_bindings into stable EntityRef / LexemeRef
        forms where possible and return an updated ConstructionPlan.
        """
        ...
```

Optional helper methods may also be provided:

```python
from __future__ import annotations
from typing import Protocol


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

### Responsibilities

The lexical resolver must:

* normalize raw input into stable typed references,
* prefer existing lexicon IDs / known lemmas when available,
* annotate provenance and confidence,
* populate or refine `lexical_bindings`,
* provide controlled raw fallback where resolution is incomplete.

### Rule

No renderer should have to guess whether a raw input is an entity, profession, adjective, role word, or event label.
That classification belongs in construction-plan building and lexical resolution.

---

## 10. Realizer interface

```python
from __future__ import annotations
from typing import Protocol


class RealizerPort(Protocol):
    async def realize(
        self,
        construction_plan: ConstructionPlan,
    ) -> SurfaceResult:
        """
        Produce a surface result from a ConstructionPlan.
        """
        ...
```

### Responsibilities

The realizer must:

* consume only `ConstructionPlan`,
* select language/family-specific realization logic,
* return a `SurfaceResult`,
* populate standard `debug_info`,
* never mutate the input plan,
* never silently reinterpret the plan into a different construction.

### Rule

A realizer may fail because the plan is unsupported, incomplete, or insufficiently lexicalized.
It may not silently replace planner-selected construction semantics.

---

## 11. Backend adapter contracts

Each backend adapter must implement the same public runtime surface:

```python
async def realize(construction_plan: ConstructionPlan) -> SurfaceResult
```

### 11.1 GF adapter

Additional responsibilities:

* map `construction_id`, `slot_map`, `generation_options`, and `lexical_bindings` to backend-specific structures,
* report concrete-language selection in `debug_info["resolved_language"]`,
* report AST when available in `debug_info["ast"]`.

### Constraint

GF is a backend.
GF-specific data may appear in debug output but may not be required by the planner contract.

### 11.2 Family-engine adapter

Additional responsibilities:

* use family configuration and language-card data,
* apply morphology through the registered family engine,
* remain construction-driven rather than frame-driven.

### Constraint

Family backends must not expose `render_bio(...)`-style interfaces as their public runtime surface.
The public runtime surface is `realize(construction_plan)`.

### 11.3 Safe-mode adapter

Additional responsibilities:

* produce deterministic fallback output,
* remain contract-faithful even when realization depth is low.

### Constraint

Safe-mode output must still honor `construction_id`, `slot_map`, and `generation_options`.

---

## 12. Runtime orchestrator interface

```python
from __future__ import annotations
from typing import Protocol, Sequence


class TextRuntimePort(Protocol):
    async def generate(
        self,
        frames: Sequence[object],
        *,
        lang_code: str,
        domain: str = "auto",
    ) -> list[SurfaceResult]:
        """
        End-to-end generation:
        frames -> planner -> construction plans -> realization -> surface results
        """
        ...
```

### Responsibilities

The runtime orchestrator must:

1. normalize and validate input,
2. invoke the planner,
3. build construction plans,
4. resolve lexical items,
5. select realization backend(s),
6. return final `SurfaceResult` objects.

This is the preferred successor to direct `GenerateText -> engine.generate(frame)` for construction-based generation.

---

## 13. Backend selection policy

Canonical backend preference order:

1. GF backend, when the language/construction pair is supported and healthy
2. family backend, when family realization is available
3. safe-mode backend, when deterministic fallback is allowed

### Rules

* backend selection must be explicit and observable,
* fallback must be recorded truthfully,
* failure in one backend does not authorize semantic drift,
* unsupported construction/backend combinations must fail clearly.

Recommended observability keys include:

* `selected_backend`
* `attempted_backends`
* `resolved_language`
* `backend_trace`

---

## 14. Error contract

### 14.1 Planner errors

Use when:

* frames are invalid,
* construction cannot be assigned,
* discourse planning fails.

Suggested type:

* `PlanningError`

### 14.2 Construction-plan errors

Use when:

* required slots are missing,
* slot values are of the wrong type,
* construction constraints are violated.

Suggested type:

* `ConstructionPlanError`

### 14.3 Lexical resolution errors

Use when:

* required entity/lexeme normalization fails without permitted fallback.

Suggested type:

* `LexicalResolutionError`

### 14.4 Realization errors

Use when:

* backend cannot realize the plan,
* backend is unavailable,
* generated AST or morphology realization fails.

Suggested type:

* `RealizationError`

### 14.5 Runtime policy

* prefer explicit typed errors internally,
* API layers may translate them into public/domain error contracts,
* never silently switch constructions to recover from an error.

---

## 15. Debug-info contract

Every `SurfaceResult.debug_info` must support the following minimum keys on nominal planner-first success:

```json
{
  "runtime_path": "planner_first",
  "construction_id": "string",
  "renderer_backend": "gf|family|safe_mode",
  "lang_code": "string",
  "fallback_used": false
}
```

Recommended optional keys:

```json
{
  "topic_entity_id": "optional string",
  "focus_role": "optional string",
  "discourse_mode": "optional string",
  "resolved_language": "optional concrete language key",
  "ast": "optional backend expression",
  "slot_keys": ["optional", "canonical", "slot", "names"],
  "lexical_resolution": "optional lexical resolver summary",
  "selected_backend": "optional backend name",
  "attempted_backends": ["optional", "backend", "sequence"],
  "backend_trace": ["optional", "trace", "messages"],
  "timings_ms": {
    "planning": 0.0,
    "resolution": 0.0,
    "realization": 0.0
  },
  "warnings": []
}
```

### Invariants

* `construction_id` in `debug_info` must equal the top-level `construction_id`.
* `renderer_backend` in `debug_info` must equal the top-level `renderer_backend`.
* `lang_code` in `debug_info` must equal the top-level `lang_code`.
* `fallback_used` in `debug_info` must equal the top-level `fallback_used`.
* `runtime_path` must truthfully report the actual runtime path.
* `fallback_used` must be truthful.

---

## 16. Mapper boundary rule

The public response mapper is downstream of `SurfaceResult`.

Allowed mapper responsibilities:

* type coercion,
* `lang_code` normalization,
* token normalization,
* mirroring canonical top-level fields into `debug_info`,
* preserving truthful compatibility metadata,
* parsing older internal result shapes during the migration tail.

Forbidden mapper responsibilities on the nominal planner-first path:

* inventing missing planner-first metadata for the first time,
* turning missing `construction_id` into acceptable nominal success,
* turning missing `renderer_backend` into acceptable nominal success,
* upgrading a compatibility result into nominal planner-first success,
* relying on `debug_info`-only values as the intended steady-state source for nominal planner-first fields.

Final-state rule:

```text
planner-first result arrives mapper-ready
  -> mapper serializes
  -> public response is emitted
```

Not:

```text
incomplete planner-first result
  -> mapper repairs missing nominal metadata
  -> public response pretends success
```

---

## 17. Compatibility layer

During migration, older direct-generation paths may remain only as compatibility adapters.

Allowed transitional shape:

```text
legacy frame
  -> compatibility mapper
  -> ConstructionPlan
  -> canonical realizer
  -> SurfaceResult
```

Not allowed:

```text
legacy frame
  -> ad hoc renderer-specific logic
  -> final text
```

Compatibility layers must be temporary, isolated, and visibly non-nominal.

---

## 18. Example end-to-end flow

### Input frames

```python
frames = [bio_frame]
```

### Planner output

```python
[
    PlannedSentence(
        construction_id="copula_equative_classification",
        lang_code="fr",
        topic_entity_id="Q7251",
        focus_role="predicate_nominal",
        discourse_mode="declarative",
        generation_options={
            "sentence_kind": "biographical_definition",
            "register": "neutral",
            "polarity": "positive",
            "allow_fallback": True,
        },
        metadata={"planner_trace": "bio/person canonical path"},
        source_frame_ids=["bio_frame_001"],
    )
]
```

### Construction plan

```python
ConstructionPlan(
    construction_id="copula_equative_classification",
    lang_code="fr",
    slot_map=SlotMap(
        values={
            "subject": EntityRef(
                entity_id="Q7251",
                label="Alan Turing",
                qid="Q7251",
                gender="m",
                entity_type="person",
            ),
            "predicate_nominal": LexemeRef(
                lexeme_id=None,
                lemma="mathématicien",
                pos="NOUN",
                source="lexicon",
                confidence=0.92,
            ),
            "nationality": LexemeRef(
                lexeme_id=None,
                lemma="britannique",
                pos="ADJ",
                source="lexicon",
                confidence=0.95,
            ),
        }
    ),
    generation_options={
        "sentence_kind": "biographical_definition",
        "register": "neutral",
        "polarity": "positive",
        "allow_fallback": True,
    },
    topic_entity_id="Q7251",
    focus_role="predicate_nominal",
    discourse_mode="declarative",
    lexical_bindings={
        "predicate_nominal": {
            "lemma": "mathématicien",
            "source": "lexicon",
            "confidence": 0.92,
        },
        "nationality": {
            "lemma": "britannique",
            "source": "lexicon",
            "confidence": 0.95,
        },
    },
    provenance={"builder": "bio_person_plan_builder"},
)
```

### Surface result

```python
SurfaceResult(
    text="Alan Turing est un mathématicien britannique.",
    lang_code="fr",
    construction_id="copula_equative_classification",
    renderer_backend="gf",
    fallback_used=False,
    tokens=[
        "Alan",
        "Turing",
        "est",
        "un",
        "mathématicien",
        "britannique.",
    ],
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

---

## 19. Required migration rule

Every migrated construction must follow this chain:

```text
frame -> PlannedSentence -> ConstructionPlan -> SurfaceResult
```

Not:

```text
frame -> renderer-specific generation
```

This is the rule that prevents drift between planner logic, construction logic, lexical resolution, and backend logic.

---

## 20. Contract-stable extension points

The following may evolve without breaking this contract:

* richer `LexemeRef.features`
* richer `EntityRef.metadata`
* richer `generation_options`
* richer `lexical_bindings`
* multi-sentence planning metadata
* backend-specific timing detail
* richer fallback policy controls
* parser-facing interfaces in the future

The following are contract-stable and may not drift casually:

* `construction_id`
* `slot_map`
* `generation_options`
* `lang_code`
* `renderer_backend`
* `fallback_used`
* `text`
* `generation_time_ms`
* minimum `debug_info` keys
* planner vs realizer responsibility boundary

---

## 21. Acceptance criteria

This contract is considered adopted when:

1. new runtime generation code consumes `ConstructionPlan`,
2. planner output is converted into renderer-ready plans explicitly,
3. lexical resolution occurs before final realization,
4. GF, family, and safe-mode backends implement `realize(construction_plan)`,
5. all active backends return `SurfaceResult`,
6. debug output is standardized,
7. at least one migrated construction runs end-to-end through the canonical path,
8. direct frame-driven rendering is demoted to compatibility-only status,
9. nominal planner-first success no longer depends on the response mapper to invent missing runtime metadata.

---

## 22. Summary

This contract makes planning authoritative and realization replaceable.

It fixes the runtime boundary between:

* semantic intent,
* sentence planning,
* construction-plan building,
* lexical normalization,
* multilingual realization,
* public response serialization.

The result is one stable runtime contract across:

* planner,
* construction-plan building,
* lexical resolution,
* GF backend,
* family-engine backends,
* safe-mode fallback,
* runtime-to-public-response handoff.

```

Les changements de fond par rapport à ta version initiale sont donc clairs :
- `ConstructionPlan` porte désormais explicitement `generation_options` et `lexical_bindings` au niveau du plan, au lieu de cacher ça dans `metadata`, ce qui est aligné avec les règles de nommage et de frontière du repo. 
- `SurfaceResult` inclut explicitement `fallback_used`, `tokens` et `generation_time_ms`, ce qui l’aligne avec le contrat public final et avec les locks du cutover. 
- `debug_info` impose `runtime_path = "planner_first"` sur le nominal planner-first, avec parité top-level/debug pour les champs canoniques. :contentReference[oaicite:3]{index=3}
- la section mapper interdit explicitement que `generation_response_mapper.py` “répare” le nominal comme steady state, ce qui répond directement au drift encore visible dans le code actuel. 

Si tu veux, je peux maintenant faire la même chose pour `docs/contracts/debug_info_contract.md` afin de garder une cohérence parfaite entre les deux.
```

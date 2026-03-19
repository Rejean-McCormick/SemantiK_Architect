# Inputs: Frames

Frames are the **stable public JSON input contract** used by SemantiK Architect for generation requests.

They describe **what should be said** in a structured way, without hard-coding any particular language’s surface form. A Frame is an input to the generation pipeline, not the runtime handoff used by renderers and not the final public success envelope returned by the API.

---

## What a “Frame” is

A Frame is a compact meaning object expressed as JSON.

It gives the system:

- a **frame type** that identifies the intended semantic pattern,
- a set of **slots/fields** that supply the required meaning,
- an input shape that can be **validated and normalized** before runtime generation begins.

Frames belong to the **external/public input layer**. Internally, they are normalized into internal semantic/domain frame objects and then passed into the planner-first runtime.

---

## Where Frames sit in the architecture

Frames are the stable entry contract at the API boundary.

They are **not**:

- the planner contract,
- the renderer contract,
- the lexical-resolution contract,
- the `ConstructionPlan`,
- the `SurfaceResult`,
- or the frontend/client convenience result model.

The architectural boundary is:

- **clients send Frames**,
- **the request boundary normalizes them**,
- **the planner/runtime consumes normalized meaning**,
- **renderers consume `ConstructionPlan`**,
- **the runtime returns `SurfaceResult`**,
- **the API maps that to the public success envelope**.

This separation keeps the public input contract stable while allowing the internal runtime to remain planner-first and construction-centered.

---

## How SemantiK Architect interprets Frames

A generation request is processed in stages:

1. the payload is read as JSON,
2. the system reads and normalizes the canonical `frame_type`,
3. the payload is converted into an internal normalized frame/domain object,
4. the planner selects or finalizes the intended construction,
5. the runtime builds a canonical `ConstructionPlan`,
6. lexical bindings are resolved as needed,
7. a renderer backend produces a `SurfaceResult`,
8. the API maps that runtime result into the public success response.

This means client payloads can remain stable even while internal runtime architecture evolves.

---

## `frame_type` is authoritative

Every Frame should declare a `frame_type`.

Examples include:

- `bio`
- `entity.person`
- `event.*`
- `rel.*`
- `narr.*`
- `meta.*`

For compatibility, the system may accept equivalent, legacy, or alias labels and normalize them into a canonical internal type before generation.

`frame_type` is the public meaning-family signal. It is not itself a renderer instruction and it is not a guarantee of a one-to-one mapping to final surface wording.

---

## Example: bio frame

A typical bio request can look like this:

```json
{
  "frame_type": "bio",
  "name": "Alan Turing",
  "profession": "computer scientist",
  "nationality": "British",
  "gender": "m"
}
````

This expresses intended meaning in a simple upstream-friendly format.

The runtime is responsible for normalizing this meaning, planning the sentence, assembling the construction, resolving lexical material, and producing language-specific text.

---

## Canonicalization and normalization

SemantiK Architect does **not** rely on raw payload shape alone.

Before generation, the system may:

* normalize equivalent frame labels,
* merge tolerated input variants into a canonical internal frame,
* normalize naming and field aliases,
* validate required fields,
* preserve optional metadata such as context or transport-neutral extras,
* reject malformed or incomplete requests before realization begins.

For example, multiple “bio-like” request shapes may normalize to the same internal bio frame representation.

Compatibility at the request boundary is allowed.

That compatibility ends at normalization.

Downstream planner/runtime code must consume normalized internal meaning objects rather than transport quirks.

---

## Frames are the input contract, not the runtime contract

Frames are for **requesting generation**.

They are intentionally separate from the internal runtime contract.

Internally, the runtime proceeds through planner-first objects such as:

* normalized internal frame/domain objects,
* sentence-level planning objects,
* `ConstructionPlan`,
* lexicalized runtime state,
* `SurfaceResult`.

Renderers and realization backends must not depend on arbitrary raw JSON payloads.

They must consume normalized runtime inputs produced by the generation pipeline.

In other words:

* **clients send Frames**,
* **the runtime normalizes them**,
* **the planner chooses the constructional path**,
* **renderers realize normalized meaning**.

This prevents raw HTTP payloads from becoming a hidden renderer contract.

---

## Frames and planner-first runtime

SemantiK Architect is planner-first on the target runtime path.

That means Frames do not directly select wording or bypass planning.

The target flow is:

**Frame input**
→ **Normalize meaning**
→ **Plan sentences / choose construction**
→ **Build `ConstructionPlan`**
→ **Resolve lexical bindings**
→ **Realize with a backend**
→ **Return `SurfaceResult`**
→ **Map to public API response**

Frames remain stable even when:

* the planner becomes more sophisticated,
* the construction inventory expands,
* lexical resolution improves,
* language-specific realization becomes richer,
* new backends or languages are introduced.

---

## Public input stability vs internal runtime evolution

Frames exist specifically to let upstream systems rely on a stable request contract without coupling themselves to internal runtime objects.

Public input stability does **not** imply that:

* raw frame fields map directly to final text,
* renderers consume raw Frames directly,
* internal planner/runtime objects stay identical forever,
* frontend convenience APIs define the HTTP request contract.

The system is free to evolve its internal runtime as long as Frames continue to normalize into the intended meaning layer.

---

## Language neutrality

Frames are meaning-first and language-neutral at the public input layer.

They should express semantic content, not language-specific phrasing rules.

Prefer semantically clear fields such as:

* `name`
* `profession`
* `nationality`
* `location`
* `agent`
* `patient`
* `time`

Avoid encoding language-specific surface decisions such as:

* precomposed clause strings,
* hard-coded article/case/gender morphology,
* language-specific word order assumptions,
* backend-specific AST hints.

Language-specific realization belongs to downstream runtime and renderer layers, not to the Frame contract.

---

## When to use Frames

Use Frames when you want:

* a **stable public JSON request contract**,
* **validation and normalization** before generation,
* a format that is easy to author, inspect, and debug,
* compatibility with the public generation API,
* clear separation between upstream inputs and internal runtime mechanics.

Frames are the preferred choice for API clients that want predictable behavior without depending on internal planner or renderer details.

---

## Frames vs Ninai

Use **Frames** when you want:

* a direct generation request format,
* a stable API-facing JSON contract,
* explicit `frame_type`-driven normalization,
* a request shape suitable for public HTTP generation endpoints.

Use **Ninai** when you want:

* a more recursive or tree-structured meaning representation,
* an intermediate representation that can be adapted into internal frames,
* a bridge-oriented workflow rather than a direct public frame request.

Frames and Ninai are related, but they are not the same layer.

A Ninai-style structure may be adapted into the same normalized meaning pipeline, but Frames remain the stable public request contract.

---

## Anti-drift rules

The following distinctions must remain explicit.

### Frames must not become render inputs

Do not treat raw Frame payloads as the canonical renderer contract.

Renderers consume normalized runtime objects, not arbitrary client JSON.

### Compatibility must end at normalization

Do not let tolerated aliases, legacy fields, or transport quirks leak into planner/runtime ownership.

### Public input must not collapse into runtime output

Do not present Frames as if they were `ConstructionPlan`, `SurfaceResult`, or the public success response.

### Frontend convenience must not redefine Frames

Frontend/session-facing helpers may wrap generation ergonomics, but they do not redefine the canonical HTTP Frame contract.

---

## Practical guidance

* Keep `frame_type` explicit whenever possible.
* Prefer semantically clear slot names over language-specific phrasing.
* Do not assume that raw input fields map directly to final surface text.
* Do not assume that a Frame maps one-to-one to a single backend template.
* Do not use Frames to smuggle renderer-local instructions.
* Treat request compatibility as an ingest concern, not a runtime contract.

---

## Summary

Frames are the **stable public meaning-first request layer** for SemantiK Architect.

They let clients describe intended meaning in JSON while the internal system remains free to:

* normalize meaning,
* plan constructions,
* resolve lexical material,
* realize language-specific surface text,
* and return a separate public success response.

That separation is intentional.

It is what allows SemantiK Architect to keep a stable input contract while using a planner-first, construction-centered, backend-agnostic runtime.

---

## See also

* [[Inputs: Ninai|Inputs-Ninai]]
* [[API Overview|API-Overview]]
* [[Conceptual Flow: Meaning to Text|Conceptual-Flow-Meaning-to-Text]]
* [[Construction Runtime Contract|construction_runtime_contract]]
* [[Public vs Runtime vs Frontend Boundaries|public_vs_runtime_vs_frontend_boundaries]]
* [[Public Generation Response Contract|public_generation_response_contract]]


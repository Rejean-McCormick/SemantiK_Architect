# Inputs: Frames

Frames are the **stable JSON input contract** used by SemantiK Architect for generation requests.

They describe **what should be said** in a structured way, without hard-coding any particular language’s surface form. A Frame is an input to the generation pipeline, not the final runtime surface used by renderers.

---

## What a “Frame” is

A Frame is a compact meaning object expressed as JSON.

It gives the system:

- a **frame type** that identifies the intended semantic pattern,
- a set of **slots/fields** that supply the required meaning,
- an input shape that can be **validated and normalized** before generation.

Frames are part of the **external/public input contract**. Internally, they may be normalized into domain frame objects and then passed through the runtime pipeline.

---

## How SemantiK Architect interprets Frames

A generation request is processed in stages:

1. the payload is read as JSON,
2. the system detects and normalizes the **canonical `frame_type`**,
3. the payload is converted into an internal frame object,
4. the generation runtime uses that normalized meaning to produce text.

This means client payloads can remain stable even while internal generation architecture evolves.

---

## `frame_type` is authoritative

Every Frame should declare a `frame_type`.

Example:

- `bio`
- `entity.person`
- `event.*`
- `rel.*`
- `narr.*`
- `meta.*`

For compatibility, the system may accept equivalent or legacy frame labels and normalize them to a canonical internal type before generation.

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

This expresses the intended meaning in a simple upstream-friendly format. The renderer is responsible for turning that meaning into language-specific text.

---

## Canonicalization and normalization

SemantiK Architect does **not** rely on raw payload shape alone.

Before generation, the system may:

* normalize equivalent frame labels,
* merge tolerated input variants into a canonical internal frame,
* validate required fields,
* preserve optional metadata such as context or transport-neutral extras.

For example, multiple “bio-like” request shapes may normalize to the same internal bio frame representation.

---

## Frames are the input contract, not the renderer contract

Frames are for **requesting generation**.

Renderers and realization backends should not depend on arbitrary raw JSON payloads. They should receive normalized runtime inputs produced by the generation pipeline.

In other words:

* **clients send Frames**,
* **the runtime normalizes them**,
* **renderers realize normalized meaning**.

This separation keeps the public API stable while allowing internal runtime contracts to evolve.

---

## When to use Frames

Use Frames when you want:

* a **stable JSON contract** for upstream systems,
* **validation and normalization** before generation,
* a format that is easy to author, inspect, and debug,
* compatibility with the public generation API.

Frames are the preferred choice for API clients that want predictable behavior without depending on internal runtime details.

---

## Frames vs Ninai

Use **Frames** when you want:

* a direct generation request format,
* a stable API-facing JSON contract,
* explicit `frame_type`-driven normalization.

Use **Ninai** when you want:

* a more recursive or tree-structured meaning representation,
* an intermediate representation that can be adapted into internal frames,
* a bridge-oriented workflow rather than a direct frame request.

Frames and Ninai are related, but they are not the same layer.

---

## Notes

* Keep `frame_type` explicit whenever possible.
* Prefer semantically clear slot names over language-specific phrasing.
* Do not assume that raw input fields map directly to final surface text.
* Public request stability does not imply that renderers consume raw Frames directly.

See also:

* [[Inputs: Ninai|Inputs-Ninai]]
* [[API Overview|API-Overview]]
* [[Conceptual Flow: Meaning to Text|Conceptual-Flow-Meaning-to-Text]]



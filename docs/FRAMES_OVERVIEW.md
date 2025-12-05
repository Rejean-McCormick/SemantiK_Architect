# Frame Families Overview

This document describes the semantic frame families used by the Abstract Wiki Architect NLG stack. Frames are the main interface between Abstract Wikipedia–style semantics and the multilingual generation pipeline.  

The goal is to:

* provide a small, explicit set of frame families that cover common encyclopedic content,
* keep frame structures language-neutral and data-driven,
* match the public NLG API (`generate`, `generate_bio`, `generate_event`, etc.).

---

## 1. Frames in the NLG API

At the API level, all frames implement a simple protocol:

```python
from typing import Protocol

class Frame(Protocol):
    frame_type: str  # e.g. "bio", "event"
```

In the current implementation, this protocol is exposed from `nlg.semantics`, and concrete frame classes live in `semantics.types`.

The frontend API treats frames uniformly:

```python
# nlg.api (conceptual)
def generate(lang: str, frame: Frame, *, options: GenerationOptions | None = None,
             debug: bool = False) -> GenerationResult: ...
```

Specialized helpers simply fix the frame type: `generate_bio(lang, bio: BioFrame, ...)`, `generate_event(lang, event: EventFrame, ...)`, etc.

### 1.1 Current status

* `BioFrame` (`frame_type = "bio"`) is fully wired end-to-end through the router and family engines.
* `EventFrame` (`frame_type = "event"`) exists as a type but does not yet have a full engine implementation; calls are essentially placeholders until event routing is implemented.

All other frame families described below are **design targets** for the final system: they define a stable taxonomy and expected structure so that semantics, normalisation, and generation can evolve coherently.

---

## 2. Frame lifecycle (end-to-end)

At a high level, frame handling proceeds as follows:

1. **Abstract semantics in**

   * Upstream components (e.g. Abstract Wikipedia / Wikifunctions) provide JSON for one or more frames.
   * `semantics.aw_bridge` and `semantics.normalization` validate and convert this JSON into typed frame instances (e.g. `BioFrame`, `EventFrame`).

2. **Discourse and information structure**

   * `discourse/state.py` tracks discourse context.
   * `discourse/info_structure.py` assigns topic/focus labels.
   * `discourse/referring_expression.py` decides on pronouns vs. full NPs.
   * `discourse/planner.py` sequences multiple frames into multi-sentence plans (e.g. birth → profession → awards). 

3. **Routing and realization**

   * `router.py` selects a family engine and language profile.
   * The engine maps frames to one or more **constructions** (e.g. copular, eventive, comparative) and calls the relevant morphology + lexicon components to realize surface forms.

4. **Aggregation and output**

   * The engine and discourse layer assemble tokens into sentences, apply punctuation, and return a `GenerationResult` with `text`, `sentences`, `lang`, and the original `frame`. 

---

## 3. Design principles for frame families

All 58 frame families follow the same principles:

1. **Language-neutral semantics**

   * Fields describe *what* to say, not *how* to say it (no inflected strings).
   * Entities, times, quantities, and roles are structured objects, usually linked to Wikidata IDs when available.

2. **Stable `frame_type` keys**

   * Each family has a canonical string, e.g. `"person"`, `"organization"`, `"conflict-event"`, `"definition"`, `"timeline"`.
   * These keys are used by:

     * JSON input (`"frame_type": "person"`),
     * normalization,
     * routing,
     * CLI (`--frame-type person`). 

3. **Small, typed dataclasses**

   * For each family there is one main dataclass (e.g. `PersonFrame`) implementing the `Frame` protocol.
   * Additional internal helper types (e.g. `Participant`, `TimelineItem`) are used where needed.

4. **Clear ownership boundaries**

   * **Frames**: semantics, roles, and attributes.
   * **Discourse**: ordering, packaging into paragraphs, referring expressions.
   * **Constructions**: clause templates (copula, event, comparative, etc.).
   * **Morphology + lexicon**: inflection and lexical choice.

5. **Data-driven schemas**

   * Every frame family has a JSON schema (under `schemas/frames/…`) used both for validation and as public documentation of field structure.

---

## 4. Taxonomy of frame families

The final system groups frames into five broad categories:

* **Entity-centric frames** – summarize “things you can write a lead sentence about”.
* **Event-centric frames** – describe episodes in time.
* **Relational frames** – encode reusable binary/ternary facts (definition, membership, cause, etc.).
* **Narrative / aggregate frames** – sequence or aggregate multiple events/facts.
* **Meta / wrapper frames** – describe articles and sections as wholes.

Below is the canonical list of families and their intended `frame_type` keys.

### 4.1 Entity-centric frame families

These frames usually correspond to article subjects and first sentences.

1. `person`
2. `organization`
3. `geopolitical-entity`
4. `place` (non-political geographic feature)
5. `facility` (buildings, infrastructure)
6. `astronomical-object`
7. `species` (and higher taxa)
8. `chemical-material`
9. `artifact` (physical object / object type)
10. `vehicle`
11. `creative-work` (book, film, painting, game, etc.)
12. `software-protocol-standard`
13. `product-brand`
14. `sports-team`
15. `competition-league`
16. `language`
17. `religion-ideology`
18. `discipline-theory`
19. `law-treaty-policy`
20. `project-program`
21. `fictional-entity` (character, universe, franchise)

Each of these frames holds:

* a main `Entity` (e.g. `main_entity: Entity`),
* key attributes (type, domain, dates, locations, membership sizes, etc.),
* optional auxiliary fields used by narrative frames (e.g. founding date reused by a timeline).

### 4.2 Event-centric frame families

These frames model temporally bounded episodes.

22. `generic-event`
23. `historical-event`
24. `conflict-event` (battle, war, operation)
25. `election-referendum`
26. `disaster-accident`
27. `scientific-technical-milestone`
28. `cultural-event` (festival, premiere, exhibition, ceremony)
29. `sports-event` (match, season, tournament instance)
30. `legal-case-event`
31. `economic-financial-event` (crisis, merger, IPO, sanctions episode)
32. `exploration-expedition-mission`
33. `life-event` (education, appointment, award, marriage, relocation)

All event families refine a shared backbone:

* participants with typed roles,
* time spans,
* location(s),
* event-specific properties (scores, magnitudes, verdicts, etc.).

### 4.3 Relational / statement-level frame families

These frames encode reusable fact templates that can be inserted anywhere in an article.

34. `definition` (definition / classification)
35. `attribute` (simple property)
36. `quantitative-measure` (numeric/statistical fact)
37. `comparative-ranking`
38. `membership-affiliation`
39. `role-position-office`
40. `part-whole-composition`
41. `ownership-control`
42. `spatial-relation`
43. `temporal-relation`
44. `causal-influence`
45. `change-of-state`
46. `communication-statement`
47. `opinion-evaluation`
48. `relation-bundle` (small, multi-fact cluster for one subject)

Implementation-wise, many of these are thin, typed wrappers around more generic types (`Entity`, `Event`, `Quantity`, `TimeSpan`), plus role labels.

### 4.4 Narrative / aggregate frame families

These frames describe sequences and aggregates, usually spanning multiple sentences.

49. `timeline` (chronology for a subject)
50. `career-season-campaign-summary`
51. `development-evolution` (changes over time)
52. `reception-impact`
53. `structure-organization` (internal structure of an entity)
54. `comparison-set-contrast` (paragraph-level comparison)
55. `list-enumeration` (enumerative descriptions)

These frames typically contain:

* a `subject` entity,
* ordered collections of subframes (e.g. events, relational frames),
* optional grouping into phases or sections.

### 4.5 Meta / wrapper frame families

These are not article content per se, but describe how content is packaged.

56. `article-document`
57. `section-summary`
58. `source-citation`

They are useful for:

* mapping Abstract Wikipedia article structures to concrete sections,
* summarizing sections into short leads,
* tracking provenance and citation requirements for generated statements.

---

## 5. Implementation layout (high-level)

The frames described above are implemented and wired across several layers:

* **Semantics** (`semantics/`)

  * `semantics.types`: core dataclasses (`Entity`, `Event`, `BioFrame`, etc.). 
  * `semantics.normalization`: JSON → frame conversion, validation, and defaults. 
  * `semantics.aw_bridge`: bridges from Abstract Wikipedia / Wikifunctions data formats.

* **NLG semantics API** (`nlg/semantics/__init__.py`)

  * Exposes `Frame`, `BioFrame`, `EventFrame` (and, in the final design, all other frame classes) to the rest of the NLG stack. 

* **Frontend API** (`nlg/api.py`, `docs/FRONTEND_API.md`, `docs/Interfaces.md`)

  * Public entry points (`generate`, `generate_bio`, `generate_event`, `NLGSession`).

* **Discourse** (`discourse/`)

  * Planning, referring expressions, information structure, and packaging. 

* **Router and engines** (`router.py`, `engines/*.py`, `language_profiles/profiles.json`)

  * Language routing, engine selection, and morphology/lexicon configuration.

---

## 6. Usage and extension guidelines

When adding or extending frame families:

1. **Decide the family and `frame_type`**

   * Choose the appropriate family from sections 4.1–4.5.
   * Introduce a new `frame_type` only if no existing family fits.

2. **Define the dataclass**

   * Add a typed dataclass in `semantics.types` (or a dedicated submodule) implementing `Frame`.
   * Ensure it uses existing primitives (`Entity`, `TimeSpan`, `Quantity`, etc.) where possible.

3. **Define the JSON schema**

   * Add a schema under `schemas/frames/…` documenting all fields and their types.
   * Use the schema for validation in `semantics.normalization`.

4. **Implement normalization**

   * Map incoming JSON (from AW / Z-objects) to the dataclass, applying defaults and light coercion.
   * Reject malformed input early with clear error messages.

5. **Wire up routing and realization**

   * Update the routing logic so `frame_type` → appropriate realization path.
   * Map each frame family to constructions that can express its facts in at least one sentence.

6. **Add tests and examples**

   * Provide unit tests for normalization and realization.
   * Add small example JSON snippets and expected outputs for major languages.

By following this taxonomy and workflow, all 58 frame families can be added incrementally while keeping the overall API and architecture stable.

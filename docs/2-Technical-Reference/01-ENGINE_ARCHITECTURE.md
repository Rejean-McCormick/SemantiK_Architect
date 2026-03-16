# 🏛️ Engine Architecture & Internals

**SemantiK Architect v2.1**

## 1. High-Level System Overview

SemantiK Architect is a **planner-centered multilingual NLG system** for generating structured, traceable text from semantic inputs.

Its architectural center is **not** any one renderer, grammar formalism, or language-specific engine. The stable center is the shared runtime pipeline:

```text
API/request
  -> frame normalization
  -> frame-to-plan bridge
  -> planner
  -> PlannedSentence
  -> ConstructionPlan
  -> lexical resolution
  -> renderer backend
  -> SurfaceResult
  -> API response mapping
````

This design allows SemantiK Architect to combine:

* **semantic frames** as structured input,
* **construction planning** as the source of sentence truth,
* **lexical resolution** as a shared multilingual layer,
* **multiple realization backends** such as GF/PGF, family renderers, and safe-mode fallback.

The system is built for **deterministic, inspectable multilingual generation**, with explicit support for broad language coverage and backend diversity.

---

## 2. Architectural Principles

### 2.1 One source of runtime truth

The planner and shared construction runtime define **what is being said**.

Renderers define only **how that plan is realized** in a particular backend or language.

No renderer, engine, or router should be an independent source of sentence-planning truth.

### 2.2 Construction-first, not bio-first

Biography is an important early domain and migration target, but it is **not** the architecture.

The runtime is intended to support multiple construction families, including:

* equative / classification
* attributive copular
* locative
* existential
* possession
* eventive
* relative-clause
* topic-comment
* comparative / superlative
* coordination

### 2.3 Backend independence

The same semantic intent should be able to flow through different realization technologies:

* **GF / PGF**
* **family renderers**
* **safe-mode fallback**

GF is a renderer backend and tooling source, **not the architecture itself**.

### 2.4 Shared semantics, thin language specialization

The architecture scales by sharing:

* frame normalization,
* planning,
* construction IDs,
* slot semantics,
* lexical binding structure,
* renderer contracts.

Language-specific logic should be limited to:

* lexical forms,
* morphology,
* local syntax / word order,
* idiomatic overrides,
* construction-specific realization details where required.

---

## 3. Runtime Layers

### Layer A: Semantic Inputs & Frame Normalization

**Role:** Convert external inputs into stable internal generation commands.

This layer accepts API payloads and normalizes them into domain objects.

Current input families include:

* flat frame payloads such as biography/person-style requests,
* compatibility aliases for person/bio payloads,
* Ninai-shaped payloads where supported.

Key responsibilities:

* resolve the authoritative language code,
* normalize payload variants,
* reject malformed or contradictory requests,
* strip transport-only fields from the domain payload.

This layer is where input compatibility is handled. It is **not** where sentence planning should live.

---

### Layer B: Planning & Construction Runtime

**Role:** Decide the sentence structure to be realized.

This is the architectural core.

The planner-centered runtime is responsible for producing a shared representation of sentence intent, including:

* `PlannedSentence`
* `construction_id`
* topic/focus metadata
* slot layout
* realization options
* construction-level semantics

This layer is the authoritative center for:

* sentence type,
* information packaging,
* construction choice,
* discourse-aware decisions.

The target runtime contract is:

```text
frame normalization
  -> frame-to-plan bridge
  -> planner
  -> PlannedSentence
  -> ConstructionPlan
```

---

### Layer C: Lexicon & Lexical Resolution

**Role:** Bind planned slots to language-appropriate lexical material.

Lexical resolution is a distinct layer between planning and realization. It is not just preprocessing.

This layer handles:

* entity references,
* lexical bindings,
* lemma selection,
* morphology-relevant lexical metadata,
* provenance such as Wikidata QIDs or source-specific IDs where available.

The lexicon remains a separate subsystem and a shared concern across backends.

This separation is important because the same construction plan may be realized by different backends, but they must operate over the same lexicalized intent.

---

### Layer D: Renderer Backends & Surface Realization

**Role:** Realize a shared construction-level plan into surface output.

Renderer backends are interchangeable surface technologies operating over the same runtime contract.

Supported backend classes include:

* **GF / PGF renderer**
* **family-oriented renderer**
* **safe-mode fallback renderer**

The renderer produces a `SurfaceResult`, which is then mapped to the public API response.

Possible output forms include:

* natural-language text,
* debug traces / runtime metadata,
* backend-specific diagnostics,
* structured exports where supported.

A backend may be strong for some `(lang_code, construction_id)` pairs and unavailable for others. Capability is therefore backend-specific, language-specific, and construction-specific.

---

### Cross-Cutting Concern: Context & Discourse State

**Role:** Support discourse-aware generation beyond isolated single sentences.

The repository includes discourse planning and stateful components for things such as:

* topic tracking,
* focus management,
* referring expressions,
* pronominalization,
* session continuity.

This is a **cross-cutting runtime concern**, not a separate renderer.

When enabled, context should influence planning and reference choice through the planner/runtime layer, not by ad hoc string rewriting after realization.

---

## 4. Current Runtime Status vs Target Runtime

### Target architecture

The intended authoritative runtime is:

```text
API payload
  -> frame normalization
  -> frame-to-plan bridge
  -> planner
  -> PlannedSentence
  -> ConstructionPlan
  -> lexical resolution
  -> renderer backend
  -> SurfaceResult
  -> API response mapping
```

### Current live behavior

The repository still documents and supports a **compatibility path** in which single-sentence generation may bypass the full planner-centered path and call a realization engine more directly after frame normalization.

That compatibility path is operational and useful during migration, but it is **not** the final architectural center.

So the correct reading is:

* **planner-centered construction runtime** = target source of truth
* **direct frame-to-engine generation** = compatibility shim during migration

This distinction matters because “it generates text” is not the same as “it is fully aligned with the final runtime contract.”

---

## 5. Realization Strategy & Language Coverage

SemantiK Architect supports a hybrid realization strategy to balance quality, scale, and graceful degradation.

### Tier 1: GF / expert-grade realization

Used where strong concrete grammars and runtime support exist.

Strengths:

* richer morphology,
* stronger syntax control,
* higher-quality realization for supported constructions.

### Tier 2: Curated / override layers

Used where manual or project-maintained overrides improve quality beyond generic defaults.

This layer can refine language-specific behavior without redefining the architecture.

### Tier 3: Safe-mode / fallback realization

Used to preserve runtime continuity when stronger renderers are unavailable for a given language/construction pair.

This layer exists for coverage and fault tolerance, not as the architectural ideal.

### Important rule

A language being routable to a backend is **not** the same thing as that language being fully validated for production-grade realization.

Validation must be tracked separately at the level of:

* language,
* construction family,
* backend,
* test coverage,
* gold-example quality.

---

## 6. GF in the Architecture

GF is an important part of the system, but its role must be understood correctly.

### GF is:

* a realization backend for selected runtime plans,
* an offline source of grammar knowledge and QA examples,
* a valuable resource for high-quality multilingual realization.

### GF is not:

* the core architecture,
* the planner,
* the public API contract,
* the authoritative semantic representation,
* the only supported realization technology.

SemantiK Architect may compile and use GF assets such as:

* abstract grammar definitions,
* concrete `Wiki*` modules,
* PGF artifacts,
* language-specific GF-backed realization paths.

But runtime authority remains with the shared planner/construction contract.

---

## 7. Build, Artifacts, and Validation

The build/tooling layer exists to assemble, validate, and audit multilingual realization assets.

Important concerns include:

* language inventory / matrix generation,
* grammar-path discovery,
* compile audits,
* runtime health checks,
* capability tracking,
* language-level validation.

The key artifact for GF-backed runtime use is the compiled PGF/grammar set, but architecture correctness cannot be inferred from build success alone.

A language is only meaningfully integrated when the system can demonstrate:

* successful build or capability discovery,
* successful runtime generation,
* correct construction-level behavior,
* acceptable surface quality,
* regression-safe validation.

---

## 8. Hexagonal Architecture

The backend follows **ports and adapters** so that domain logic stays isolated from infrastructure.

### Core domain / application responsibilities

The core is responsible for:

* frame/domain models,
* planning logic,
* construction-level abstractions,
* shared runtime contracts,
* use-case orchestration.

### Adapters

Adapters connect the core to external systems, including:

* the HTTP API,
* persistence and filesystem access,
* GF runtime wrappers,
* Redis or messaging infrastructure,
* exporter layers,
* tooling and operational services.

Dependencies point inward: adapters depend on core/application code, not the reverse.

This structure keeps the architectural center stable even as external technologies change.

---

## 9. Automation, QA, and Operational Tooling

The repository contains optional tooling and agent-oriented components for authoring, repair, QA, and maintenance.

These may include builder, judge, or repair-oriented workflows.

They should be understood as **operational tooling**, not as part of the deterministic core runtime contract.

Core generation should remain understandable without assuming any AI service is active.

The right separation is:

* **core runtime** = deterministic generation architecture
* **automation/tooling** = assistance for build, QA, repair, or maintenance

---

## 10. Request Lifecycle

### 1. Ingest

A client sends a request to the generation API.

Typical route shape:

```text
POST /api/v1/generate/{lang_code}
```

### 2. Normalize

The API layer:

* resolves the authoritative language code,
* validates payload shape,
* normalizes compatible frame variants,
* maps the request into domain form.

### 3. Plan

The target path converts the normalized frame into a plan-oriented representation and produces:

* `PlannedSentence`
* `ConstructionPlan`
* runtime metadata such as `construction_id`

### 4. Resolve Lexicon

The system binds planned slots to lexical material needed for realization.

### 5. Realize

A selected backend realizes the construction plan:

* GF / PGF if available and appropriate,
* family renderer if selected,
* safe mode if needed.

### 6. Map to Public Response

The internal surface result is converted into the public API response.

The public response should remain clearly distinguished from internal runtime objects.

---

## 11. Public API Response vs Internal Runtime Objects

It is important not to confuse internal and external contracts.

### Internal runtime objects

Examples include:

* `PlannedSentence`
* `ConstructionPlan`
* lexical bindings
* `SurfaceResult`

These are runtime contracts inside the system.

### Public API response

The API exposes a user-facing response envelope, including surface text and runtime/debug metadata intended for clients.

The public API response is a mapped external view of internal runtime results. It should not be documented as if it were the runtime contract itself.

---

## 12. Directory Map & Key Files

| Path                                                       | Component              | Role                                                                            |
| ---------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------- |
| `app/adapters/api/contracts/generation_request_mapper.py`  | Request normalization  | Resolves language, normalizes payload variants, maps HTTP input to domain input |
| `app/adapters/api/contracts/generation_response_mapper.py` | Response mapping       | Maps internal generation results to the public API contract                     |
| `app/adapters/api/routers/generation.py`                   | API route              | HTTP entry point for generation                                                 |
| `app/adapters/engines/`                                    | Renderer backends      | GF, family, and safe-mode realization adapters                                  |
| `app/adapters/persistence/lexicon/`                        | Lexical infrastructure | Lexicon access, caching, indexing, and entity/lexeme resolution                 |
| `discourse/`                                               | Context and discourse  | State, referring expressions, discourse planning                                |
| `gf/`                                                      | GF grammars            | Abstract and concrete GF modules used by GF-backed realization                  |
| `schemas/contracts/`                                       | Runtime contracts      | Shared schemas for construction/runtime structures                              |
| `schemas/frames/`                                          | Frame schemas          | Structured semantic input families                                              |
| `tools/language_health/`                                   | Validation tooling     | Compile audits, runtime checks, reporting                                       |
| `tools/everything_matrix/`                                 | Inventory/tooling      | Language/resource scanning and matrix generation                                |
| `builder/orchestrator/`                                    | Build orchestration    | Build and assembly workflows for grammar/runtime assets                         |

---

## 13. What This System Is Not

SemantiK Architect is **not**:

* a pure template engine,
* a GF-only architecture,
* a biography-only system,
* a renderer-first design,
* an LLM-only generation stack,
* a system where build success alone proves language readiness.

It is best understood as a **planner-first, construction-centered, backend-flexible multilingual NLG platform**.

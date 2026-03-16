# 4. Conceptual Flow: Meaning → Text

SemantiK Architect is **generation-first**: it does not interpret raw text. It takes a **normalized meaning input** and realizes it into surface language through a **planner-first, construction-centered runtime**.

## Flow (at a glance)

**Meaning input (Frame, or adapter-fed Ninai-style structure)**  
→ **Normalize meaning**  
→ **Plan sentences and discourse choices**  
→ **Assemble a canonical ConstructionPlan**  
→ **Resolve lexical bindings**  
→ **Realize with a renderer backend**  
→ **Return a SurfaceResult**  
→ **Map to public API/output formats**  
→ **Run optional QA / regression checks**

## Step-by-step

1. **Provide meaning (input)**  
   SemantiK Architect accepts meaning-first inputs. In practice, the stable production-facing input is a **normalized frame**, while more experimental or upstream structures (including Ninai-style trees) can be adapted into the same internal generation flow.

2. **Normalize meaning (adapter stage)**  
   Incoming payloads are validated and normalized into internal semantic/domain objects:
   - required fields are checked
   - naming is normalized
   - defaults are resolved
   - upstream adapter formats are converted into the same internal meaning layer

   This is **not text parsing**. It is structured meaning normalization.

3. **Plan sentences (planner stage)**  
   The planner is the first authoritative runtime stage. It transforms normalized meaning into **backend-neutral sentence plans**:
   - preserves the intended meaning
   - chooses or finalizes the `construction_id`
   - packages content into sentence-sized units
   - applies discourse-aware choices such as topic/focus
   - stays independent of any specific renderer backend

   The planner may reorganize presentation for discourse purposes, but it must not silently change the underlying meaning.

4. **Assemble the canonical ConstructionPlan**  
   Planned content is assembled into a **ConstructionPlan**, which is the shared runtime contract passed to all renderers. A ConstructionPlan makes the realization boundary explicit by carrying:
   - `construction_id`
   - `lang_code`
   - `slot_map`
   - `generation_options`
   - optional discourse fields such as `topic_entity_id` and `focus_role`
   - optional `lexical_bindings`
   - optional provenance / metadata for debugging and traceability

   This is the point where SemantiK Architect makes the intended construction and semantic roles fully explicit.

5. **Resolve lexical bindings**  
   Before realization, the runtime may enrich the plan with normalized lexical information for specific slots. This is where the system can attach lexical references and confidence/provenance data instead of relying only on raw strings. The goal is to keep lexical resolution explicit and shared across backends.

6. **Realize surface text (renderer stage)**  
   A renderer backend consumes the **same ConstructionPlan** and produces the final surface text. The canonical realization boundary is:

   **ConstructionPlan → SurfaceResult**

   Different renderers may exist (for example GF, family-engine, or safe-mode style backends), but they must all respect the same construction-centered contract. A renderer may fail when a plan is unsupported or under-specified, but it must not silently reinterpret the construction.

7. **Return a canonical SurfaceResult**  
   Realization returns a shared runtime result that includes:
   - `text`
   - `lang_code`
   - `construction_id`
   - `renderer_backend`
   - `fallback_used`
   - optional token/debug information

   This keeps runtime behavior observable and makes fallback or downgrade decisions explicit.

8. **Map to public outputs**  
   Public API responses and other output formats should be derived from the shared runtime result, not from backend-private payloads. This keeps the public contract aligned with the runtime contract and avoids renderer-specific drift.

9. **Run optional QA / regression checks**  
   Generated output can be compared against **Gold Standards** and checked by automated evaluation workflows such as the **Judge**. This closes the loop operationally: improvements should remain stable, regressions should be detected, and quality should be enforced continuously rather than treated as a one-off manual check.

## Migration note

The **authoritative architecture** is planner-first and construction-centered. Some legacy code may still use a direct frame-to-engine path during migration, but that path is a **compatibility layer**, not the long-term runtime model.
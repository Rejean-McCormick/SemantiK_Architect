
# 📐 Schema Alignment Protocol & The "Triangle of Doom"

**Abstract Wiki Architect v2.0**

## 1. The Core Problem: Alignment Failure

In the v2.0 architecture, a runtime error (`400 Bad Request`) often occurs not because code is broken, but because the system's three definitions of "Truth" are out of sync.

We call this the **Triangle of Doom**:

1.  **The API Contract (Input):** What the user sends (JSON). Defined in `schemas/*.json` and `app/adapters/ninai.py`.
2.  **The Abstract Grammar (Interface):** What the engine accepts (GF). Defined in `gf/AbstractWiki.gf`.
3.  **The Factory Logic (Generator):** What the builder produces (Python). Defined in `utils/grammar_factory.py`.

### The Symptom
* **Error:** `Function 'mkBio' not found in grammar` or `unknown function` in compiler logs.
* **Cause:** The API sent a `frame_type="bio"` (expecting `mkBio`), but the Abstract Grammar only defined `mkFact`.

---

## 2. The Solution: Manual Propagation Protocol

Until a "Schema-to-Grammar" compiler is built, we explicitly adopt a **Manual Propagation Strategy**. To add or fix a Semantic Frame (e.g., `Event`, `Bio`, `Location`), you **MUST** update all three vertices of the triangle simultaneously.

### Step 1: Update the Interface (Abstract Grammar)
**File:** `gf/AbstractWiki.gf`

Define the function signature. Use generic types (`Entity`, `Property`) to avoid type explosion.

```haskell
fun
  -- Adding support for Bio frames
  mkBio : Entity -> Property -> Property -> Fact ;
  
  -- Adding support for Event frames (Future)
  mkEvent : Entity -> Entity -> Fact ; 

```

### Step 2: Update the Factory (Tier 3 Generation)

**File:** `utils/grammar_factory.py`

Teach the "Safe Mode" generator how to linearize this new function for under-resourced languages (Strings).

```python
def generate_safe_mode_grammar(lang_code):
    # ...
    gf_code = f"""
    lin
      -- Hardcoded SVO stub for Bio
      mkBio name prof nat = name ++ "is a" ++ nat ++ prof;
      
      -- Hardcoded stub for Event
      mkEvent subject event = subject ++ "participated in" ++ event;
    """

```

### Step 3: Update Tier 1 Concrete Grammars

**File:** `gf/WikiEng.gf` (and other RGL languages)

You must manually implement the linearization for High-Resource languages, or the build will fail during Phase 2 Linking.

```haskell
lin
  mkBio name prof nat = name ++ "is a" ++ nat ++ prof ;

```

---

## 3. Decision Record (ADR)

### Context

The API layer (`NinaiAdapter`) is dynamic and handles optional JSON fields. The Grammar layer (`GF`) is static, strictly typed, and requires fixed arity (argument counts).

### Decision

We choose **Explicit Semantic Mapping** over **Generic Triples**.

* **Option A (Rejected):** Use a generic `mkTriple : Subject -> Predicate -> Object -> Fact` for everything.
* *Pros:* No need to update grammar for new frames.
* *Cons:* Loses semantic nuance (e.g., "Born in" vs "Located in") required for accurate translations and UD tagging.


* **Option B (Accepted):** Define specific functions `mkBio`, `mkEvent`.
* *Pros:* Allows language-specific handling (e.g., French uses "né en" for birth, "situé à" for location).
* *Cons:* Requires the 3-step manual update process described above.



### Future Roadmap

To automate this, we will eventually implement an **Abstract Generator** script that reads `schemas/frames/*.json` and auto-generates `AbstractWiki.gf` during the build pre-flight check.

```

```
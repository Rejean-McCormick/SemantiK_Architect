**Language Integration Workflow**
Quick Reference

Purpose: the normal deterministic path to add or repair one language without drifting away from the runtime contract.

| Core rule: change source files first, then refresh the Everything Matrix. The matrix is the system snapshot and status view, not the source of edits. |
| :---------------------------------------------------------------------------------------------------------------------------------------------------- |

# **Normal workflow**

## **1. Add or change language files**

Put grammar, config, and lexicon files in place first.
Do not treat generated artifacts or matrix output as the source of truth. 

## **2. Refresh the Everything Matrix**

Rebuild the matrix so the repo re-discovers the language, rebuild strategy, lexicon status, app status, and QA status.
This step is required before trusting later compile or health results. 

## **3. Validate the lexicon**

Run lexicon validation before compile.
The goal is to catch thin, empty, malformed, or structurally unusable lexical data early, before build and runtime checks. 

## **4. Fill gaps only if needed**

If coverage is too thin, use deterministic lexicon tools to import or fill gaps.
These are repair tools, not part of the shortest normal path when the lexicon is already good enough.  

## **5. Bootstrap Tier 1 scaffolding only if needed**

Use Tier 1 bootstrap only when the language is missing required scaffolding.
Do not run it as a routine step for languages that already have working source files. 

## **6. Compile the PGF**

Compile after the matrix refresh and lexicon validation.
This is the point where the language must enter the grammar binary cleanly. 

## **7. Validate compile and runtime**

Run language health in both modes so compile and runtime are checked together.
This is where you confirm that the language is not only buildable but callable through the runtime.  

## **8. Generate one real sentence**

Use the dev smoke path or call `/api/v1/generate/<lang>` and verify a real surface result comes back.
Do not stop at “some text appeared”. Confirm at minimum:

* non-empty `text`
* correct `lang_code`
* visible `renderer_backend`
* explicit `fallback_used`
* usable `debug_info` for runtime diagnosis   

## **9. Confirm runtime path explicitly**

When you inspect `debug_info`, verify which runtime path actually ran.
The target architecture is planner-first; if the language is still served through the legacy direct path, that must stay explicit and treated as compatibility state, not hidden success.  

## **10. Stabilize**

Run judge or regression only after the language builds and generates.
Then refresh the matrix again so final build and QA status are recorded in the system snapshot.  

# **Exact tool calls**

| Step                               | Command                                                                                                                         |   |
| :--------------------------------- | :------------------------------------------------------------------------------------------------------------------------------ | - |
| Refresh matrix                     | `build_index --langs <lang> --regen-rgl --regen-lex --regen-app --regen-qa --verbose`                                           |   |
| Validate lexicon                   | `lexicon_coverage --lang <lang> --include-files`                                                                                |   |
| Fill lexical gaps (only if needed) | `harvest_lexicon ...` or `gap_filler --langs <lang> --pivot en --verbose`                                                       |   |
| Bootstrap Tier 1 (only if needed)  | `bootstrap_tier1 --langs <lang> --verbose`                                                                                      |   |
| Compile PGF                        | `compile_pgf --langs <lang> --verbose`                                                                                          |   |
| Validate health                    | `language_health --mode both --langs <lang> --json --verbose`                                                                   |   |
| Generate sentence                  | Use Dev smoke test or call `/api/v1/generate/<lang>`                                                                            |   |
| Stabilize                          | `run_judge --langs <lang> --verbose` then `build_index --langs <lang> --regen-rgl --regen-lex --regen-app --regen-qa --verbose` |   |

# **Required vs optional**

| Required in the normal path         | Use only when needed                              |   |
| :---------------------------------- | :------------------------------------------------ | - |
| `build_index`                       | `run_judge`                                       |   |
| `lexicon_coverage`                  | `harvest_lexicon`                                 |   |
| `compile_pgf`                       | `gap_filler`                                      |   |
| `language_health`                   | `bootstrap_tier1`                                 |   |
| one real generation test            | `diagnostic_audit`                                |   |
| runtime-path check via `debug_info` | low-level scanners and pytest-only recovery tools |   |

# **Dependencies to remember**

* Use ISO-2 language codes in tool calls, for example `en`, `fr`, `pt`. 
* Refresh the matrix after source changes because later compile and status decisions depend on that snapshot. 
* Validate the lexicon before compile so empty or broken lexical shards are caught early. 
* Compile before final health validation so runtime checks are not reading stale binaries. 
* A language is not truly integrated until it generates a sentence through the runtime. 
* For migrated constructions, the authoritative target is planner-first orchestration with shared runtime contracts; legacy direct generation may still exist during migration, but it must remain explicit in diagnostics.  
* A successful generation check should validate the runtime result shape, not only the presence of text. The stable top-level diagnostics are `construction_id`, `renderer_backend`, and `fallback_used`, with additional detail in `debug_info`.  

# **Definition of done for one language**

A language can be considered integrated for the normal path when all of the following are true:

* source files are in place
* the matrix sees the language correctly
* lexicon validation passes
* PGF compile passes
* runtime health passes
* one real generation succeeds for `/api/v1/generate/<lang>`
* the result exposes valid runtime diagnostics
* any fallback or legacy-path usage is explicit, not hidden  

For stronger acceptance on core constructions, add regression and judge coverage after the normal path is green. English and French planner-first integration coverage is part of the broader migration target, not just a nice-to-have. 


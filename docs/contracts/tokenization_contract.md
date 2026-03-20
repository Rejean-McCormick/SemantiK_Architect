# Tokenization Contract

Status: normative
Owner: Runtime / API
Scope: runtime and public semantics of the canonical `tokens` field carried by `SurfaceResult` and serialized into generation responses

---

## 1. Purpose

This document defines the canonical meaning, production rules, normalization rules, and public obligations for the `tokens` field used in SemantiK Architect generation results.

It exists to ensure that:

* runtime producers and response mappers expose one stable token field,
* clients receive predictable token arrays,
* planner-first nominal success does not rely on hidden mapper repair,
* migration paths do not invent backend-specific token contracts,
* test code can rely on deterministic behavior,
* token transport stays clearly separated from lexical resolution, slot planning, and deeper linguistic annotation.

This contract is intentionally narrow.

It defines how `tokens` are represented, required, normalized, and exposed.
It does **not** define a full linguistic tokenization theory.

---

## 2. Scope

This document defines:

* the meaning of `tokens` in `SurfaceResult`,
* the normalization rules for token values supplied by runtime producers,
* fallback token derivation behavior for compatibility paths,
* the guarantees clients may rely on,
* the obligations of runtime producers and response mappers,
* and the acceptance semantics of `tokens` on the nominal planner-first path.

This document does **not** define:

* lexical segmentation for all languages,
* morphology-aware token decomposition,
* grapheme or subword segmentation,
* UD tokenization,
* sentence splitting,
* clause boundary detection,
* search or index normalization.

---

## 3. Canonical field

`tokens` is the canonical ordered token sequence associated with the final realized surface text.

It appears in runtime results such as `SurfaceResult` and in the public generation success envelope.

Canonical shape:

```json id="l2s3p7"
{
  "tokens": ["Marie Curie", "était", "une", "physicienne", "polonaise."]
}
```

Rules:

* `tokens` MUST be an ordered sequence of strings.
* `tokens` MUST correspond to the final returned surface text.
* `tokens` MUST NOT encode planner slots, lexical bindings, AST fragments, or backend control strings.
* `tokens` MUST remain transport-oriented and lightweight.
* `tokens` is the only canonical top-level token field for realized text.

---

## 4. Meaning of a token

In this repository, a token is a **surface chunk** of the final text, not a linguistically complete or language-universal tokenization unit.

A token MAY be:

* a whitespace-separated word-like piece,
* a multi-word surface chunk if the producer emits it that way,
* a punctuation-bearing item such as `mathematician.`,
* a larger atomic chunk such as `Marie Curie`.

This is important:

* the runtime does **not** force one universal token granularity,
* a producer may provide a higher-level surface grouping,
* compatibility fallback behavior is simpler and whitespace-driven.

Therefore, clients MUST treat `tokens` as a stable ordered surface sequence, not as a guaranteed morphology-grade tokenization.

---

## 5. Source-of-truth rule

The source-of-truth for `tokens` is:

1. runtime-produced `tokens`, if present and valid,
2. otherwise compatibility fallback derivation from the final `text`.

This precedence is mandatory.

If a runtime producer provides valid `tokens`, the mapper MUST preserve them after normalization.
If no valid tokens are provided, compatibility fallback MAY derive them from `text` under the rules below.

---

## 6. Final-path strictness rule

This is the most important rule in this contract.

### 6.1 Nominal planner-first rule

On the **nominal planner-first path**, `tokens` MUST already be present in the runtime `SurfaceResult` before public response mapping.

That means:

* `tokens` MUST be explicit on nominal planner-first success,
* `tokens` MUST NOT be omitted on nominal planner-first success,
* mapper-side fallback token derivation MUST NOT be treated as nominal planner-first steady-state behavior.

### 6.2 Compatibility rule

Fallback derivation from `text` exists for:

* compatibility paths,
* migration tails,
* older internal result shapes,
* explicit degraded or legacy behavior.

It does **not** define the final steady-state obligation for nominal planner-first results.

### 6.3 Public-envelope rule

The public success envelope always includes `tokens`.

If runtime did not provide valid tokens on a compatibility path, the mapper must still emit canonical `tokens` before public serialization.

So:

* public transport still guarantees `tokens`,
* but nominal planner-first runtime must arrive mapper-ready with `tokens` already present.

---

## 7. Normalization rules

Normalization behavior is intentionally simple.

## 7.1 Input value: `null`

If the incoming token value is `null`, normalized `tokens` MUST become an empty sequence.

Example:

```json id="x3z1v0"
{
  "tokens": []
}
```

## 7.2 Input value: string

If the incoming token value is a string:

* trim surrounding whitespace,
* if the trimmed string is non-empty, normalize to a single-item sequence,
* if the trimmed string is empty, normalize to an empty sequence.

Examples:

Input:

```json id="k7m5n2"
"Alan Turing"
```

Normalized:

```json id="h1q8y4"
["Alan Turing"]
```

Input:

```json id="d6w4c1"
"   "
```

Normalized:

```json id="b9e2r5"
[]
```

## 7.3 Input value: sequence

If the incoming token value is a sequence:

* keep only items that are strings,
* trim each item,
* drop empty strings after trimming,
* preserve original order,
* do not split individual items further,
* do not deduplicate.

Example:

Input:

```json id="t8u4i6"
[" Alan ", "", "Turing", null, " mathematician. "]
```

Normalized:

```json id="g5f1l3"
["Alan", "Turing", "mathematician."]
```

## 7.4 Input value: other type

If the incoming token value is any other type, normalized `tokens` MUST become an empty sequence.

---

## 8. Compatibility fallback derivation from `text`

If normalized runtime tokens are empty and the final surface `text` is available, tokens MAY be derived from `text` by simple whitespace splitting **only for compatibility handling**.

Fallback derivation rule:

* split `text` on whitespace,
* drop empty parts,
* preserve resulting order,
* do not perform punctuation splitting,
* do not perform language-specific segmentation,
* do not alter case,
* do not strip punctuation attached to a part.

Example:

Text:

```text id="a2p9s6"
Alan Turing is a British mathematician.
```

Fallback tokens:

```json id="m4j8q2"
["Alan", "Turing", "is", "a", "British", "mathematician."]
```

This fallback is intentionally minimal and deterministic.

It is a compatibility rule, not the nominal planner-first target.

---

## 9. Invariants

The following invariants are mandatory.

## 9.1 Order invariant

`tokens` MUST preserve surface order.

## 9.2 Surface invariant

Joining or reading `tokens` left-to-right must reflect the same realized text sequence as the final `text`, modulo token-boundary granularity and whitespace compression.

## 9.3 Final-text invariant

`tokens` MUST correspond to the final returned surface text, not to:

* an intermediate AST,
* a slot map,
* a lexical binding inventory,
* a partially realized template.

## 9.4 Stability invariant

For a given generation path and identical runtime output, token normalization MUST be deterministic.

## 9.5 Non-empty item invariant

A normalized token sequence MUST NOT contain empty strings.

## 9.6 Public-field invariant

Every successful public generation response MUST include top-level `tokens`.

## 9.7 Nominal-path invariant

Every nominal planner-first `SurfaceResult` MUST include top-level `tokens` before mapping.

---

## 10. What clients may rely on

Clients MAY rely on the following:

* `tokens` is always ordered,
* each token is a string,
* empty tokens are removed,
* a valid producer-provided non-empty token sequence is preferred over fallback splitting,
* compatibility fallback tokenization is whitespace-based and deterministic,
* punctuation may remain attached to tokens,
* multi-word tokens may occur,
* successful public responses always include `tokens`.

Clients MUST NOT rely on the following unless another contract says so:

* one-token-per-word,
* one-token-per-morpheme,
* one-token-per-grapheme cluster,
* punctuation always split into separate tokens,
* compatibility with UD tokenization,
* stable multilingual word-segmentation quality.

---

## 11. Relationship to other contracts

## 11.1 `ConstructionPlan`

`ConstructionPlan` does not own tokenization.
Tokenization belongs only after realization.

## 11.2 `SurfaceResult`

`SurfaceResult` is the runtime object that carries `tokens` alongside:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `debug_info`
* `generation_time_ms`

## 11.3 Public generation response

The public API success envelope exposes `tokens` directly.
It must preserve the semantics defined here.

## 11.4 Debug info

Debug metadata may describe how tokens were produced, but `tokens` itself remains a first-class top-level field, not a debug-only artifact.

## 11.5 Runtime vs public vs frontend boundary

`tokens` belongs to:

* the runtime result layer,
* the public HTTP transport layer,
* and optionally frontend or client consumers that mirror the public response.

It does not become a planner field, lexical-resolution field, or frontend-only convenience invention.

---

## 12. Producer obligations

A renderer or runtime producer that emits `tokens` MUST:

* provide tokens aligned with final text,
* avoid empty token items,
* avoid backend-local placeholder strings,
* keep token order stable,
* emit surface-oriented token chunks.

A producer MUST NOT:

* emit planner slot names instead of surface tokens,
* emit hidden backend control strings,
* emit tokens for an earlier unnormalized draft of the sentence.

### 12.1 Nominal planner-first obligation

On nominal planner-first success, a producer MUST provide `tokens`.

It may not omit them and rely on mapper fallback as the steady-state implementation strategy.

### 12.2 Compatibility allowance

On compatibility or migration paths, a producer MAY omit `tokens`, in which case compatibility fallback derivation may be used before public serialization.

---

## 13. Mapper obligations

The response-mapping layer MUST:

* normalize incoming token values,
* preserve valid producer-provided tokens,
* derive compatibility fallback tokens from `text` when needed,
* ensure successful public responses always include canonical `tokens`.

The mapper MUST NOT:

* invent morphology-aware tokenization that the runtime did not provide,
* silently reinterpret producer token boundaries beyond normalization,
* replace valid producer tokens with a different tokenization strategy,
* treat fallback-derived tokens as proof that nominal planner-first runtime supplied them.

### 13.1 Nominal-path boundary rule

On the nominal planner-first path, mapper token derivation is a bug signal, not the intended steady-state source of truth.

The mapper may serialize and normalize.
It must not be the hidden owner of nominal token production.

---

## 14. Language and backend neutrality

This contract is backend-neutral and language-neutral.

That means:

* GF may emit tokens,
* family engines may emit tokens,
* safe mode may emit tokens,
* compatibility shims may emit tokens,
* compatibility fallback splitting may be used in any language when no token list is present.

However, the token contract does **not** require all backends to tokenize with identical granularity.

The shared contract is about:

* field name,
* type,
* normalization,
* order,
* public presence,
* and compatibility fallback behavior.

It is not about enforcing one universal tokenizer across all languages.

---

## 15. Non-goals

The `tokens` field is **not**:

* a lexical-resolution output,
* a slot map,
* a morphology trace,
* a parser input,
* a UD export,
* a search normalization artifact,
* a grapheme segmentation result,
* a sentence segmentation contract.

If the project needs any of those, they require separate contracts.

---

## 16. Recommended debug metadata

When useful, producers or mappers SHOULD expose token provenance in `debug_info`.

Recommended optional keys:

```json id="c8n4u1"
{
  "token_source": "backend",
  "tokenization_mode": "surface_chunks",
  "token_fallback_used": false
}
```

Allowed values for `token_source` include:

* `backend`
* `mapper_fallback`
* `unknown`

Allowed values for `tokenization_mode` may include:

* `surface_chunks`
* `whitespace_split`
* backend-specific documented modes

These keys are recommended, not required.

---

## 17. Examples

## 17.1 Backend-provided multi-word token

```json id="r4m2t8"
{
  "text": "Marie Curie était une physicienne polonaise.",
  "tokens": ["Marie Curie", "était", "une", "physicienne", "polonaise."]
}
```

This is valid.

## 17.2 Backend-provided whitespace-like tokens

```json id="v9y3k6"
{
  "text": "Alan Turing is a British mathematician.",
  "tokens": ["Alan", "Turing", "is", "a", "British", "mathematician."]
}
```

This is valid.

## 17.3 Missing tokens on compatibility path

```json id="j6d1f7"
{
  "text": "Alan Turing is a British mathematician.",
  "tokens": []
}
```

Normalized final tokens on a compatibility path:

```json id="p5h8w2"
["Alan", "Turing", "is", "a", "British", "mathematician."]
```

## 17.4 String token input

Incoming producer value:

```json id="q7l2s4"
{
  "tokens": "Alan Turing"
}
```

Normalized final tokens:

```json id="n3c6b8"
["Alan Turing"]
```

## 17.5 Invalid token payload

Incoming producer value:

```json id="u2x9m5"
{
  "tokens": 123
}
```

Normalized tokens before fallback:

```json id="e1g7r3"
[]
```

If final `text` is available on a compatibility path, fallback derivation then applies.

---

## 18. Migration policy

During migration:

* older code paths MAY omit tokens,
* response mappers MUST still expose canonical public `tokens`,
* compatibility fallback token derivation MUST remain deterministic,
* no backend may invent a second top-level token field.

Avoid drift names such as:

* `words`
* `surface_tokens`
* `token_list`
* `segments`

The canonical field name is:

* `tokens`

### 18.1 Final-state direction

The final-state direction is:

* nominal planner-first runtime produces `tokens` directly,
* mapper fallback survives only as a compatibility edge,
* public responses remain stable throughout the migration.

---

## 19. Acceptance criteria

This contract is considered implemented when:

1. all successful public generation paths expose a top-level `tokens` field,
2. nominal planner-first runtime results expose top-level `tokens` before mapping,
3. producer-provided token sequences normalize deterministically,
4. compatibility paths with empty or invalid token payloads fall back deterministically from final `text`,
5. no path emits empty-string tokens,
6. `tokens` always corresponds to final surface text rather than intermediate structures,
7. token semantics are documented consistently across runtime and public API docs.

---

## 20. Final rule

There is exactly one canonical token field for realized text: `tokens`.

If two generation paths expose different top-level token fields or incompatible token normalization rules, the contract is broken.

If nominal planner-first success omits `tokens` and relies on mapper fallback as the steady-state behavior, the contract is also broken.

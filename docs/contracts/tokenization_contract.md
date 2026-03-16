# Tokenization Contract

Status: normative  
Owner: Runtime / API  
Scope: public and runtime-facing semantics of the `tokens` field carried by `SurfaceResult` and serialized into generation responses

---

## 1. Purpose

This document defines the canonical meaning and normalization rules for the `tokens` field used in SemantiK Architect generation results.

It exists to ensure that:

- renderers and response mappers expose one stable token field,
- clients receive predictable token arrays,
- migration paths do not invent backend-specific token contracts,
- test code can rely on minimal deterministic behavior,
- token transport stays clearly separated from lexical resolution, slot planning, and deeper linguistic annotation.

This contract is intentionally narrow.

It defines how `tokens` are represented and normalized.
It does **not** define a full linguistic tokenization theory.

---

## 2. Scope

This document defines:

- the meaning of `tokens` in `SurfaceResult`,
- the normalization rules for values supplied by backends,
- fallback token derivation behavior when no backend tokens are supplied,
- the guarantees clients may rely on,
- the non-goals of this field.

This document does **not** define:

- lexical segmentation for all languages,
- morphology-aware token decomposition,
- grapheme or subword segmentation,
- UD tokenization,
- sentence splitting,
- clause boundary detection,
- search/index normalization.

---

## 3. Canonical field

`tokens` is the canonical ordered token sequence associated with the final realized surface text.

It appears in runtime results such as `SurfaceResult` and in the public generation success envelope.

Canonical shape:

```json
{
  "tokens": ["Marie Curie", "était", "une", "physicienne", "polonaise"]
}
````

Rules:

* `tokens` MUST be an ordered sequence of strings.
* `tokens` MUST correspond to the final returned surface text.
* `tokens` MUST NOT encode planner slots, lexical bindings, or AST fragments.
* `tokens` MUST remain transport-oriented and lightweight.

---

## 4. Meaning of a token

In this repository, a token is a **surface chunk** of the final text, not a linguistically complete or language-universal tokenization unit.

A token MAY be:

* a whitespace-separated word-like piece,
* a multi-word surface chunk if the backend emits it that way,
* a punctuation-bearing item such as `mathematician.`,
* a larger atomic chunk such as `Marie Curie`.

This is important:

* the runtime does **not** currently force one universal token granularity,
* the backend may provide a higher-level token grouping,
* fallback behavior is simpler and whitespace-driven.

Therefore, clients MUST treat `tokens` as a stable ordered surface sequence, not as a guaranteed morphology-grade tokenization.

---

## 5. Source-of-truth rule

The source-of-truth for `tokens` is:

1. backend-provided `tokens`, if present and valid,
2. otherwise a fallback derivation from the final `text`.

This precedence is mandatory.

If a backend provides valid `tokens`, the mapper MUST preserve them after normalization.
If no valid tokens are provided, the mapper MUST derive them from `text`.

---

## 6. Normalization rules

The current normalization behavior is intentionally simple.

### 6.1 Input value: `null`

If the incoming token value is `null`, normalized `tokens` MUST become an empty sequence.

Example:

```json
{
  "tokens": []
}
```

---

### 6.2 Input value: string

If the incoming token value is a string:

* trim surrounding whitespace,
* if the trimmed string is non-empty, normalize to a single-item sequence,
* if the trimmed string is empty, normalize to an empty sequence.

Examples:

Input:

```json
"Alan Turing"
```

Normalized:

```json
["Alan Turing"]
```

Input:

```json
"   "
```

Normalized:

```json
[]
```

---

### 6.3 Input value: sequence

If the incoming token value is a sequence:

* keep only items that are strings,
* trim each item,
* drop empty strings after trimming,
* preserve original order,
* do not split individual items further,
* do not deduplicate.

Example:

Input:

```json
[" Alan ", "", "Turing", null, " mathematician. "]
```

Normalized:

```json
["Alan", "Turing", "mathematician."]
```

---

### 6.4 Input value: other type

If the incoming token value is any other type, normalized `tokens` MUST become an empty sequence.

---

## 7. Fallback derivation from `text`

If normalized backend tokens are empty and the final surface `text` is available, tokens MUST be derived from `text` by simple whitespace splitting.

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

```text
Alan Turing is a British mathematician.
```

Fallback tokens:

```json
["Alan", "Turing", "is", "a", "British", "mathematician."]
```

This fallback is intentionally minimal and deterministic.

---

## 8. Invariants

The following invariants are mandatory.

### 8.1 Order invariant

`tokens` MUST preserve surface order.

### 8.2 Surface invariant

Joining or reading `tokens` left-to-right must reflect the same realized text sequence as the final `text`, modulo token-boundary granularity and whitespace compression.

### 8.3 Final-text invariant

`tokens` MUST correspond to the final returned surface text, not to:

* an intermediate AST,
* a slot map,
* a lexical binding inventory,
* a partially realized template.

### 8.4 Stability invariant

For a given generation path and identical backend output, token normalization MUST be deterministic.

### 8.5 Non-empty item invariant

A normalized token sequence MUST NOT contain empty strings.

---

## 9. What clients may rely on

Clients MAY rely on the following:

* `tokens` is always ordered,
* each token is a string,
* empty tokens are removed,
* a backend-provided non-empty token sequence is preferred over fallback splitting,
* fallback tokenization is whitespace-based and deterministic,
* punctuation may remain attached to tokens,
* multi-word tokens may occur.

Clients MUST NOT rely on the following unless another contract says so:

* one-token-per-word,
* one-token-per-morpheme,
* one-token-per-grapheme cluster,
* punctuation always split into separate tokens,
* compatibility with UD tokenization,
* stable multilingual word segmentation quality.

---

## 10. Relationship to other contracts

### 10.1 `ConstructionPlan`

`ConstructionPlan` does not own tokenization.
Tokenization belongs only after realization.

### 10.2 `SurfaceResult`

`SurfaceResult` is the runtime object that carries `tokens` alongside:

* `text`
* `lang_code`
* `construction_id`
* `renderer_backend`
* `fallback_used`
* `debug_info`

### 10.3 Public generation response

The public API success envelope may expose `tokens` directly.
When it does, it must preserve the semantics defined here.

### 10.4 Debug info

Debug metadata may describe how tokens were produced, but `tokens` itself remains a first-class top-level field, not a debug-only artifact.

---

## 11. Producer obligations

A renderer or runtime producer that emits `tokens` SHOULD:

* provide tokens already aligned with final text,
* avoid empty token items,
* avoid backend-local placeholder strings,
* keep token order stable,
* emit semantically useful token chunks when possible.

A producer MUST NOT:

* emit planner slot names instead of surface tokens,
* emit hidden backend control strings,
* emit tokens for an earlier unnormalized draft of the sentence.

If a producer cannot provide reliable tokens, it MAY omit them and rely on fallback derivation.

---

## 12. Mapper obligations

The response-mapping layer MUST:

* normalize incoming token values,
* preserve backend-provided tokens when valid,
* derive fallback tokens from `text` when needed,
* keep tokens comparable across planner-first and compatibility paths.

The mapper MUST NOT:

* invent morphology-aware tokenization that the backend did not provide,
* silently reinterpret backend token boundaries beyond normalization,
* replace valid backend tokens with a different tokenization strategy.

---

## 13. Language and backend neutrality

This contract is backend-neutral and language-neutral.

That means:

* GF may emit tokens,
* family engines may emit tokens,
* safe mode may emit tokens,
* compatibility shims may emit tokens,
* fallback splitting may be used in any language when no token list is present.

However, the token contract does **not** require all backends to tokenize with identical granularity.

The shared contract is about:

* field name,
* type,
* normalization,
* order,
* fallback behavior.

It is not about enforcing one universal tokenizer across all languages.

---

## 14. Non-goals

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

## 15. Recommended debug metadata

When useful, producers or mappers SHOULD expose token provenance in `debug_info`.

Recommended optional keys:

```json
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

## 16. Examples

### 16.1 Backend-provided multi-word token

```json
{
  "text": "Marie Curie était une physicienne polonaise.",
  "tokens": ["Marie Curie", "était", "une", "physicienne", "polonaise."]
}
```

This is valid.

---

### 16.2 Backend-provided whitespace-like tokens

```json
{
  "text": "Alan Turing is a British mathematician.",
  "tokens": ["Alan", "Turing", "is", "a", "British", "mathematician."]
}
```

This is valid.

---

### 16.3 Missing tokens, fallback split

```json
{
  "text": "Alan Turing is a British mathematician.",
  "tokens": []
}
```

Normalized final tokens:

```json
["Alan", "Turing", "is", "a", "British", "mathematician."]
```

---

### 16.4 String token input

Incoming backend value:

```json
{
  "tokens": "Alan Turing"
}
```

Normalized final tokens:

```json
["Alan Turing"]
```

---

### 16.5 Invalid token payload

Incoming backend value:

```json
{
  "tokens": 123
}
```

Normalized tokens before fallback:

```json
[]
```

If final `text` is available, fallback derivation then applies.

---

## 17. Migration policy

During migration:

* older code paths MAY omit tokens,
* response mappers MUST still expose normalized `tokens`,
* fallback token derivation MUST remain deterministic,
* no backend may invent a second top-level token field.

Avoid drift names such as:

* `words`
* `surface_tokens`
* `token_list`
* `segments`

The canonical field name is:

* `tokens`

---

## 18. Acceptance criteria

This contract is considered implemented when:

1. all active generation paths expose a top-level `tokens` field,
2. backend-provided token sequences normalize deterministically,
3. empty or invalid token payloads fall back to whitespace splitting from final `text`,
4. no path emits empty-string tokens,
5. `tokens` always corresponds to final surface text rather than intermediate structures,
6. token semantics are documented consistently across runtime and public API docs.

---

## 19. Final rule

There is exactly one canonical token field for realized text: `tokens`.

If two generation paths expose different top-level token fields or incompatible token normalization rules, the contract is broken.



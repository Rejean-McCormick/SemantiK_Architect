
# Frontend API

This document describes the simple frontend API for generating text from semantic frames.

The goal is to provide a small, stable set of entry points for integrators and linguists, while keeping the internal routing, engines, morphology, constructions, discourse, and lexicon modules as implementation details.

> **Current implementation status**
>
> - The `bio` / biography pipeline is fully wired end-to-end (via `router.render_bio` and the family engines).
> - `event` and other frame types are **API-level placeholders**: the types and signatures exist, but there is no concrete engine implementation yet. Calls will typically produce empty text until those engines are added.

---

## 1. Concepts

**Language (`lang`)**  
ISO 639-1 language code, e.g. `"en"`, `"fr"`, `"sw"`.

**Frame (`Frame`)**  
Semantic object representing what should be expressed (e.g. `BioFrame`, `EventFrame`).

**Generation options (`GenerationOptions`)**  
Optional high-level controls (style, length, etc.).

**Generation result (`GenerationResult`)**  
Structured output containing the realized text and metadata.

---

## 2. Quick start

Assuming the package name is `nlg`:

```python
from nlg.api import generate_bio
from semantics.types import BioFrame, Entity

bio = BioFrame(
    main_entity=Entity(name="Douglas Adams", gender="male", human=True),
    primary_profession_lemmas=["writer"],
    nationality_lemmas=["British"],
)

result = generate_bio(lang="en", bio=bio)

print(result.text)       # "Douglas Adams was a British writer."
print(result.sentences)  # ["Douglas Adams was a British writer."]
````

Generic entry point:

```python
from nlg.api import generate
from semantics.types import BioFrame, Entity

bio = BioFrame(
    main_entity=Entity(name="Douglas Adams", gender="male", human=True),
    primary_profession_lemmas=["writer"],
)

result = generate(lang="fr", frame=bio)
print(result.text)
```

> **Note:** At the moment, this generic path is effectively backed by the biography engine via a router adapter. Other frame types (e.g. `EventFrame`) will only start producing meaningful text once their engines are wired.

---

## 3. Public API

All public interfaces for the frontend live in `nlg.api`.

### 3.1 `generate`

General entry point for turning a frame into text.

```python
from nlg.api import generate
from semantics.types import Frame  # Protocol base

def generate(
    lang: str,
    frame: "Frame",
    *,
    options: "GenerationOptions | None" = None,
    debug: bool = False,
) -> "GenerationResult":
    ...
```

**Parameters**

* `lang`: Target language code (e.g. `"en"`, `"fr"`, `"sw"`).
* `frame`: Any supported frame (e.g. `BioFrame`, `EventFrame`).
* `options`: Optional `GenerationOptions`.
* `debug`: If `True`, debug information is included in the result (if available from the engine).

**Returns**

* `GenerationResult`

**Example**

```python
from nlg.api import generate, GenerationOptions
from semantics.types import BioFrame, Entity

bio = BioFrame(
    main_entity=Entity(name="Douglas Adams", gender="male", human=True),
    primary_profession_lemmas=["writer"],
)

options = GenerationOptions(
    register="neutral",
    max_sentences=2,
)

result = generate(
    lang="sw",
    frame=bio,
    options=options,
    debug=True,
)

print(result.text)
print(result.debug_info)  # engine, constructions, etc. (if enabled)
```

---

### 3.2 `generate_bio`

Convenience wrapper for biography frames.

```python
from nlg.api import generate_bio
from semantics.types import BioFrame

def generate_bio(
    lang: str,
    bio: "BioFrame",
    *,
    options: GenerationOptions | None = None,
    debug: bool = False,
) -> GenerationResult:
    ...
```

Behaves like:

```python
generate(lang=lang, frame=bio, options=options, debug=debug)
```

> **Status:** Fully implemented and backed by the family-specific biography engines via `router.render_bio`.

---

### 3.3 `generate_event`

Convenience wrapper for event frames.

```python
from nlg.api import generate_event
from semantics.types import EventFrame

def generate_event(
    lang: str,
    event: "EventFrame",
    *,
    options: GenerationOptions | None = None,
    debug: bool = False,
) -> GenerationResult:
    ...
```

Behaves like:

```python
generate(lang=lang, frame=event, options=options, debug=debug)
```

> **Status:** The function exists and routes through `generate`, but there is currently **no concrete event engine**. Until the event pipeline is implemented, you should expect empty strings / placeholder behavior for `EventFrame` inputs.

---

### 3.4 `NLGSession`

Optional stateful interface for long-running processes and services.

```python
from nlg.api import NLGSession
from semantics.types import Frame

class NLGSession:
    def __init__(self, *, preload_langs: list[str] | None = None):
        """
        Create a session.

        preload_langs:
            Optional list of language codes to initialize in advance.
        """
        ...

    def generate(
        self,
        lang: str,
        frame: Frame,
        *,
        options: "GenerationOptions | None" = None,
        debug: bool = False,
    ) -> "GenerationResult":
        ...
```

Under the hood, `NLGSession` maintains an internal cache of per-language engines; if the router does not expose a dedicated engine factory, it falls back to a small adapter that delegates biography generation to `router.render_bio`.

**Usage**

```python
from nlg.api import NLGSession
from semantics.types import BioFrame, Entity

session = NLGSession(preload_langs=["en", "fr"])

bio = BioFrame(
    main_entity=Entity(name="Douglas Adams", gender="male", human=True),
    primary_profession_lemmas=["writer"],
)

result_en = session.generate("en", bio)
result_fr = session.generate("fr", bio)
```

---

## 4. Data models

The concrete semantic types live under `semantics.types` and related modules. The snippets below illustrate the expected shape.

### 4.1 Frames

Frames implement a common protocol:

```python
from typing import Protocol

class Frame(Protocol):
    frame_type: str  # e.g. "bio", "event"
```

#### Example: `BioFrame`

```python
from dataclasses import dataclass, field
from semantics.types import Frame, Entity

@dataclass
class BioFrame(Frame):
    frame_type: str = "bio"
    main_entity: Entity
    primary_profession_lemmas: list[str] = field(default_factory=list)
    nationality_lemmas: list[str] = field(default_factory=list)
    extra: dict | None = None   # optional extra info
```

#### Example: `EventFrame`

```python
from dataclasses import dataclass
from semantics.types import Frame

@dataclass
class EventFrame(Frame):
    frame_type: str = "event"
    # Event-specific fields (participants, time, location, etc.)
```

Concrete field sets are defined in `semantics.types` / `semantics.normalization` and should be treated as the source of truth.

---

### 4.2 `GenerationOptions`

High-level configuration for generation.

```python
from dataclasses import dataclass

@dataclass
class GenerationOptions:
    register: str | None = None        # "neutral", "formal", "informal"
    max_sentences: int | None = None   # maximum number of sentences
    discourse_mode: str | None = None  # e.g. "intro", "summary"
    seed: int | None = None            # reserved for future stochastic behavior
```

**Example**

```python
from nlg.api import generate_bio, GenerationOptions

options = GenerationOptions(
    register="neutral",
    max_sentences=1,
)

result = generate_bio("en", bio, options=options)
print(result.text)
```

---

### 4.3 `GenerationResult`

Standard output type for all generation calls.

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class GenerationResult:
    text: str                          # final realized text
    sentences: list[str]               # sentence-level split
    lang: str                          # language code used
    frame: "Frame"                     # original frame
    debug_info: dict[str, Any] | None = None
```

**Example**

```python
result = generate_bio("en", bio)

print(result.text)
# "Douglas Adams was a British writer."

print(result.sentences)
# ["Douglas Adams was a British writer."]

print(result.lang)
# "en"
```

If `debug=True` was passed to the generating function, `debug_info` may contain implementation-specific details such as engine identifiers, selected constructions, or intermediate forms (when the underlying engine chooses to expose them).

---

## 5. CLI

A small CLI is provided for quick experiments and linguistic work. It lives in `nlg/cli_frontend.py` and exposes the `nlg-cli` entry point (via your packaging / tooling).

> **Current limitation:** The CLI only has a fully wired path for `frame_type="bio"`. Other frame types are accepted syntactically but will not yet produce meaningful output until their engines are implemented.

### 5.1 Command: `nlg-cli generate`

General form:

```bash
nlg-cli generate \
  --lang <LANG> \
  --frame-type <FRAME_TYPE> \
  --input <PATH_TO_JSON> \
  [--max-sentences N] \
  [--register neutral|formal|informal] \
  [--discourse-mode MODE] \
  [--debug]
```

**Arguments**

* `--lang`
  Target language code, e.g. `en`, `fr`, `sw`.

* `--frame-type`
  Frame type, e.g. `bio`, `event`. If omitted, the JSON must contain `frame_type`.

* `--input`
  Path to a JSON file describing the frame. If omitted or `-`, input is read from stdin.

* `--max-sentences` (optional)
  Passed through as `GenerationOptions.max_sentences`.

* `--register` (optional)
  Passed through as `GenerationOptions.register`.

* `--discourse-mode` (optional)
  Passed through as `GenerationOptions.discourse_mode`.

* `--debug` (optional)
  If set, debug information is printed in addition to the main text (when available).

**Example frame JSON (`frame.json`)**

```json
{
  "frame_type": "bio",
  "name": "Douglas Adams",
  "gender": "male",
  "profession_lemma": "writer",
  "nationality_lemma": "British"
}
```

(This is the normalized JSON shape expected by `semantics.normalization.normalize_bio_semantics`, which the CLI uses for `frame_type == "bio"`.)

**Example command**

```bash
nlg-cli generate \
  --lang en \
  --frame-type bio \
  --input frame.json
```

**Output**

* Main text is printed to standard output.
* If `--debug` is provided, additional debug information may be printed or logged.

---

## 6. Integration guidelines

* Use `nlg.api.generate` or `NLGSession.generate` as the only entry points for frontend or service code.
* Construct frames using the models in `semantics.types` (e.g. `BioFrame`, `EventFrame`) or via your own JSON → frame conversion based on those types.
* Prefer `GenerationOptions` to control output style and length; low-level morphological or discourse behavior is handled internally by engines and the router.
* Treat `debug_info` as optional and implementation-specific; do not rely on it for core functionality.
* For now, treat `EventFrame` and other non-bio frames as **experimental** until their engines are wired. The biography pipeline is the reference implementation.

This frontend API is intentionally thin: it presents a simple, stable surface over a complex multilingual NLG stack while keeping internal modules flexible and evolvable.


# Frontend API

This document describes the simple frontend API for generating text from semantic frames.

The goal is to provide a small, stable set of entry points for integrators and linguists, while keeping the internal routing, engines, morphology, constructions, discourse, and lexicon modules as implementation details. 

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
from nlg.semantics import BioFrame

bio = BioFrame(
    person={"qid": "Q42"},
    occupations=[{"lemma": "writer"}],
    nationalities=[{"lemma": "British"}],
)

result = generate_bio(lang="en", bio=bio)

print(result.text)       # "Douglas Adams was a British writer."
print(result.sentences)  # ["Douglas Adams was a British writer."]
```

Generic entry point:

```python
from nlg.api import generate
from nlg.semantics import BioFrame

bio = BioFrame(
    person={"qid": "Q42"},
    occupations=[{"lemma": "writer"}],
)

result = generate(lang="fr", frame=bio)
print(result.text)
```

---

## 3. Public API

All public interfaces for the frontend live in `nlg.api`.

### 3.1 `generate`

General entry point for turning a frame into text.

```python
from nlg.api import generate
from nlg.semantics import Frame

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
* `debug`: If `True`, debug information is included in the result.

**Returns**

* `GenerationResult`

**Example**

```python
from nlg.api import generate, GenerationOptions
from nlg.semantics import BioFrame

bio = BioFrame(
    person={"qid": "Q42"},
    occupations=[{"lemma": "writer"}],
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
from nlg.semantics import BioFrame

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

---

### 3.3 `generate_event`

Convenience wrapper for event frames.

```python
from nlg.api import generate_event
from nlg.semantics import EventFrame

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

---

### 3.4 `NLGSession`

Optional stateful interface for long-running processes and services.

```python
from nlg.api import NLGSession
from nlg.semantics import Frame

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

**Usage**

```python
from nlg.api import NLGSession
from nlg.semantics import BioFrame

session = NLGSession(preload_langs=["en", "fr"])

bio = BioFrame(
    person={"qid": "Q42"},
    occupations=[{"lemma": "writer"}],
)

result_en = session.generate("en", bio)
result_fr = session.generate("fr", bio)
```

---

## 4. Data models

### 4.1 Frames

Frames live in `nlg.semantics`. All frames implement a common interface:

```python
from typing import Protocol

class Frame(Protocol):
    frame_type: str  # e.g. "bio", "event"
```

#### Example: `BioFrame`

```python
from dataclasses import dataclass, field
from nlg.semantics import Frame

@dataclass
class BioFrame(Frame):
    frame_type: str = "bio"
    person: dict
    birth_event: dict | None = None
    death_event: dict | None = None
    occupations: list[dict] = field(default_factory=list)
    nationalities: list[dict] = field(default_factory=list)
    # Additional biography-specific fields as needed
```

#### Example: `EventFrame`

```python
from dataclasses import dataclass
from nlg.semantics import Frame

@dataclass
class EventFrame(Frame):
    frame_type: str = "event"
    # Event-specific fields (participants, time, location, etc.)
```

Concrete field sets are defined in `nlg.semantics` and should be treated as the source of truth.

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

If `debug=True` was passed to the generating function, `debug_info` may contain implementation-specific details such as engine identifiers, selected constructions, or intermediate forms.

---

## 5. CLI

A small CLI is provided for quick experiments and linguistic work.

### 5.1 Command: `nlg-cli generate`

General form:

```bash
nlg-cli generate \
  --lang <LANG> \
  --frame-type <FRAME_TYPE> \
  --input <PATH_TO_JSON> \
  [--max-sentences N] \
  [--debug]
```

**Arguments**

* `--lang`
  Target language code, e.g. `en`, `fr`, `sw`.

* `--frame-type`
  Frame type, e.g. `bio`, `event`. Determines how the JSON is parsed.

* `--input`
  Path to a JSON file describing the frame.

* `--max-sentences` (optional)
  Passed through as `GenerationOptions.max_sentences`.

* `--debug` (optional)
  If set, debug information is printed in addition to the main text.

**Example frame JSON (`frame.json`)**

```json
{
  "frame_type": "bio",
  "person": { "qid": "Q42" },
  "occupations": [{ "lemma": "writer" }],
  "nationalities": [{ "lemma": "British" }]
}
```

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
* Construct frames using the models in `nlg.semantics` (e.g. `BioFrame`, `EventFrame`).
* Prefer `GenerationOptions` to control output style and length; low-level morphological or discourse behavior is handled internally.
* Treat `debug_info` as optional and implementation-specific; do not rely on it for core functionality.

This frontend API is intentionally thin: it presents a simple, stable surface over a complex multilingual NLG stack while keeping internal modules flexible and evolvable.

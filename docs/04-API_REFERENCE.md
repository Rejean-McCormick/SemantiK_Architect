# 🔌 API Reference & Semantic Frames

**Abstract Wiki Architect v2.0**

## 1. Overview

The Abstract Wiki Architect exposes a **Hybrid Natural Language Generation (NLG) Engine** via a RESTful API.
It supports two primary input modes:

1. **Semantic Frames:** Simple, flat JSON objects (Internal Format).
2. **Ninai Protocol:** Recursive JSON Object Trees (Abstract Wikipedia Standard).

The engine is **deterministic**: the same input + configuration will always produce the same output, unless "Micro-Planning" (Style Injection) is enabled.

* **Base URL:** `http://localhost:8000/api/v1`
* **Encoding:** UTF-8

---

## 2. Authentication

By default, the API is open for local development (`APP_ENV=development`).

In production, if `API_SECRET` is set in the environment variables, you must include it in the headers.

| Header | Value | Required |
| --- | --- | --- |
| `X-API-Key` | `<Your-API-Secret>` | Yes (Production only) |

---

## 3. Endpoints

### Generate Text

**`POST /generate`**

Converts an abstract intent into natural language.

**Query Parameters**

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `lang` | `string` | **Yes** | The 3-letter ISO 639-3 code (e.g., `eng`, `fra`, `zul`). |
| `style` | `string` | No | `simple` (default) or `formal`. Triggers Micro-Planning. |

**Headers (v2.0 Features)**

| Header | Value | Description |
| --- | --- | --- |
| `Content-Type` | `application/json` | Required for all requests. |
| `Accept` | `text/plain` | **Default.** Returns a flat string. |
| `Accept` | `text/x-conllu` | **UD Export.** Returns CoNLL-U dependency tags. |
| `X-Session-ID` | `<UUID>` | **Context.** Enables multi-sentence pronominalization. |

---

## 4. Input Mode A: Semantic Frames (Internal)

The body must be a single flat JSON object. The `frame_type` field determines the logic.

### A. Bio Frame (`bio`)

Used for introductory biographical sentences.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `frame_type` | `str` | **Yes** | Must be `"bio"`. |
| `name` | `str` | **Yes** | The subject's proper name (e.g., "Alan Turing"). |
| `profession` | `str` | **Yes** | Lookup key in `people.json` (e.g., "computer_scientist"). |
| `nationality` | `str` | No | Lookup key in `geography.json` (e.g., "british"). |
| `gender` | `str` | No | `"m"`, `"f"`, or `"n"`. Critical for inflection. |

**Example:**

```json
{
  "frame_type": "bio",
  "name": "Shaka",
  "profession": "warrior",
  "nationality": "zulu",
  "gender": "m"
}

```

### B. Event Frame (`event`)

Used for temporal events.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `frame_type` | `str` | **Yes** | Must be `"event"`. |
| `event_type` | `str` | **Yes** | `"birth"`, `"death"`, `"award"`, `"discovery"`. |
| `subject` | `str` | **Yes** | The entity experiencing the event. |
| `date` | `str` | No | Year or ISO date string. |

---

## 5. Input Mode B: Ninai Protocol (Standard)

The API natively supports the **Ninai JSON Object Model** used by Abstract Wikipedia. The recursive structure is automatically flattened by the `NinaiAdapter`.

**Schema:**
The root object must define a `function` key matching the Ninai constructor registry.

**Example Request:**

```json
{
  "function": "ninai.constructors.Statement",
  "args": [
    { "function": "ninai.types.Bio" },
    { 
      "function": "ninai.constructors.List", 
      "args": ["physicist", "chemist"] 
    },
    { "function": "ninai.constructors.Entity", "args": ["Q42"] }
  ]
}

```

---

## 6. Output Formats

### Standard Text (`Accept: text/plain`)

```json
{
  "result": "Shaka est un guerrier zoulou.",
  "meta": {
    "lang": "fra",
    "engine": "WikiFra",
    "latency_ms": 12
  }
}

```

### Universal Dependencies (`Accept: text/x-conllu`)

Returns the CoNLL-U representation for evaluation against treebanks.

```json
{
  "result": "# text = Shaka est un guerrier zoulou.\n1 Shaka _ PROPN _ _ 3 nsubj _ _\n...",
  "meta": {
    "lang": "fra",
    "exporter": "UDMapping"
  }
}

```

---

## 7. Error Handling

| Status | Error Type | Cause |
| --- | --- | --- |
| **400** | `Bad Request` | Malformed JSON or Ninai parse error. |
| **404** | `Not Found` | The requested `lang` is not in the `AbstractWiki.pgf` binary. |
| **422** | `Unprocessable` | A specific word is missing from the Lexicon. |
| **424** | `Failed Dependency` | UD Exporter failed to map a function (check `UD_MAP`). |
| **500** | `Server Error` | Internal engine failure. |

---

## 8. Integration Guide (Python Client)

```python
import requests
import uuid

API_URL = "http://localhost:8000/api/v1/generate"
SESSION_ID = str(uuid.uuid4())

def generate_sentence(frame: dict, lang: str = "eng") -> str:
    """
    Generates text with context awareness.
    """
    headers = {
        "Content-Type": "application/json",
        "X-Session-ID": SESSION_ID  # Enables 'He/She' logic
    }
    
    response = requests.post(
        API_URL, 
        params={"lang": lang}, 
        json=frame,
        headers=headers
    )
    response.raise_for_status()
    return response.json()["result"]

```
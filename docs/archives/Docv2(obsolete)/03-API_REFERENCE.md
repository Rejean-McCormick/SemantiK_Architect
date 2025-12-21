# API Reference & Semantic Frames

## 1\. Overview

The Abstract Wiki Architect API accepts a **Semantic Frame** (a JSON object representing meaning) and returns natural language text in the requested target language. The system serves as a deterministic NLG engine, converting abstract intents into readable sentences based on the linguistic rules defined in the backend architecture.

**Base URL:** `POST /api/v1/generate`

## 2\. Request Format

  * **Method:** `POST`
  * **Header:** `Content-Type: application/json`
  * **Query Parameter:** `lang` (Required, e.g., `en`, `fr`, `tr`, `sw`). [cite_start]The target language code must match a configuration in `data/morphology_configs/` or `data/romance/`, etc. [cite: 692, 706, 772]
  * **Body:** A single Semantic Frame object.

### Generic Request Example

```bash
curl -X POST "http://localhost:8000/api/v1/generate?lang=fr" \
     -H "Content-Type: application/json" \
     -d '{
           "frame_type": "bio",
           "name": "Marie Curie",
           "profession": "physicist",
           "nationality": "polish"
         }'
```

## 3\. Semantic Frame Schemas

The system logic (Renderer) dispatches processing based on the `frame_type` field. Below are the supported schemas.

### A. Bio Frame (`bio`)

Used for introductory biographical sentences. This frame triggers the `BiographicalRenderer` logic, which handles profession agreement, nationality inflection, and article selection.

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `frame_type` | String | Yes | Must be `"bio"`. |
| `name` | String | Yes | The subject's name (e.g., "Alan Turing"). |
| `profession` | String | Yes | [cite_start]Key identifying a profession in the `people.json` lexicon (e.g., "computer\_scientist"). [cite: 313, 447, 494] |
| `nationality` | String | No | [cite_start]Key identifying a nationality in the `geography.json` lexicon (e.g., "british"). [cite: 265, 456, 499] |
| `gender` | String | No | `"m"`, `"f"`, or `"n"`. [cite_start]Used for morphological agreement if the lexicon entry is ambiguous or missing. [cite: 275, 414, 587] |

**Example:**

```json
{
  "frame_type": "bio",
  "name": "Grace Hopper",
  "profession": "computer_scientist",
  "nationality": "american",
  "gender": "f"
}
```

### B. Relational Frame (`relational`)

Used to express a direct relationship between two entities. This is useful for describing family ties, academic advisors, or political successors.

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `frame_type` | String | Yes | Must be `"relational"`. |
| `subject` | String | Yes | The agent/subject of the sentence. |
| `relation` | String | Yes | The predicate key (e.g., "spouse\_of", "advisor\_to", "child\_of"). |
| `object` | String | Yes | The patient/object or target of the relation. |

**Example:**

```json
{
  "frame_type": "relational",
  "subject": "Pierre Curie",
  "relation": "spouse_of",
  "object": "Marie Curie"
}
```

### C. Event Frame (`event`)

Used for temporal events like birth, death, awards, or discoveries.

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `frame_type` | String | Yes | Must be `"event"`. |
| `event_type` | String | Yes | The type of event: `"birth"`, `"death"`, `"award"`, `"discovery"`. |
| `subject` | String | Yes | The entity experiencing the event. |
| `date` | String | No | ISO date or year (e.g., "1934"). |
| `location` | String | No | [cite_start]City or Country key found in the lexicon (e.g., "Paris", "Germany"). [cite: 301, 599] |

**Example:**

```json
{
  "frame_type": "event",
  "event_type": "birth",
  "subject": "Albert Einstein",
  "date": "1879",
  "location": "germany"
}
```

## 4\. Response Format

### Success (200 OK)

The API returns a JSON object containing the generated text and metadata about the generation process.

```json
{
  "result": "Grace Hopper est une informaticienne américaine.",
  "meta": {
    "engine": "RomanceRenderer",
    "lang": "fr",
    "latency_ms": 12
  }
}
```

### Error Handling

| Status Code | Error Type | Description |
| :--- | :--- | :--- |
| **400** | Bad Request | Missing `frame_type` or required fields in the request body. |
| **404** | Not Found | [cite_start]The requested `lang` is not supported in the configuration (e.g., `morphology_configs` is missing). [cite: 62, 706] |
| **422** | Unprocessable Entity | A specific lexicon entry (profession, nationality) could not be found in the loaded dictionary files (e.g., "spaceman" not in `people.json`). |
| **500** | Internal Server Error | An unexpected failure in the morphology engine (e.g., missing matrix configuration for a requested language family). |

## 5\. Integration Patterns

### Frontend Integration

When building a frontend for this API, it is recommended to:

1.  **Validate Input:** Ensure `frame_type` matches one of the supported schemas before sending.
2.  **Handle Fallbacks:** If the API returns a 422 (missing word), the frontend should fallback to displaying the raw data or a generic placeholder (e.g., "Grace Hopper (computer\_scientist)").
3.  **Language Selection:** Query the supported languages endpoint (if available) or hardcode the list based on the `data/` directory structure.

### Python Client Example

```python
import requests

def generate_bio(name, profession, nationality, lang="en"):
    url = "http://localhost:8000/api/v1/generate"
    payload = {
        "frame_type": "bio",
        "name": name,
        "profession": profession,
        "nationality": nationality
    }
    response = requests.post(url, params={"lang": lang}, json=payload)
    return response.json()

# Usage
print(generate_bio("Marie Curie", "physicist", "polish", lang="fr"))

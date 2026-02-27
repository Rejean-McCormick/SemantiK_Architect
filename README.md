

# Semantik Architect (V2)

**Industrial-grade NLG system for Abstract Wikipedia and Wikifunctions.**

Semantik Architect is a family-based, data-driven Natural Language Generation (NLG) toolkit. Instead of writing one renderer per language (“300 scripts for 300 languages”), this project builds:

* **Shared Family Engines:** ~15 universal engines (Romance, Slavic, Bantu, etc.) implemented as Adapters.
* **Configuration Cards:** Hundreds of per-language JSON configurations (grammar matrices).
* **Hexagonal Core:** A pure Python domain layer containing semantic frames and cross-linguistic constructions.
* **Lexicon Subsystem:** A robust persistence layer with bridges to Wikidata.
* **Background Worker:** An async system for compiling and onboarding languages.

The goal is to provide a professional, testable architecture for rule-based NLG, aligned with Abstract Wikipedia but usable as a standalone API service.

---

## 🏛️ Architecture Overview (Hexagonal)

The system has moved from a flat script structure to a **Modular Monolith** organized by technical capability.

```text
app/
├── core/                   # 🧠 THE BRAIN (Pure Python, No Infrastructure)
│   ├── domain/             # Models (Frames, Sentences) & Events
│   ├── ports/              # Interfaces (IMessageBroker, IGrammarEngine)
│   └── use_cases/          # Business Logic (GenerateText, BuildLanguage)
│
├── adapters/               # 🔌 THE PLUGS (Infrastructure)
│   ├── api/                # FastAPI (Driving Adapter)
│   ├── worker/             # Background Worker (Driving Adapter)
│   ├── messaging/          # Redis Pub/Sub (Driven Adapter)
│   ├── persistence/        # FileSystem & Wikidata (Driven Adapters)
│   └── engines/            # Grammar Engines (GF & Python Wrappers)
│
└── shared/                 # 🛠️ SHARED UTILITIES
    ├── container.py        # Dependency Injection
    └── config.py           # Settings (Pydantic)

```

### 💡 Intuition: Consoles, Cartridges, and the Router

Think of each sentence as a game you want to play.

* **Old way:** Build one console per game (one monolithic renderer per language).
* **Semantik Architect:**
1. **The Console (Core/Engine):** Universal logic (Romance, Slavic, etc.).
2. **The Cartridge (Config/Lexicon):** Per-language JSON files loaded dynamically.
3. **The Router (API/Use Case):** Plugs the right cartridge into the console based on the request.



**Example (Romance Family):**

* The **Romance Engine (Adapter)** knows how to feminize nouns and apply plural rules generically.
* The **Italian Cartridge** (`data/lexicon/it.json`) tells it: `"-o" -> "-a"` for feminine.
* The **Spanish Cartridge** tweaks only what differs: Indefinite articles differ, but pluralization is similar.

---

## 🧩 Components

### 1. Semantic Frames (The Input)

Located in `app/core/domain/models.py`. These are the abstract representations of intent, independent of language.

* **Entity Frames:** People, Organizations, Places.
* **Event Frames:** Actions with participants and time.
* **Relational Frames:** Definitions, attributes, measurements.

**Example Payload:**

```json
{
  "frame_type": "bio",
  "subject": { "name": "Marie Curie", "qid": "Q7186" },
  "properties": { "profession": "physicist", "nationality": "polish" }
}

```

### 2. Constructions (Sentence Patterns)

Located in `app/core/domain/constructions/` (Conceptually). These are family-agnostic patterns that orchestrate the generation:

* `copula_equative`: "X is Y"
* `transitive_event`: "X did Y to Z"
* `passive_event`: "Z was done by X"

### 3. Grammar Engines (The Generators)

Located in `app/adapters/engines/`. We support multiple backend engines:

* **GF (Grammatical Framework):** For high-precision, resource-heavy generation (Full Strategy).
* **Python/Jinja (Simple):** For rapid prototyping and pidgin generation (Fast Strategy).

### 4. Lexicon Subsystem

Located in `app/adapters/persistence/`.

* **FileSystemRepo:** Loads local JSON lexicons.
* **WikidataAdapter:** Fetches live data from SPARQL endpoints to hydrate missing lexemes.

---

## 🚀 Quick Start (Docker)

The easiest way to run the full stack (API + Worker + Redis) is via Docker Compose.

### 1. Start the System

```bash
docker-compose up --build

```

* **Unified UI:** `http://localhost:4000/semantik_architect/`
* **API Docs:** `http://localhost:8000/docs`
* **Redis:** `localhost:6379`

### 2. Verify Health

```bash
curl http://localhost:8000/api/v1/health/ready
# {"broker":"up", "storage":"up", "engine":"up"}

```

---

## 💻 API Usage

Instead of calling Python functions directly, you now interact via REST API.

### 1. Generate Text (Synchronous)

**`POST /api/v1/generate/{lang_code}`**

```bash
curl -X POST http://localhost:8000/api/v1/generate/fra \
  -H "x-api-key: secret" \
  -H "Content-Type: application/json" \
  -d '{
    "frame_type": "bio",
    "subject": {"name": "Marie Curie"},
    "properties": {"profession": "physicist", "nationality": "polish"}
  }'

```

> **Response:** *Marie Curie est une physicienne polonaise.*

### 2. Onboard New Language (Async Saga)

**`POST /api/v1/languages/`**

Triggers the Onboarding Saga which:

1. Registers the language in the system.
2. Scaffolds initial JSON configuration files.
3. Dispatches a build event to the Background Worker.

```bash
curl -X POST http://localhost:8000/api/v1/languages/ \
  -H "x-api-key: secret" \
  -H "Content-Type: application/json" \
  -d '{"code": "zul", "name": "Zulu", "family": "Bantu"}'

```

---

## 🛠️ Development (Local)

If you are developing core logic without Docker:

```bash
# 1. Install
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,api]"

# 2. Run API (Shim)
python -m app.main

# 3. Run Worker (Requires Redis)
# Use 'arq' CLI to watch for file changes
arq app.workers.worker.WorkerSettings --watch app

```

---

## 🧪 Testing

We use `pytest` with a strict separation of Unit and Integration tests.

```bash
# Run all tests
pytest

# Run only Core Unit tests (Fast, Mocked Infrastructure)
pytest tests/core

# Run Integration tests (Requires Redis/Internet)
pytest tests/integration

```

---

## 🗺️ Mapping to Wikifunctions

The system includes utilities to mock Wikifunctions Z-Objects, facilitating future export.

### Z-Object Mock

Located in `app/shared/wikifunctions_mock.py`. Wraps Python dictionaries in Z-Object structures (Z6 for strings, Z9 for references) to simulate how the Abstract Wikipedia renderer calls functions.

### Config Extraction

You can extract the internal JSON configurations to use as Z-Data on Wikifunctions:

```bash
python -m app.utils.config_extractor it

```

*Outputs the Italian configuration JSON compatible with Z-Function inputs.*

---

## 🌐 Related Projects & Ecosystem

Semantik Architect is designed to work in concert with a suite of tools for information deconstruction and secure exchange.

* **SenTient:** A powerful integration of Falcon 2.0, OpenTapioca, and OpenRefine. It deconstructs information to improve system circulation and acts as the intelligence layer alongside Architect.
* **Orgo:** A closed-loop, secure application for resilience. Architect and SenTient operate within Orgo to ensure robust internal operations. (Note: Orgo is an independent project with distinct organizational affiliations outside the scope of the Wikimedia Foundation).
* **Konnaxion:** The open counterpart to Orgo, focused on constructive, philanthropic exchanges solidly anchored in ethical principles.
* **The Senior Architect's Codex:** Advanced Jupyter notebooks and utilities for AI empowerment.
* **Core Modules:** Ariane (Navigation) and Ame-Artificielle.



---

## 🔮 Roadmap & Status

**Current Status (V2.1 - Dec 2025):**

* ✅ **Hexagonal Architecture:** Full separation of concerns.
* ✅ **Async Worker:** Long-running compilations no longer block the API.
* ✅ **Unified API:** One canonical entrypoint (`/api/v1`) for all clients.
* ✅ **Biography Generation:** BioFrame supported across Romance and Germanic families.
* ✅ **Dockerized:** One-command deploy.

**Upcoming:**

* [ ] **LLM Refiner:** Post-processing step to smooth rule-based output.
* [ ] **Web UI:** Next.js frontend for managing languages (In Progress).
* [ ] **Observability:** OpenTelemetry tracing.

---

### 🔗 Links

* **Repository:** [github.com/Rejean-McCormick/abstract-wiki-architect](https://www.google.com/search?q=https://github.com/Rejean-McCormick/abstract-wiki-architect)
* **Wiki:** Architecture deep dives and frame definitions.
* **Meta-Wiki:** Abstract Wikipedia Tools Hub
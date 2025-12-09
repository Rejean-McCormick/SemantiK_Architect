
# Abstract Wiki Architect: Global Architecture

## 1\. System Overview

Abstract Wiki Architect is a **Rule-Based Natural Language Generation (NLG) Engine**. Unlike statistical models (LLMs) that predict the next token based on probability, this system constructs sentences deterministically using linguistic rules and structured data. It is designed to generate high-quality, verifiable biographical and encyclopedic sentences across diverse language families (Indo-European, Uralic, Bantu, Altaic, etc.).

[Image of Natural Language Generation Architecture Diagram]

## 2\. Core Philosophy: Separation of Concerns

The architecture is strictly layered to ensure modularity. Changes in the vocabulary (Lexicon) do not break the grammar rules (Matrix), and changes in grammar do not break the sentence templates (Renderer).

### Layer A: The Lexicon (Data)

  * **Role:** The "Vocabulary." Stores words (lemmas) and their inherent properties (gender, stems, irregular forms, QIDs).
  * **Strategy:** **Usage-Based Sharding**. Data is organized by domain rather than monolithic files to optimize loading and relevance.
      * **Core:** High-frequency functional words (copulas, pronouns, articles).
      * **People:** Biographical terms (professions, titles, relationships).
      * **Science/Geo:** Domain-specific terminology.
  * [cite_start]**Source:** Wikidata is the upstream "raw material" (referenced via Q-IDs); local JSON files are the downstream runtime optimization[cite: 38].

### Layer B: The Grammar Matrix (Logic)

  * **Role:** The "Rules." Defines how words change form (Morphology) and how they relate to one another (Syntax).
  * **Mechanism:** Shared configurations (Matrices) per language family avoid code duplication.
      * [cite_start]**Romance Matrix:** Handles gender agreement, pluralization, and article selection (e.g., *le* vs *la* vs *l'*)[cite: 62, 69].
      * [cite_start]**Germanic Matrix:** Handles strong/weak verb conjugation (e.g., *sing* $\to$ *sang*) and shifting vowel stems[cite: 706].
      * [cite_start]**Slavic Matrix:** Handles complex case declension (Nominative vs. Instrumental) required for predicates (e.g., Polish: *jest fizykiem*)[cite: 795].
      * [cite_start]**Agglutinative Matrix:** Handles vowel harmony (Front vs. Back vowels) and suffix stacking for languages like Turkish and Hungarian[cite: 692].
      * [cite_start]**Japonic/Polysynthetic:** Handles particle attachment (e.g., *wa*, *no*) and deep suffixation logic[cite: 118, 802].

### Layer C: The Renderer (Presentation)

  * **Role:** The "Assembly." Takes an abstract intent (Data) and combines it with the Lexicon and Grammar Matrix to produce a final string.
  * **Templates:** Logic-agnostic patterns such as `{name} {copula} {profession} {nationality}.`
  * **Output Example:**
      * *Input:* `Marie Curie | Physicist | Polish`
      * *French Output:* "Marie Curie est une physicienne polonaise."
      * *German Output:* "Marie Curie ist eine polnische Physikerin."

## 3\. Data Flow

The generation pipeline follows a strict four-step process:

1.  **Input (Abstract Intent):**
    The system receives a semantic frame (JSON) describing *who* and *what* to describe.

    ```json
    { "name": "Shaka", "profession": "warrior", "nationality": "zulu" }
    ```

2.  **Lookup (Lexicon Layer):**
    The loader fetches the relevant terms from `data/lexicon/{lang}/{domain}.json`.

      * *Fetch:* "warrior" $\to$ Target Lemma
      * *Fetch:* "zulu" $\to$ Target Adjective

3.  **Inflection (Morphology Engine):**
    The engine applies rules from `data/morphology_configs/`.

      * *Check:* Does the profession need to agree with the subject's gender?
      * *Check:* Does the adjective require a specific case or prefix?
      * *Apply:* Modify the lemma (e.g., add suffix `-a`, change vowel `o` $\to$ `u`).

4.  **Realization (Renderer):**
    The inflected words are slotted into the language-specific sentence template.

      * *Finalize:* Capitalization, punctuation, and phonological smoothing (e.g., elision).

## 4\. Directory Structure Map

| Directory | Purpose | Examples |
| :--- | :--- | :--- |
| **`data/lexicon/`** | Stores words split by language and domain. | `en/core.json`, `fr/people.json` |
| **`data/morphology_configs/`** | Logic for language families. | `romance_grammar_matrix.json`, `slavic_matrix.json` |
| **`data/romance/`, `data/germanic/`** | Language-specific connector configs. | `fr.json`, `de.json`, `es.json` |
| **`data/raw_wikidata/`** | Staging area for raw data dumps. | `*.json.gz` (Ignored by git) |

## 5\. Supported Language Families

  * **Indo-European:** Germanic (En, De, Nl, Sv...), Romance (Fr, Es, It, Pt, Ro), Slavic (Ru, Pl, Cs), Celtic (Cy), Indo-Aryan (Hi, Bn), Iranic (Fa).
  * **Altaic / Agglutinative:** Turkic (Tr), Japonic (Ja), Koreanic (Ko).
  * **Uralic:** Finno-Ugric (Fi, Hu).
  * **Austronesian:** Malayo-Polynesian (Id).
  * **Bantu:** Swahili (Sw).
  * **Inuit-Yupik-Unangan:** Inuktitut (Iu).
  * **Dravidian:** Tamil (Ta), Malayalam (Ml).
  * **Semitic:** Arabic (Ar), Hebrew (He).
  * **Sinitic:** Mandarin (Zh).


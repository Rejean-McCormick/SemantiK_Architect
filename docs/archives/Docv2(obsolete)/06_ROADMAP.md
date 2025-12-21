# 06\. Roadmap & Future Architecture

## 1\. Overview

The current architecture (V1) relies on in-memory JSON loading and regex-based morphology. While sufficient for prototyping and low-latency demonstrations with limited vocabularies, it faces scalability bottlenecks as the lexicon grows. This roadmap outlines the transition to V2.

## 2\. Database Migration Strategy

  * **Current State:** Flat JSON files loaded into Python dictionaries at startup.
  * **Limitation:** Memory usage scales linearly with lexicon size; startup time increases; no relational integrity.
  * **V2 Target:** **Relational/Graph Storage** (SQLite/PostgreSQL).
      * **Schema:** `lexicon` (lemmas), `forms` (inflections), `morphology` (rules).
      * **Benefits:** $O(1)$ indexed lookups, lazy loading, and SQL constraints for data integrity.

## 3\. Advanced Morphology Engine (FST)

  * **Current State:** `MorphologyBuilder` classes using Python string manipulation (regex).
  * **Limitation:** Difficult to handle non-concatenative morphology (Semitic roots) or polysynthetic sandhi (Inuktitut).
  * **V2 Target:** **Finite State Transducers (FST)**.
      * **Libraries:** Pynini or HFST.
      * **Mechanism:** Morphology defined as a graph of states (Root $\to$ Suffix A $\to$ Suffix B).

## 4\. Grammatical Framework (GF) Integration

*Status: Research / Experimental*

We are exploring alignment with the **Grammatical Framework (GF)** to leverage its Resource Grammar Library (RGL).

  * **Strategy:** "Parasitic" Morphology.
  * **Mechanism:** Map semantic frames (`Bio`, `Event`) to GF Abstract Syntax Trees.
  * **Benefit:** "Outsource" complex inflection (e.g., Finnish cases, Russian aspect) to GF's RGL while keeping the lightweight Python engine for simpler languages.

## 5\. API & Generation Evolution

  * **Current State:** Single-sentence generation.
  * **V2 Target:** **Document-Level Generation**.
      * **Discourse Planning:** Ordering facts logically (Birth $\to$ Career $\to$ Death).
      * **Aggregation:** Combining sentences ("She is X. She is Y." $\to$ "She is X and Y.").
      * **Referring Expressions:** Generating pronouns ("She", "Her") naturally.

## 6\. Quality Assurance Pipeline

  * **Current State:** Unit tests checking string equality.
  * **V2 Target:** **Round-Trip Evaluation**.
      * Generate text in Language X $\to$ Translate to English via External API $\to$ Compare with original intent.

-----

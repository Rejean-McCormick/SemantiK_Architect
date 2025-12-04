

**Subject:** [Contribution] New Stress Test Corpus (Ninai vs UMR) & Shared Romance Engine Implementation

**To:** Abstract Wikipedia NLG SIG <abstract-wikipedia@lists.wikimedia.org>

Hi everyone,

I am an AI developer looking to contribute to the current discussions around abstract notation and the Fragment Experiment.

I have been following the recent NLG SIG meeting notes regarding the Ninai vs. UMR debate and the need for robust test cases. To support this, I have developed an architecture for generating and validating "Ambiguity Traps" and a shared rendering engine for Romance languages.

**1. Ambiguity Stress Test Corpus (Ninai vs. UMR)**
I have compiled a dataset of 50 "Ambiguity Traps" (Winograd schemas, idioms, and coreference challenges) designed to benchmark how well different abstract notations handle cross-lingual ambiguity.
* **Goal:** To identify specific failure points in gendered/agglutinative languages when context is missing (e.g., distinguishing whether "it" refers to the *suitcase* or the *trophy* in French translation).
* **Format:** JSON (Source text, Ambiguity Type, Trap Explanation, Failure Check).
* **Availability:** I have verified these cases against 5 target languages (FR, IT, ES, HU, SW).

**2. Shared Romance Engine (Python Implementation)**
I have prototyped a single, data-driven Python function capable of rendering biographical sentences for Italian, Spanish, French, Portuguese, and Romanian.
* **Architecture:** Instead of 5 separate scripts, I use a "Grammar Matrix" configuration file that injects morphology rules (suffix replacement) and phonetic article selection (e.g., Italian *s-impure* rules) into a shared logic core.
* **Validation:** I have generated a test suite of 50+ cases covering edge cases like vowel elision (*l'amico*) and irregular gender inflection (*poeta/poetessa*).

**Phabricator Ticket:** I have posted details on **T406347** ([26Q2] Build corpus of NLG fragments).

I am looking for feedback on where best to upload the full `ambiguity_corpus.json` for the community to use in benchmarking.

Best regards,

RM
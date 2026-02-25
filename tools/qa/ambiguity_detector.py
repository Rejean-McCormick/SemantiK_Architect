# tools/qa/ambiguity_detector.py
"""
Ambiguity Detector (AI-Assisted Quality Assurance).

This tool hunts for "Ambiguity Traps" in the grammar.
1. It generates (or accepts) sentences known to be linguistically fragile.
2. It parses them using the GF Engine.
3. It flags sentences that produce >1 Parse Tree (Syntactic Ambiguity).

Usage:
    python tools/qa/ambiguity_detector.py --lang eng --topic "biography"
    python tools/qa/ambiguity_detector.py --lang eng --sentence "I saw the man with the telescope"

Output:
    JSON report classifying sentences as Safe (1 tree), Ambiguous (>1 trees), or Broken (0 trees).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

# --- Setup Path to import from 'app' ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../../"))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from utils.tool_logger import ToolLogger

try:
    from app.shared.config import settings
except ImportError:
    try:
        from app.core.config import settings
    except ImportError:
        print("[FATAL] Config import failed.", file=sys.stderr)
        sys.exit(1)

# Use GFGrammarEngine explicitly
from app.adapters.engines.gf_wrapper import GFGrammarEngine

# --- Logging Setup ---
log = ToolLogger("ambiguity_detector")

# --- Mock Seeds ---
STATIC_SEEDS: Dict[str, List[str]] = {
    "general": [
        "I saw the man with the telescope",  # Classic PP attachment ambiguity
        "Flying planes can be dangerous",    # Adjective vs Gerund
        "The fish is ready to eat",          # Subject vs Object
        "Time flies like an arrow",          # Noun vs Verb
    ],
    "biography": [
        "She is a French history professor",         # (French history) professor vs French (history professor)
        "He married the woman from Paris in 1990",   # Married in 1990 vs Woman from Paris (who was there in 1990)
        "The writer wrote the book on the table",    # Wrote (on the table) vs (Book on the table)
    ],
}


class AmbiguityDetector:
    def __init__(self, lang: str, pgf_path: Optional[str] = None):
        self.lang = (lang or "").strip()
        if not self.lang:
            log.error("FATAL: --lang cannot be empty.", fatal=True)

        try:
            # Use GFGrammarEngine and correct arg 'lib_path'
            self.engine = GFGrammarEngine(lib_path=pgf_path or settings.PGF_PATH)
        except Exception as e:
            log.error(f"FATAL: Could not load GF Engine. {e}", fatal=True)

        # Ensure grammar is loaded (some wrappers lazy-load).
        _ = self.engine.grammar

        # Resolve user input to an actual PGF concrete module key.
        resolver = getattr(self.engine, "_resolve_concrete_name", None)
        resolved: Optional[str] = None
        if callable(resolver):
            resolved = resolver(self.lang)

            # Allow passing raw suffix without "Wiki" prefix.
            if not resolved and not self.lang.startswith("Wiki"):
                resolved = resolver(f"Wiki{self.lang}")

        if not resolved:
            log.error(
                f"FATAL: Language '{self.lang}' could not be resolved to a concrete PGF module.",
                fatal=True,
            )

        self.concrete = resolved

    def generate_candidates(self, topic: str) -> List[str]:
        """Returns curated seeds for the given topic."""
        topic = (topic or "").strip() or "general"
        log.info(f"[AI] Generating ambiguous candidates for topic: '{topic}'...")
        return STATIC_SEEDS.get(topic, STATIC_SEEDS["general"])

    def analyze_sentence(self, sentence: str) -> Dict[str, Any]:
        """Parses the sentence and counts the trees."""
        try:
            parses = list(self.engine.parse(sentence, language=self.concrete))
            count = len(parses)

            status = "SAFE"
            if count == 0:
                status = "FAIL_NO_PARSE"
            elif count > 1:
                status = "AMBIGUOUS"

            return {
                "sentence": sentence,
                "tree_count": count,
                "status": status,
                "trees": [str(t) for t in parses] if count > 1 else [],
            }
        except Exception as e:
            return {
                "sentence": sentence,
                "tree_count": 0,
                "status": "ERROR",
                "error": str(e),
            }

    def run_batch(self, sentences: List[str]) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        stats = {"safe": 0, "ambiguous": 0, "fail": 0}

        for s in sentences:
            res = self.analyze_sentence(s)
            results.append(res)

            if res["status"] == "SAFE":
                stats["safe"] += 1
            elif res["status"] == "AMBIGUOUS":
                stats["ambiguous"] += 1
            else:
                stats["fail"] += 1

        return {"summary": stats, "details": results}


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect Syntactic Ambiguity in Grammar.")
    parser.add_argument("--lang", required=True, help="Target language code or Wiki concrete (e.g., eng, en, WikiEng).")
    parser.add_argument("--sentence", help="Single sentence to check.")
    parser.add_argument("--topic", default="general", help="Topic for batch generation.")
    parser.add_argument("--json-out", help="Path to save JSON report.")

    args = parser.parse_args()

    log.header(
        {
            "Language": args.lang,
            "Mode": "Sentence Check" if args.sentence else f"Topic Batch ({args.topic})",
        }
    )

    detector = AmbiguityDetector(args.lang)

    # 1. Select Mode
    if args.sentence:
        candidates = [args.sentence]
    else:
        candidates = detector.generate_candidates(args.topic)

    # 2. Run Analysis
    log.stage("Analysis", f"Parsing {len(candidates)} sentences using '{detector.concrete}'...")
    report = detector.run_batch(candidates)

    # 3. Print Console Report
    log.info("")
    log.info("--- Metrics ---")
    log.info(f"Safe:      {report['summary']['safe']}")
    log.info(f"Ambiguous: {report['summary']['ambiguous']} (Requires disambiguation rules)")
    log.info(f"Failed:    {report['summary']['fail']} (Grammar cannot cover these)")
    log.info("---------------")

    for item in report["details"]:
        if item["status"] == "AMBIGUOUS":
            log.warning(f"Ambiguous: '{item['sentence']}'")
            log.info(f"  -> Found {item['tree_count']} interpretations.")
            for i, t in enumerate(item["trees"][:2]):
                log.info(f"     {i + 1}. {t}")
        elif item["status"] == "FAIL_NO_PARSE":
            if args.sentence:
                log.error(f"Parse failed: '{item['sentence']}' - No parse tree found.")

    # 4. Save JSON
    if args.json_out:
        log.stage("Export", f"Saving report to {args.json_out}")
        try:
            with open(args.json_out, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save JSON: {e}")

    success = report["summary"]["ambiguous"] == 0
    log.summary(
        {
            "Safe": report["summary"]["safe"],
            "Ambiguous": report["summary"]["ambiguous"],
            "Failed": report["summary"]["fail"],
        },
        success=success,
    )

    # Exit code: 1 if ANY ambiguity found (so CI/CD can block ambiguous releases)
    if not success:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
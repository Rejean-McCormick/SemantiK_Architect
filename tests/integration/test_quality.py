# tests/integration/test_quality.py
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.shared.config import settings

# Import the concrete adapter (PGF-backed) used by the running system
from app.adapters.engines.gf_wrapper import GFGrammarEngine as GrammarEngine

# Mock judge to ensure tests don't crash if AI services aren't configured locally
try:
    from ai_services.judge import judge
except ImportError:
    class MockJudge:
        def evaluate_case(self, text, case):
            return {"score": 0.0, "verdict": "SKIPPED", "critique": "Judge module missing."}

    judge = MockJudge()


# ==============================================================================
# HELPERS
# ==============================================================================

def _ai_unavailable_reason(report: dict) -> str | None:
    """
    Returns a reason string if the AI Judge is unavailable/misconfigured,
    otherwise returns None.
    """
    verdict = str(report.get("verdict", "")).strip().upper()
    critique = str(report.get("critique", "")).strip()

    # Explicit skip from judge
    if verdict.startswith("SKIPPED"):
        return critique or "AI Judge disabled."

    # Common misconfig/auth errors (Gemini / Google Generative Language)
    crit_upper = critique.upper()
    if verdict == "ERROR" and (
        "API_KEY_INVALID" in crit_upper
        or "API KEY NOT VALID" in crit_upper
        or "PLEASE PASS A VALID API KEY" in crit_upper
        or "UNAUTHENTICATED" in crit_upper
        or "PERMISSION_DENIED" in crit_upper
    ):
        return critique or "AI Judge misconfigured (invalid/unauthorized API key)."

    return None


# ==============================================================================
# SETUP & FIXTURES
# ==============================================================================

def load_gold_standard_cases():
    """
    Loads the ground truth dataset for validation during test collection.
    Returns an empty list if file is missing (to avoid collection crashes).
    """
    if not hasattr(settings, "GOLD_STANDARD_PATH") or not settings.GOLD_STANDARD_PATH:
        return []

    path = Path(settings.GOLD_STANDARD_PATH)
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


TEST_CASES = load_gold_standard_cases()


@pytest.fixture(scope="module")
def engine():
    """
    Initializes the GrammarEngine once for the whole test module.
    """
    eng = GrammarEngine()

    # Skip early if PGF binary isn't present where the engine resolved it.
    if not Path(eng.pgf_path).exists():
        pytest.skip(f"PGF binary not found at {eng.pgf_path}. Please build the grammar first.")

    return eng


# ==============================================================================
# QUALITY REGRESSION SUITE
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.skipif(
    not TEST_CASES,
    reason=f"Gold standard file not found or empty at {getattr(settings, 'GOLD_STANDARD_PATH', 'UNKNOWN')}",
)
@pytest.mark.parametrize("case", TEST_CASES, ids=lambda c: f"{c.get('lang', 'unk')}-{c.get('id', 'unk')}")
async def test_language_quality_regression(engine, case):
    """
    Integration test that validates generated text against the AI Judge.

    Steps:
    1. Generate text using the actual GF engine.
    2. Pass output to Judge Agent (LLM).
    3. Assert Judge Score > 0.8 (ONLY when AI Judge is available).
    """
    lang = case["lang"]
    intent = case["intent"]
    expected = case["expected"]
    case_id = case.get("id", "unknown")

    # 1) Ensure grammar is loaded (GFGrammarEngine loads lazily)
    status = await engine.status()
    if not status.get("loaded"):
        pytest.skip(
            "Grammar not loaded in engine. "
            f"pgf_path={status.get('pgf_path')} error_type={status.get('error_type')} error={status.get('error')}"
        )

    # 2) Validation: ensure language resolves to an actual concrete key in the PGF
    resolved = engine._resolve_concrete_name(lang)  # noqa: SLF001 (test-only access)
    if not resolved:
        pytest.skip(f"Language '{lang}' not found in PGF binary (unable to resolve to a concrete grammar).")

    # 3) Generation
    generated_text = ""
    try:
        result = await engine.generate(lang, intent)

        if isinstance(result, dict):
            generated_text = result.get("text", "").strip()
        else:
            generated_text = getattr(result, "text", "").strip()

    except Exception as e:
        pytest.fail(
            "Engine generation crashed.\n"
            f"  Language: {lang}\n"
            f"  Resolved: {resolved}\n"
            f"  PGF:      {engine.pgf_path}\n"
            f"  Intent:   {intent}\n"
            f"  Error:    {str(e)}"
        )

    assert generated_text, (
        "Engine returned empty string.\n"
        f"  Language: {lang}\n"
        f"  Resolved: {resolved}\n"
        f"  Intent:   {intent}"
    )

    # 4) Evaluation: Invoke The AI Judge (sync)
    report = judge.evaluate_case(generated_text, case)

    # If Judge is unavailable/misconfigured, SKIP (do not fail the grammar pipeline)
    reason = _ai_unavailable_reason(report)
    if reason is not None:
        pytest.skip(f"AI Judge unavailable: {reason}")

    score = report.get("score", 0.0)
    verdict = report.get("verdict", "FAIL")
    critique = report.get("critique", "No critique provided.")

    # 5) Reporting (Visible with pytest -s)
    print(f"\n[{verdict}] {lang} (ID: {case_id}) | Score: {score}")
    if score < 0.8:
        print(f"   Intent:   {intent}")
        print(f"   Expected: {expected}")
        print(f"   Actual:   {generated_text}")
        print(f"   Critique: {critique}")

    failure_msg = (
        f"\nQuality Failure in {lang} (ID: {case_id}):\n"
        f"---------------------------------------------------\n"
        f"Language: {lang} (resolved={resolved})\n"
        f"Intent:   {intent}\n"
        f"Expected: {expected}\n"
        f"Actual:   {generated_text}\n"
        f"Score:    {score} (Threshold: 0.8)\n"
        f"Verdict:  {verdict}\n"
        f"Critique: {critique}\n"
        f"---------------------------------------------------"
    )

    assert score >= 0.8, failure_msg


def test_judge_connectivity():
    """Simple check to ensure the Judge Agent is online and configured."""
    if not getattr(settings, "GOOGLE_API_KEY", None):
        pytest.skip("AI testing skipped: GOOGLE_API_KEY missing.")

    if not hasattr(judge, "_client") or judge._client is None:
        pytest.skip("AI testing skipped: Judge client not initialized (likely invalid/missing key).")
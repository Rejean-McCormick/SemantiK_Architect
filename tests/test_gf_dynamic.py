# tests/test_gf_dynamic.py
from __future__ import annotations

from pathlib import Path

import pytest

pgf = pytest.importorskip("pgf")

from app.adapters.engines.gf_wrapper import GFGrammarEngine
from app.core.domain.planning.construction_plan import ConstructionPlan


def _select_input_lang(engine: GFGrammarEngine) -> str:
    """
    Prefer stable aliases first so we exercise the wrapper's language-resolution
    behavior, not only direct concrete names.
    """
    for candidate in ("eng", "en", "fre", "fr", "WikiEng", "WikiFre"):
        if engine._resolve_concrete_name(candidate):
            return candidate

    loaded = sorted(getattr(engine.grammar, "languages", {}).keys())
    if not loaded:
        pytest.skip("GF grammar loaded, but contains no concrete languages.")
    return loaded[0]


@pytest.fixture(scope="module")
def gf_engine() -> GFGrammarEngine:
    """
    Load the GF wrapper once for the module.

    This remains a dynamic-PGF regression test, so it skips cleanly when the PGF
    binary or Python pgf module is unavailable in the runtime.
    """
    engine = GFGrammarEngine()
    pgf_path = Path(engine.pgf_path)

    if not pgf_path.exists():
        pytest.skip(
            f"PGF binary not found at {pgf_path}. "
            "Run the GF build step before executing dynamic GF tests."
        )

    grammar = engine.grammar
    if grammar is None:
        pytest.skip(
            "GF grammar could not be loaded dynamically. "
            f"error_type={engine.last_load_error_type!r}, "
            f"error={engine.last_load_error!r}"
        )

    return engine


def _assert_shared_surface_result_contract(
    result,
    *,
    expected_lang_code: str,
    expected_construction_id: str,
    expected_backend: str,
    expected_fallback_used: bool,
) -> None:
    """
    Shared assertion helper aligned with the final runtime/public contract lock.

    This test file is runtime-facing, but the runtime result is expected to
    arrive mapper-ready on the nominal path and structurally stable on explicit
    fallback paths.
    """
    assert result.text, "SurfaceResult.text must be non-empty."
    assert isinstance(result.text, str)
    assert result.lang_code == expected_lang_code
    assert result.construction_id == expected_construction_id
    assert result.renderer_backend == expected_backend
    assert result.fallback_used is expected_fallback_used

    assert isinstance(result.tokens, list)
    assert result.tokens, "SurfaceResult.tokens must be present and non-empty."
    assert all(isinstance(token, str) for token in result.tokens)

    assert isinstance(result.debug_info, dict)
    assert isinstance(result.generation_time_ms, (int, float))
    assert result.generation_time_ms >= 0.0

    # Required shared parity keys.
    assert result.debug_info["construction_id"] == expected_construction_id
    assert result.debug_info["renderer_backend"] == expected_backend
    assert result.debug_info["lang_code"] == expected_lang_code
    assert result.debug_info["fallback_used"] is expected_fallback_used

    # Required runtime-path observability.
    assert isinstance(result.debug_info["slot_keys"], list)
    assert "runtime_path" in result.debug_info
    assert isinstance(result.debug_info["runtime_path"], str)
    assert result.debug_info["runtime_path"]


@pytest.mark.asyncio
async def test_gf_status_reports_loaded_runtime_and_languages(
    gf_engine: GFGrammarEngine,
) -> None:
    status = await gf_engine.status()
    supported = await gf_engine.get_supported_languages()

    assert status["loaded"] is True
    assert status["backend"] == "gf"
    assert status["language_count"] > 0
    assert Path(status["pgf_path"]).exists()

    assert supported
    assert sorted(supported) == sorted(gf_engine.grammar.languages.keys())


def test_linearize_simple_phrase_across_loaded_languages(
    gf_engine: GFGrammarEngine,
) -> None:
    """
    Smoke test the actual PGF binary directly across every loaded concrete
    syntax. This file is explicitly about dynamic loading + linearization, so an
    abstract-expression test is appropriate here.
    """
    expr = pgf.readExpr("SimpNP apple_N")

    failures: list[str] = []
    successes: list[tuple[str, str]] = []

    for lang_name in sorted(gf_engine.grammar.languages.keys()):
        text = gf_engine.linearize(expr, lang_name)

        if not text or text.startswith("<"):
            failures.append(f"{lang_name}: {text!r}")
            continue

        successes.append((lang_name, text))

    assert successes, "No loaded GF language produced a non-empty linearization."
    assert not failures, (
        "Some loaded GF languages failed to linearize a simple shared AST.\n"
        + "\n".join(failures)
    )


def test_linearize_invalid_expression_returns_stable_error_placeholder(
    gf_engine: GFGrammarEngine,
) -> None:
    lang = _select_input_lang(gf_engine)
    text = gf_engine.linearize("This Is Not Valid GF Syntax (", lang)

    assert text.startswith("<LinearizeError:"), text


@pytest.mark.asyncio
async def test_realize_bio_construction_plan_returns_surface_result_with_metadata(
    gf_engine: GFGrammarEngine,
) -> None:
    """
    Keep this file aligned with the planner-first runtime by proving the GF
    wrapper can consume ConstructionPlan directly and emit canonical runtime
    metadata without depending on public-response repair.
    """
    lang = _select_input_lang(gf_engine)
    resolved_language = gf_engine._resolve_concrete_name(lang)

    plan = ConstructionPlan(
        construction_id="copula_equative_classification",
        lang_code=lang,
        slot_map={
            "subject": "Marie Curie",
            "profession": "physicist",
            "nationality": "Polish",
        },
        metadata={
            "base_construction_id": "copula_equative_classification",
        },
    )

    result = await gf_engine.realize(plan)

    _assert_shared_surface_result_contract(
        result,
        expected_lang_code=lang,
        expected_construction_id="copula_equative_classification",
        expected_backend="gf",
        expected_fallback_used=False,
    )

    assert not result.text.startswith("<"), result.text
    assert result.debug_info["runtime_path"] == "planner_first"
    assert result.debug_info["resolved_language"] == resolved_language
    assert set(result.debug_info["slot_keys"]) == {
        "subject",
        "profession",
        "nationality",
    }
    assert "backend_trace" in result.debug_info
    assert isinstance(result.debug_info["backend_trace"], list)
    assert any(
        "constructed GF AST from ConstructionPlan" in step
        for step in result.debug_info["backend_trace"]
    )


@pytest.mark.asyncio
async def test_realize_unsupported_construction_is_explicit_fallback(
    gf_engine: GFGrammarEngine,
) -> None:
    """
    Regression guard for the migration docs: no silent success and no hidden
    backend substitution. Unsupported GF constructions must remain explicit.
    """
    lang = _select_input_lang(gf_engine)

    plan = ConstructionPlan(
        construction_id="relational_temporal_relation",
        lang_code=lang,
        slot_map={
            "left": {"name": "World War II"},
            "right": {"start_year": 1951},
            "relation": "before",
        },
    )

    result = await gf_engine.realize(plan)

    _assert_shared_surface_result_contract(
        result,
        expected_lang_code=lang,
        expected_construction_id="relational_temporal_relation",
        expected_backend="gf",
        expected_fallback_used=True,
    )

    assert result.text.startswith("<GF Unsupported Construction:")
    assert result.debug_info["construction_id"] == "relational_temporal_relation"
    assert "warnings" in result.debug_info
    assert isinstance(result.debug_info["warnings"], list)
    assert any(
        "unsupported GF construction_id" in warning
        for warning in result.debug_info["warnings"]
    )


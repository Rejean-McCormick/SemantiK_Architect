# tests/integration/test_generate_via_planner_fr.py
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.domain.frame import BioFrame
from app.core.domain.models import Sentence, SurfaceResult
from app.core.domain.planning.construction_plan import ConstructionPlan
from app.core.domain.planning.planned_sentence import PlannedSentence
from app.core.use_cases.generate_text import GenerateText


class RecordingFrenchPlanner:
    """
    Minimal integration-test planner.

    GenerateText currently tries a small set of migration-safe planner
    signatures, beginning with:

        planner.plan((frame,), lang_code="fr")

    This implementation accepts that preferred shape and emits one
    canonical PlannedSentence.
    """

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def plan(
        self,
        frames: tuple[Any, ...] | list[Any] | Any,
        *,
        lang_code: str,
        domain: str | None = None,
    ) -> list[PlannedSentence]:
        if isinstance(frames, (tuple, list)):
            assert len(frames) == 1
            frame = frames[0]
        else:
            frame = frames

        self.calls.append(
            {
                "lang_code": lang_code,
                "domain": domain,
                "frame_type": getattr(frame, "frame_type", None),
            }
        )

        return [
            PlannedSentence(
                construction_id="copula_equative_classification",
                lang_code=lang_code,
                frame=frame,
                topic_entity_id="Q7259",
                focus_role="predicate_nominal",
                generation_options={"register": "neutral"},
                metadata={"source": "test_planner_fr"},
            )
        ]


class RecordingFrenchLexicalResolver:
    """
    Minimal lexical-resolution stage that materializes a renderer-facing
    ConstructionPlan from the planner output.
    """

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def resolve(
        self,
        planned_sentence: PlannedSentence,
        *,
        lang_code: str | None = None,
        frame: Any | None = None,
    ) -> ConstructionPlan:
        assert isinstance(planned_sentence, PlannedSentence)

        resolved_lang = (lang_code or planned_sentence.lang_code).strip().lower()
        self.calls.append(
            {
                "lang_code": resolved_lang,
                "construction_id": planned_sentence.construction_id,
                "frame_type": getattr(frame, "frame_type", None),
            }
        )

        return ConstructionPlan(
            construction_id=planned_sentence.construction_id,
            lang_code=resolved_lang,
            slot_map={
                "subject": {
                    "label": "Ada Lovelace",
                    "qid": "Q7259",
                    "entity_type": "person",
                },
                "profession": "mathématicienne",
                "nationality": "britannique",
                "gender": "f",
            },
            generation_options=dict(planned_sentence.generation_options),
            topic_entity_id=planned_sentence.topic_entity_id,
            focus_role=planned_sentence.focus_role,
            lexical_bindings={
                "profession": {
                    "lemma": "mathématicienne",
                    "pos": "NOUN",
                    "source": "test_lexicon_fr",
                    "confidence": 1.0,
                },
                "nationality": {
                    "lemma": "britannique",
                    "pos": "ADJ",
                    "source": "test_lexicon_fr",
                    "confidence": 1.0,
                },
            },
            provenance={
                "planner_source": "test_planner_fr",
            },
            metadata={
                "lexical_resolution": {
                    "applied": True,
                    "resolved_slots": ["profession", "nationality"],
                    "fallback_used": False,
                },
                "planner_metadata": dict(planned_sentence.metadata),
            },
        )


class RecordingFrenchRealizer:
    """
    Minimal renderer that proves GenerateText is consuming the shared
    ConstructionPlan boundary and emitting stable runtime metadata.
    """

    backend_name = "family"

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def realize(
        self,
        construction_plan: ConstructionPlan,
        *,
        lang_code: str | None = None,
        frame: Any | None = None,
    ) -> SurfaceResult:
        assert isinstance(construction_plan, ConstructionPlan)

        effective_lang = (lang_code or construction_plan.lang_code).strip().lower()
        slot_keys = list(construction_plan.slot_keys)

        self.calls.append(
            {
                "lang_code": effective_lang,
                "construction_id": construction_plan.construction_id,
                "slot_keys": slot_keys,
                "frame_type": getattr(frame, "frame_type", None),
            }
        )

        return SurfaceResult(
            text="Ada Lovelace est une mathématicienne britannique.",
            lang_code=effective_lang,
            construction_id=construction_plan.construction_id,
            renderer_backend=self.backend_name,
            fallback_used=False,
            tokens=[
                "Ada",
                "Lovelace",
                "est",
                "une",
                "mathématicienne",
                "britannique.",
            ],
            debug_info={
                "runtime_path": "planner_first",
                "construction_id": construction_plan.construction_id,
                "renderer_backend": self.backend_name,
                "lang_code": effective_lang,
                "fallback_used": False,
                "resolved_language": "WikiFre",
                "selected_backend": self.backend_name,
                "attempted_backends": [self.backend_name],
                "slot_keys": slot_keys,
                "lexical_resolution": dict(
                    construction_plan.metadata.get("lexical_resolution", {})
                ),
                "backend_trace": [
                    "validated ConstructionPlan",
                    "resolved lexical bindings",
                    "assembled FR equative clause",
                ],
            },
            generation_time_ms=7.5,
        )


@pytest.fixture
def sample_french_bio_frame() -> BioFrame:
    return BioFrame(
        frame_type="bio",
        subject={
            "name": "Ada Lovelace",
            "qid": "Q7259",
            "gender": "f",
        },
        context_id="Q7259",
        meta={"register": "neutral"},
    )


def _assert_runtime_result_contract(result: Sentence) -> None:
    """
    Integration-level contract assertions for the planner-first EN/FR cutover.

    GenerateText may still return a broader Sentence compatibility object,
    but the result must carry stable nominal-path runtime truth either as
    top-level fields or, at minimum during compatibility wrapping, in
    structured debug_info.
    """
    assert isinstance(result, Sentence)
    assert isinstance(result.text, str) and result.text.strip()
    assert result.lang_code == "fr"

    debug = result.debug_info
    assert isinstance(debug, dict)

    # Canonical runtime-path truth
    assert debug["runtime_path"] == "planner_first"
    assert debug["fallback_used"] is False
    assert debug["construction_id"] == "copula_equative_classification"
    assert debug["renderer_backend"] == "family"
    assert debug["lang_code"] == "fr"

    # Required observability
    assert debug["selected_backend"] == "family"
    assert debug["attempted_backends"] == ["family"]
    assert debug["resolved_language"] == "WikiFre"
    assert set(debug["slot_keys"]) >= {"subject", "profession", "nationality"}
    assert debug["lexical_resolution"]["applied"] is True
    assert set(debug["lexical_resolution"]["resolved_slots"]) == {
        "profession",
        "nationality",
    }

    # Tokens must exist somewhere canonical and match the final text.
    top_level_tokens = getattr(result, "tokens", None)
    debug_tokens = debug.get("tokens")

    expected_tokens = [
        "Ada",
        "Lovelace",
        "est",
        "une",
        "mathématicienne",
        "britannique.",
    ]

    if top_level_tokens is not None:
        assert list(top_level_tokens) == expected_tokens
    if debug_tokens is not None:
        assert list(debug_tokens) == expected_tokens

    # If the broader Sentence model has already been upgraded with the
    # canonical top-level runtime fields, they must match debug_info.
    if hasattr(result, "construction_id"):
        assert getattr(result, "construction_id") == "copula_equative_classification"
    if hasattr(result, "renderer_backend"):
        assert getattr(result, "renderer_backend") == "family"
    if hasattr(result, "fallback_used"):
        assert getattr(result, "fallback_used") is False
    if hasattr(result, "generation_time_ms"):
        assert float(getattr(result, "generation_time_ms")) >= 0.0


@pytest.mark.asyncio
async def test_generate_via_planner_fr_returns_planner_first_sentence(
    sample_french_bio_frame: BioFrame,
) -> None:
    planner = RecordingFrenchPlanner()
    lexical_resolver = RecordingFrenchLexicalResolver()
    realizer = RecordingFrenchRealizer()

    use_case = GenerateText(
        planner=planner,
        lexical_resolver=lexical_resolver,
        realizer=realizer,
        allow_legacy_engine_fallback=False,
    )

    result = await use_case.execute("fr", sample_french_bio_frame)

    assert "Ada Lovelace" in result.text
    assert "mathématicienne" in result.text
    assert "britannique" in result.text

    _assert_runtime_result_contract(result)

    assert len(planner.calls) == 1
    assert planner.calls[0]["lang_code"] == "fr"
    assert planner.calls[0]["frame_type"] == "bio"

    assert len(lexical_resolver.calls) == 1
    assert lexical_resolver.calls[0]["lang_code"] == "fr"
    assert lexical_resolver.calls[0]["construction_id"] == (
        "copula_equative_classification"
    )

    assert len(realizer.calls) == 1
    assert realizer.calls[0]["lang_code"] == "fr"
    assert realizer.calls[0]["construction_id"] == "copula_equative_classification"
    assert set(realizer.calls[0]["slot_keys"]) >= {
        "subject",
        "profession",
        "nationality",
    }


@pytest.mark.asyncio
async def test_generate_via_planner_fr_prefers_planner_runtime_over_legacy_engine(
    sample_french_bio_frame: BioFrame,
) -> None:
    planner = RecordingFrenchPlanner()
    lexical_resolver = RecordingFrenchLexicalResolver()
    realizer = RecordingFrenchRealizer()

    legacy_engine = MagicMock()
    legacy_engine.generate = AsyncMock(
        return_value=Sentence(
            text="Ceci ne devrait jamais être utilisé.",
            lang_code="fr",
            debug_info={"runtime_path": "legacy_engine"},
            generation_time_ms=0.0,
        )
    )

    use_case = GenerateText(
        engine=legacy_engine,
        planner=planner,
        lexical_resolver=lexical_resolver,
        realizer=realizer,
        allow_legacy_engine_fallback=True,
    )

    result = await use_case.execute("fr", sample_french_bio_frame)

    assert "Ada Lovelace" in result.text
    assert "mathématicienne" in result.text

    _assert_runtime_result_contract(result)

    legacy_engine.generate.assert_not_awaited()
    assert len(planner.calls) == 1
    assert len(lexical_resolver.calls) == 1
    assert len(realizer.calls) == 1


@pytest.mark.asyncio
async def test_generate_via_planner_fr_is_deterministic_across_repeated_calls(
    sample_french_bio_frame: BioFrame,
) -> None:
    planner = RecordingFrenchPlanner()
    lexical_resolver = RecordingFrenchLexicalResolver()
    realizer = RecordingFrenchRealizer()

    use_case = GenerateText(
        planner=planner,
        lexical_resolver=lexical_resolver,
        realizer=realizer,
        allow_legacy_engine_fallback=False,
    )

    first = await use_case.execute("fr", sample_french_bio_frame)
    second = await use_case.execute("fr", sample_french_bio_frame)

    assert first.text == second.text
    assert first.lang_code == second.lang_code == "fr"
    assert first.debug_info["runtime_path"] == second.debug_info["runtime_path"] == (
        "planner_first"
    )
    assert first.debug_info["construction_id"] == second.debug_info["construction_id"] == (
        "copula_equative_classification"
    )
    assert first.debug_info["renderer_backend"] == second.debug_info["renderer_backend"] == (
        "family"
    )
    assert first.debug_info["fallback_used"] is False
    assert second.debug_info["fallback_used"] is False

    first_tokens = list(getattr(first, "tokens", []) or first.debug_info.get("tokens", []))
    second_tokens = list(
        getattr(second, "tokens", []) or second.debug_info.get("tokens", [])
    )
    assert first_tokens == second_tokens == [
        "Ada",
        "Lovelace",
        "est",
        "une",
        "mathématicienne",
        "britannique.",
    ]

    assert len(planner.calls) == 2
    assert len(lexical_resolver.calls) == 2
    assert len(realizer.calls) == 2


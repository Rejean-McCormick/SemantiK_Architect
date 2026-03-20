# tests/integration/test_generate_via_planner_en.py
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.domain.exceptions import DomainError
from app.core.domain.models import Frame, Sentence, SurfaceResult
from app.core.domain.planning.construction_plan import ConstructionPlan
from app.core.domain.planning.planned_sentence import PlannedSentence
from app.core.use_cases.generate_text import GenerateText


def _english_bio_frame() -> Frame:
    return Frame(
        frame_type="bio",
        subject={
            "name": "Alan Turing",
            "qid": "Q7251",
        },
        properties={
            "profession": "mathematician",
            "nationality": "British",
        },
        meta={
            "source_id": "integration_en_bio_001",
        },
    )


def _slot_keys(plan: ConstructionPlan) -> list[str]:
    keys = getattr(plan, "slot_keys", None)
    if callable(keys):
        return list(keys())
    if keys is not None:
        return list(keys)
    return list(getattr(plan, "slot_map", {}).keys())


class RecordingPlanner:
    def __init__(self, construction_id: str = "copula_equative_classification") -> None:
        self.construction_id = construction_id
        self.calls: list[dict[str, Any]] = []

    async def plan(
        self,
        frames: Any,
        *,
        lang_code: str,
        domain: str | None = None,
    ) -> list[PlannedSentence]:
        frame = frames[0] if isinstance(frames, (list, tuple)) else frames
        subject = getattr(frame, "subject", {}) if frame is not None else {}

        self.calls.append(
            {
                "lang_code": lang_code,
                "domain": domain,
                "frame_type": getattr(frame, "frame_type", None),
                "subject_name": subject.get("name"),
            }
        )

        return [
            PlannedSentence(
                construction_id=self.construction_id,
                lang_code=lang_code,
                frame=frame,
                topic_entity_id="Q7251",
                focus_role="predicate_nominal",
                discourse_mode="declarative",
                generation_options={"register": "default"},
                metadata={"planner_stage": "integration_test_en"},
                source_frame_ids=("integration_en_bio_001",),
                priority=1,
            )
        ]


class RecordingLexicalResolver:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def resolve(
        self,
        payload: PlannedSentence,
        *,
        lang_code: str | None = None,
        frame: Frame | None = None,
    ) -> ConstructionPlan:
        assert isinstance(payload, PlannedSentence)

        resolved_lang = (lang_code or payload.lang_code).strip().lower()
        frame_subject = getattr(frame, "subject", {}) if frame is not None else {}
        frame_props = getattr(frame, "properties", {}) if frame is not None else {}

        profession = frame_props.get("profession", "mathematician")
        nationality = frame_props.get("nationality", "British")

        plan = ConstructionPlan(
            construction_id=payload.construction_id,
            lang_code=resolved_lang,
            slot_map={
                "subject": {
                    "label": frame_subject.get("name", "Alan Turing"),
                    "qid": frame_subject.get("qid", "Q7251"),
                    "entity_type": "person",
                },
                "profession": profession,
                "nationality": nationality,
                "predicate_nominal": {
                    "role": "profession_plus_nationality",
                    "profession": profession,
                    "nationality": nationality,
                },
            },
            generation_options=dict(payload.generation_options),
            topic_entity_id=payload.topic_entity_id,
            focus_role=payload.focus_role,
            lexical_bindings={
                "profession": {
                    "lemma": profession,
                    "source": "test_lexicon_en",
                    "confidence": 1.0,
                },
                "nationality": {
                    "lemma": nationality,
                    "source": "test_lexicon_en",
                    "confidence": 1.0,
                },
            },
            provenance={
                "source_frame_ids": list(payload.source_frame_ids or ()),
                "resolver": "integration_test_en",
            },
            metadata={
                "lexical_resolution": {
                    "applied": True,
                    "resolved_slots": ["profession", "nationality"],
                    "fallback_used": False,
                },
                "planner_metadata": dict(payload.metadata),
                "source_frame_id": payload.primary_source_frame_id,
            },
        )

        self.calls.append(
            {
                "planned_sentence": payload,
                "construction_plan": plan,
            }
        )
        return plan


class RecordingFamilyRealizer:
    backend_name = "family"

    def __init__(self) -> None:
        self.calls: list[ConstructionPlan] = []

    async def realize(
        self,
        payload: ConstructionPlan,
        *,
        lang_code: str | None = None,
        frame: Frame | None = None,
    ) -> SurfaceResult:
        assert isinstance(payload, ConstructionPlan)
        self.calls.append(payload)

        subject = payload.get_slot("subject")
        profession_binding = payload.lexical_bindings["profession"]
        nationality_binding = payload.lexical_bindings["nationality"]

        profession = profession_binding.get("lemma", "mathematician")
        nationality = nationality_binding.get("lemma", "British")
        effective_lang = (lang_code or payload.lang_code).strip().lower()

        text = f"{subject['label']} is a {nationality} {profession}."
        tokens = [
            "Alan",
            "Turing",
            "is",
            "a",
            "British",
            "mathematician.",
        ]

        return SurfaceResult(
            text=text,
            lang_code=effective_lang,
            construction_id=payload.construction_id,
            renderer_backend=self.backend_name,
            fallback_used=False,
            tokens=tokens,
            debug_info={
                "runtime_path": "planner_first",
                "construction_id": payload.construction_id,
                "renderer_backend": self.backend_name,
                "lang_code": effective_lang,
                "fallback_used": False,
                "resolved_language": "WikiEng",
                "selected_backend": self.backend_name,
                "attempted_backends": [self.backend_name],
                "slot_keys": _slot_keys(payload),
                "lexical_binding_keys": sorted(payload.lexical_bindings.keys()),
                "lexical_resolution": dict(
                    payload.metadata.get("lexical_resolution", {})
                ),
                "backend_trace": [
                    "validated ConstructionPlan",
                    "resolved lexical bindings",
                    "assembled EN equative clause",
                ],
            },
            generation_time_ms=6.5,
        )


class FailingRealizer:
    backend_name = "family"

    def __init__(self) -> None:
        self.calls: list[ConstructionPlan] = []

    async def realize(
        self,
        payload: ConstructionPlan,
        *,
        lang_code: str | None = None,
        frame: Frame | None = None,
    ) -> SurfaceResult:
        assert isinstance(payload, ConstructionPlan)
        self.calls.append(payload)
        raise RuntimeError("realizer exploded")


def _assert_runtime_result_contract(result: Sentence) -> None:
    assert isinstance(result, Sentence)
    assert result.text == "Alan Turing is a British mathematician."
    assert result.lang_code == "en"

    debug = result.debug_info
    assert isinstance(debug, dict)

    assert debug["runtime_path"] == "planner_first"
    assert debug["fallback_used"] is False
    assert debug["construction_id"] == "copula_equative_classification"
    assert debug["renderer_backend"] == "family"
    assert debug["lang_code"] == "en"

    assert debug["selected_backend"] == "family"
    assert debug["attempted_backends"] == ["family"]
    assert debug["resolved_language"] == "WikiEng"
    assert set(debug["slot_keys"]) >= {"subject", "profession", "nationality"}
    assert debug["lexical_binding_keys"] == ["nationality", "profession"]
    assert debug["lexical_resolution"]["applied"] is True
    assert set(debug["lexical_resolution"]["resolved_slots"]) == {
        "profession",
        "nationality",
    }

    expected_tokens = [
        "Alan",
        "Turing",
        "is",
        "a",
        "British",
        "mathematician.",
    ]

    top_level_tokens = getattr(result, "tokens", None)
    debug_tokens = debug.get("tokens")

    if top_level_tokens is not None:
        assert list(top_level_tokens) == expected_tokens
    if debug_tokens is not None:
        assert list(debug_tokens) == expected_tokens

    if hasattr(result, "construction_id"):
        assert getattr(result, "construction_id") == "copula_equative_classification"
    if hasattr(result, "renderer_backend"):
        assert getattr(result, "renderer_backend") == "family"
    if hasattr(result, "fallback_used"):
        assert getattr(result, "fallback_used") is False
    if hasattr(result, "generation_time_ms"):
        assert float(getattr(result, "generation_time_ms")) >= 0.0


@pytest.mark.asyncio
async def test_generate_text_english_uses_planner_first_runtime_end_to_end() -> None:
    frame = _english_bio_frame()
    planner = RecordingPlanner()
    resolver = RecordingLexicalResolver()
    realizer = RecordingFamilyRealizer()

    use_case = GenerateText(
        planner=planner,
        lexical_resolver=resolver,
        realizer=realizer,
        engine=None,
        allow_legacy_engine_fallback=False,
    )

    result = await use_case.execute("en", frame)

    _assert_runtime_result_contract(result)

    assert len(planner.calls) == 1
    assert planner.calls[0]["lang_code"] == "en"
    assert planner.calls[0]["frame_type"] == "bio"
    assert planner.calls[0]["subject_name"] == "Alan Turing"

    assert len(resolver.calls) == 1
    planned_sentence = resolver.calls[0]["planned_sentence"]
    construction_plan = resolver.calls[0]["construction_plan"]

    assert isinstance(planned_sentence, PlannedSentence)
    assert planned_sentence.construction_id == "copula_equative_classification"
    assert planned_sentence.lang_code == "en"

    assert isinstance(construction_plan, ConstructionPlan)
    assert construction_plan.construction_id == "copula_equative_classification"
    assert construction_plan.lang_code == "en"
    assert construction_plan.get_slot("subject")["label"] == "Alan Turing"
    assert construction_plan.lexical_bindings["profession"]["lemma"] == "mathematician"
    assert construction_plan.lexical_bindings["nationality"]["lemma"] == "British"

    assert len(realizer.calls) == 1
    realized_plan = realizer.calls[0]
    assert realized_plan.construction_id == "copula_equative_classification"
    assert realized_plan.lang_code == "en"
    assert realized_plan.lexical_bindings["profession"]["lemma"] == "mathematician"


@pytest.mark.asyncio
async def test_generate_text_english_prefers_planner_runtime_over_legacy_engine() -> None:
    frame = _english_bio_frame()
    planner = RecordingPlanner()
    resolver = RecordingLexicalResolver()
    realizer = RecordingFamilyRealizer()

    legacy_engine = MagicMock()
    legacy_engine.generate = AsyncMock(
        return_value=Sentence(
            text="This should never be used.",
            lang_code="en",
            debug_info={"runtime_path": "legacy_engine"},
            generation_time_ms=0.0,
        )
    )

    use_case = GenerateText(
        planner=planner,
        lexical_resolver=resolver,
        realizer=realizer,
        engine=legacy_engine,
        allow_legacy_engine_fallback=True,
    )

    result = await use_case.execute("en", frame)

    _assert_runtime_result_contract(result)

    legacy_engine.generate.assert_not_awaited()
    assert len(planner.calls) == 1
    assert len(resolver.calls) == 1
    assert len(realizer.calls) == 1


@pytest.mark.asyncio
async def test_generate_text_english_is_deterministic_and_does_not_share_plan_state() -> None:
    frame = _english_bio_frame()
    planner = RecordingPlanner()
    resolver = RecordingLexicalResolver()
    realizer = RecordingFamilyRealizer()

    use_case = GenerateText(
        planner=planner,
        lexical_resolver=resolver,
        realizer=realizer,
        engine=None,
        allow_legacy_engine_fallback=False,
    )

    first = await use_case.execute("en", frame)
    second = await use_case.execute("en", frame)

    _assert_runtime_result_contract(first)
    _assert_runtime_result_contract(second)

    assert first.text == second.text
    assert first.debug_info["construction_id"] == second.debug_info["construction_id"]
    assert first.debug_info["renderer_backend"] == second.debug_info["renderer_backend"]
    assert first.debug_info["runtime_path"] == second.debug_info["runtime_path"] == "planner_first"

    assert len(realizer.calls) == 2
    first_plan = realizer.calls[0]
    second_plan = realizer.calls[1]

    assert first_plan is not second_plan

    first_subject = first_plan.get_slot("subject")
    second_subject = second_plan.get_slot("subject")
    assert dict(first_subject) == dict(second_subject)

    try:
        first_subject["label"] = "Changed"
    except TypeError:
        pass

    assert second_plan.get_slot("subject")["label"] == "Alan Turing"
    assert first_plan.lexical_bindings["profession"]["lemma"] == "mathematician"
    assert second_plan.lexical_bindings["profession"]["lemma"] == "mathematician"


@pytest.mark.asyncio
async def test_generate_text_english_realizer_failure_is_explicit_without_hidden_success() -> None:
    frame = _english_bio_frame()
    planner = RecordingPlanner()
    resolver = RecordingLexicalResolver()
    realizer = FailingRealizer()

    use_case = GenerateText(
        planner=planner,
        lexical_resolver=resolver,
        realizer=realizer,
        engine=None,
        allow_legacy_engine_fallback=False,
    )

    with pytest.raises(DomainError) as excinfo:
        await use_case.execute("en", frame)

    assert "Unexpected generation failure" in str(excinfo.value)
    assert "realizer exploded" in str(excinfo.value)

    assert len(planner.calls) == 1
    assert len(resolver.calls) == 1
    assert len(realizer.calls) == 1
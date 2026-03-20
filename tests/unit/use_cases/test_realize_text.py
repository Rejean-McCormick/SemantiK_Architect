Use this updated version:

```python id="7j4q0z"
# tests/unit/use_cases/test_realize_text.py
from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.core.domain.exceptions import DomainError
from app.core.domain.models import SurfaceResult
from app.core.domain.planning.construction_plan import ConstructionPlan
from app.core.use_cases.realize_text import (
    ConstructionPlanError,
    LexicalResolutionError,
    RealizationError,
    RealizeText,
)


def make_plan(
    *,
    construction_id: str = "copula_equative_classification",
    lang_code: str = "en",
    slot_map: dict[str, object] | None = None,
    generation_options: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
) -> ConstructionPlan:
    return ConstructionPlan(
        construction_id=construction_id,
        lang_code=lang_code,
        slot_map=slot_map
        or {
            "subject": "Ada Lovelace",
            "predicate_nominal": "mathematician",
        },
        generation_options=generation_options or {},
        metadata=metadata or {},
    )


class StaticRealizer:
    def __init__(self, result: object, *, backend_name: str = "family") -> None:
        self.backend_name = backend_name
        self._result = result
        self.calls: list[object] = []

    async def realize(self, construction_plan: object) -> object:
        self.calls.append(construction_plan)
        if isinstance(self._result, BaseException):
            raise self._result
        return self._result


class FunctionalRealizer:
    def __init__(self, fn, *, backend_name: str = "family") -> None:
        self.backend_name = backend_name
        self._fn = fn
        self.calls: list[object] = []

    async def realize(self, construction_plan: object) -> object:
        self.calls.append(construction_plan)
        return self._fn(construction_plan, len(self.calls) - 1)


@dataclass
class ResolvedSlotMap:
    payload: dict[str, object]
    lexical_bindings: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return dict(self.payload)


class FakeResolver:
    def __init__(self, result: object) -> None:
        self._result = result
        self.calls: list[tuple[object, str]] = []

    async def resolve_slot_map(
        self,
        slot_map: object,
        *,
        lang_code: str,
        construction_id: str | None = None,
        generation_options: dict[str, object] | None = None,
    ) -> object:
        self.calls.append((slot_map, lang_code))
        if isinstance(self._result, BaseException):
            raise self._result
        return self._result


class ExpectedResolverDomainError(DomainError):
    pass


@pytest.mark.asyncio
async def test_execute_returns_normalized_surface_result_and_runtime_metadata():
    plan = make_plan()
    realizer = StaticRealizer(
        {
            "text": "Ada Lovelace is a mathematician.",
            "lang_code": "en",
            "renderer_backend": "family",
            "fallback_used": False,
            "debug_info": {"capability_tier": "full"},
            "generation_time_ms": 12.5,
        },
        backend_name="family",
    )

    result = await RealizeText(realizer).execute(plan)

    assert isinstance(result, SurfaceResult)
    assert result.text == "Ada Lovelace is a mathematician."
    assert result.lang_code == "en"
    assert result.construction_id == "copula_equative_classification"
    assert result.renderer_backend == "family"
    assert result.fallback_used is False
    assert list(result.tokens) == ["Ada", "Lovelace", "is", "a", "mathematician."]
    assert result.generation_time_ms == 12.5

    assert result.debug_info["construction_id"] == plan.construction_id
    assert result.debug_info["lang_code"] == "en"
    assert result.debug_info["renderer_backend"] == "family"
    assert result.debug_info["selected_backend"] == "family"
    assert result.debug_info["attempted_backends"] == ["family"]
    assert result.debug_info["fallback_used"] is False
    assert result.debug_info["capability_tier"] == "full"

    assert len(realizer.calls) == 1
    assert realizer.calls[0] is plan


@pytest.mark.asyncio
async def test_execute_derives_tokens_from_text_when_realizer_omits_them():
    plan = make_plan()
    realizer = StaticRealizer(
        {
            "text": "Ada Lovelace is a mathematician.",
            "lang_code": "en",
            "renderer_backend": "family",
            "fallback_used": False,
            "debug_info": {},
            "generation_time_ms": 3.0,
        },
        backend_name="family",
    )

    result = await RealizeText(realizer).execute(plan)

    assert list(result.tokens) == ["Ada", "Lovelace", "is", "a", "mathematician."]
    assert result.generation_time_ms == 3.0
    assert result.renderer_backend == "family"


@pytest.mark.asyncio
async def test_execute_applies_lexical_resolution_and_clones_plan_without_mutating_original():
    plan = make_plan(
        slot_map={
            "subject": "Alan Turing",
            "predicate_nominal": "mathematician",
        }
    )
    resolved_slot_map = ResolvedSlotMap(
        payload={
            "subject": "Alan Turing",
            "predicate_nominal": "mathematician",
        },
        lexical_bindings={
            "subject": {"kind": "entity", "id": "Q7251", "source": "wikidata"},
            "predicate_nominal": {
                "kind": "lexeme",
                "lemma": "mathematician",
                "source": "wikidata",
            },
        },
    )
    resolver = FakeResolver(resolved_slot_map)
    realizer = StaticRealizer(
        {
            "text": "Alan Turing is a mathematician.",
            "lang_code": "en",
            "renderer_backend": "gf",
            "fallback_used": False,
            "tokens": ["Alan", "Turing", "is", "a", "mathematician."],
            "debug_info": {},
            "generation_time_ms": 4.0,
        },
        backend_name="gf",
    )

    result = await RealizeText(realizer, resolver).execute(plan)

    assert len(realizer.calls) == 1
    realized_plan = realizer.calls[0]

    assert realized_plan is not plan
    assert dict(plan.lexical_bindings) == {}
    assert realized_plan.lexical_bindings["subject"]["id"] == "Q7251"
    assert realized_plan.lexical_bindings["predicate_nominal"]["lemma"] == "mathematician"

    assert result.renderer_backend == "gf"
    assert result.generation_time_ms == 4.0
    assert result.debug_info["lexical_resolution"]["applied"] is True
    assert result.debug_info["lexical_resolution"]["resolver"] == "FakeResolver"
    assert result.debug_info["renderer_backend"] == "gf"
    assert result.debug_info["selected_backend"] == "gf"
    assert result.debug_info["attempted_backends"] == ["gf"]


@pytest.mark.asyncio
async def test_execute_accepts_raw_string_result_and_infers_backend_name():
    plan = make_plan()
    realizer = StaticRealizer(
        "Ada Lovelace mathematician",
        backend_name="safe_mode",
    )

    result = await RealizeText(realizer).execute(plan)

    assert result.text == "Ada Lovelace mathematician"
    assert result.lang_code == "en"
    assert result.renderer_backend == "safe_mode"
    assert result.fallback_used is False
    assert list(result.tokens) == ["Ada", "Lovelace", "mathematician"]
    assert result.generation_time_ms == 0.0
    assert result.debug_info["renderer_backend"] == "safe_mode"
    assert result.debug_info["selected_backend"] == "safe_mode"
    assert result.debug_info["attempted_backends"] == ["safe_mode"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_plan",
    [
        None,
        {"construction_id": "copula_equative_classification", "lang_code": "en"},
        {"construction_id": "", "lang_code": "en", "slot_map": {}},
        {"construction_id": "copula_equative_classification", "lang_code": "", "slot_map": {}},
        {
            "construction_id": "copula_equative_classification",
            "lang_code": "en",
            "slot_map": None,
        },
    ],
)
async def test_execute_rejects_invalid_construction_plans(bad_plan):
    realizer = StaticRealizer({"text": "unused", "renderer_backend": "family"})

    with pytest.raises(ConstructionPlanError):
        await RealizeText(realizer).execute(bad_plan)


@pytest.mark.asyncio
async def test_execute_raises_lexical_resolution_error_when_resolver_crashes():
    plan = make_plan()
    resolver = FakeResolver(RuntimeError("resolver exploded"))
    realizer = StaticRealizer({"text": "unused", "renderer_backend": "family"})

    with pytest.raises(LexicalResolutionError, match="resolver exploded"):
        await RealizeText(realizer, resolver).execute(plan)

    assert realizer.calls == []


@pytest.mark.asyncio
async def test_execute_propagates_domain_errors_from_lexical_resolver():
    plan = make_plan()
    resolver = FakeResolver(ExpectedResolverDomainError("lexical miss"))
    realizer = StaticRealizer({"text": "unused", "renderer_backend": "family"})

    with pytest.raises(ExpectedResolverDomainError, match="lexical miss"):
        await RealizeText(realizer, resolver).execute(plan)

    assert realizer.calls == []


@pytest.mark.asyncio
async def test_execute_wraps_backend_failure_as_realization_error():
    plan = make_plan()
    realizer = StaticRealizer(RuntimeError("backend exploded"), backend_name="gf")

    with pytest.raises(RealizationError) as exc_info:
        await RealizeText(realizer).execute(plan)

    message = str(exc_info.value)
    assert "Could not realize construction" in message
    assert plan.construction_id in message
    assert plan.lang_code in message
    assert "backend exploded" in message


@pytest.mark.asyncio
async def test_execute_rejects_result_without_non_empty_text():
    plan = make_plan()
    realizer = StaticRealizer(
        {
            "text": "",
            "lang_code": "en",
            "renderer_backend": "family",
        },
        backend_name="family",
    )

    with pytest.raises(RealizationError, match="non-empty 'text' field"):
        await RealizeText(realizer).execute(plan)


@pytest.mark.asyncio
async def test_execute_preserves_explicit_generation_time_ms_from_realizer():
    plan = make_plan()
    realizer = StaticRealizer(
        {
            "text": "Ada Lovelace is a mathematician.",
            "lang_code": "en",
            "renderer_backend": "family",
            "fallback_used": False,
            "tokens": ["Ada", "Lovelace", "is", "a", "mathematician."],
            "debug_info": {"timings_ms": {"realization": 7.25}},
            "generation_time_ms": 7.25,
        },
        backend_name="family",
    )

    result = await RealizeText(realizer).execute(plan)

    assert result.generation_time_ms == 7.25
    assert result.debug_info["timings_ms"]["realization"] == 7.25


@pytest.mark.asyncio
async def test_execute_many_preserves_order_and_returns_one_surface_result_per_plan():
    plans = [
        make_plan(
            construction_id="copula_equative_classification",
            slot_map={"subject": "Ada Lovelace", "predicate_nominal": "mathematician"},
        ),
        make_plan(
            construction_id="copula_equative_classification",
            slot_map={"subject": "Grace Hopper", "predicate_nominal": "computer scientist"},
        ),
    ]

    def realize_for_plan(plan: ConstructionPlan, _index: int) -> dict[str, object]:
        return {
            "text": f"{plan.slot_map['subject']} realized",
            "lang_code": "en",
            "renderer_backend": "family",
            "fallback_used": False,
            "tokens": [str(plan.slot_map["subject"]), "realized"],
            "debug_info": {},
            "generation_time_ms": 1.0,
        }

    realizer = FunctionalRealizer(realize_for_plan, backend_name="family")
    results = await RealizeText(realizer).execute_many(plans)

    assert [result.text for result in results] == [
        "Ada Lovelace realized",
        "Grace Hopper realized",
    ]
    assert [result.construction_id for result in results] == [
        "copula_equative_classification",
        "copula_equative_classification",
    ]
    assert [result.renderer_backend for result in results] == ["family", "family"]
    assert [call.slot_map["subject"] for call in realizer.calls] == [
        "Ada Lovelace",
        "Grace Hopper",
    ]


@pytest.mark.asyncio
async def test_execute_many_wraps_non_domain_failures_with_index_context():
    plans = [
        make_plan(slot_map={"subject": "Ada Lovelace", "predicate_nominal": "mathematician"}),
        make_plan(slot_map={"subject": "Grace Hopper", "predicate_nominal": "computer scientist"}),
    ]

    def flaky_realizer(plan: ConstructionPlan, index: int) -> dict[str, object]:
        if index == 1:
            raise RuntimeError("second call exploded")
        return {
            "text": f"{plan.slot_map['subject']} realized",
            "lang_code": "en",
            "renderer_backend": "family",
            "fallback_used": False,
            "tokens": [str(plan.slot_map["subject"]), "realized"],
            "debug_info": {},
            "generation_time_ms": 1.0,
        }

    realizer = FunctionalRealizer(flaky_realizer, backend_name="family")

    with pytest.raises(RealizationError, match="index 1"):
        await RealizeText(realizer).execute_many(plans)
```

What changed for consistency with the final contract:

* `lang_code` uses `en` instead of `eng`
* `SurfaceResult` remains the canonical result target
* `generation_time_ms` is asserted as a first-class runtime field
* `tokens` are always asserted on successful normalized results
* lexical-resolution and backend debug fields stay aligned with the current `RealizeText` normalization behavior
* the tests no longer encode the older looser runtime assumptions

One important note: this test file assumes `RealizeText` will preserve `generation_time_ms` when normalizing results. In the current dump, that part is not fully wired yet, so this is the **target final test file** for the code you’re about to bring into alignment.


# tests/http_api/test_generate.py
from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.adapters.api.dependencies import get_generate_text_use_case
from app.adapters.api.main import create_app
from app.core.domain.exceptions import LanguageNotFoundError
from app.core.domain.models import SurfaceResult

API_PREFIX = "/api/v1"
AUTH_HEADERS = {"X-API-Key": "dev-api-key"}


class StubGenerateTextUseCase:
    """
    Async test double for the GenerateText use case.

    It records calls so tests can verify request normalization, and can return
    either a SurfaceResult-compatible value or raise an exception.
    """

    def __init__(self, result: Any):
        self.result = result
        self.calls: list[tuple[str, Any]] = []

    async def execute(self, lang_code: str, frame: Any) -> Any:
        self.calls.append((lang_code, frame))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture
def client_factory():
    @contextmanager
    def _make(use_case: Any):
        app = create_app()
        app.dependency_overrides[get_generate_text_use_case] = lambda: use_case
        try:
            with TestClient(app) as client:
                yield client
        finally:
            app.dependency_overrides.clear()

    return _make


def test_generate_success_path_language_preserves_public_shape_and_runtime_metadata(
    client_factory,
):
    use_case = StubGenerateTextUseCase(
        SurfaceResult(
            text="Marie Curie is a Polish physicist.",
            lang_code="en",
            construction_id="copula_equative_classification",
            renderer_backend="family",
            fallback_used=False,
            tokens=["Marie", "Curie", "is", "a", "Polish", "physicist."],
            debug_info={
                "runtime_path": "planner_first",
                "slot_keys": ["subject", "profession", "nationality"],
                "selected_backend": "family",
                "attempted_backends": ["family"],
            },
            generation_time_ms=12.5,
        )
    )

    # Flat compatibility payload: request mapper should normalize this to a
    # canonical bio/person frame before it reaches the use case.
    payload = {
        "frame_type": "entity.person",
        "name": "Marie Curie",
        "profession": "physicist",
        "nationality": "Polish",
        "qid": "Q7186",
    }

    with client_factory(use_case) as client:
        response = client.post(
            f"{API_PREFIX}/generate/en",
            json=payload,
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 200
    data = response.json()

    assert data["text"] == "Marie Curie is a Polish physicist."
    assert data["lang_code"] == "en"
    assert data["construction_id"] == "copula_equative_classification"
    assert data["renderer_backend"] == "family"
    assert data["fallback_used"] is False
    assert data["tokens"] == ["Marie", "Curie", "is", "a", "Polish", "physicist."]
    assert data["generation_time_ms"] == 12.5

    assert "debug_info" in data
    assert data["debug_info"]["runtime_path"] == "planner_first"
    assert data["debug_info"]["construction_id"] == "copula_equative_classification"
    assert data["debug_info"]["renderer_backend"] == "family"
    assert data["debug_info"]["fallback_used"] is False
    assert data["debug_info"]["lang_code"] == "en"
    assert data["debug_info"]["tokens"] == [
        "Marie",
        "Curie",
        "is",
        "a",
        "Polish",
        "physicist.",
    ]
    assert data["debug_info"]["generation_time_ms"] == 12.5
    assert data["debug_info"]["slot_keys"] == ["subject", "profession", "nationality"]
    assert data["debug_info"]["selected_backend"] == "family"
    assert data["debug_info"]["attempted_backends"] == ["family"]

    assert len(use_case.calls) == 1
    lang_code, frame = use_case.calls[0]
    assert lang_code == "en"
    assert getattr(frame, "frame_type", None) == "bio"
    assert getattr(frame, "subject", {})["name"] == "Marie Curie"
    assert getattr(frame, "subject", {})["qid"] == "Q7186"


def test_generate_success_language_inside_payload_uses_payload_route(client_factory):
    use_case = StubGenerateTextUseCase(
        SurfaceResult(
            text="Marie Curie est une physicienne polonaise.",
            lang_code="fr",
            construction_id="copula_equative_classification",
            renderer_backend="gf",
            fallback_used=False,
            tokens=["Marie", "Curie", "est", "une", "physicienne", "polonaise."],
            debug_info={
                "runtime_path": "planner_first",
                "slot_keys": ["subject", "profession", "nationality"],
                "selected_backend": "gf",
                "attempted_backends": ["gf"],
                "resolved_language": "WikiFre",
            },
            generation_time_ms=9.0,
        )
    )

    payload = {
        "lang": "fr",
        "frame_type": "bio",
        "subject": {"name": "Marie Curie", "qid": "Q7186"},
        "profession": "physicienne",
        "nationality": "polonaise",
    }

    with client_factory(use_case) as client:
        response = client.post(
            f"{API_PREFIX}/generate",
            json=payload,
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 200
    data = response.json()

    assert data["text"] == "Marie Curie est une physicienne polonaise."
    assert data["lang_code"] == "fr"
    assert data["construction_id"] == "copula_equative_classification"
    assert data["renderer_backend"] == "gf"
    assert data["fallback_used"] is False
    assert data["tokens"] == [
        "Marie",
        "Curie",
        "est",
        "une",
        "physicienne",
        "polonaise.",
    ]
    assert data["generation_time_ms"] == 9.0

    assert data["debug_info"]["runtime_path"] == "planner_first"
    assert data["debug_info"]["construction_id"] == "copula_equative_classification"
    assert data["debug_info"]["renderer_backend"] == "gf"
    assert data["debug_info"]["fallback_used"] is False
    assert data["debug_info"]["lang_code"] == "fr"
    assert data["debug_info"]["tokens"] == [
        "Marie",
        "Curie",
        "est",
        "une",
        "physicienne",
        "polonaise.",
    ]
    assert data["debug_info"]["generation_time_ms"] == 9.0
    assert data["debug_info"]["slot_keys"] == ["subject", "profession", "nationality"]
    assert data["debug_info"]["selected_backend"] == "gf"
    assert data["debug_info"]["attempted_backends"] == ["gf"]
    assert data["debug_info"]["resolved_language"] == "WikiFre"

    assert len(use_case.calls) == 1
    lang_code, frame = use_case.calls[0]
    assert lang_code == "fr"
    assert getattr(frame, "frame_type", None) == "bio"
    assert getattr(frame, "subject", {})["name"] == "Marie Curie"


def test_generate_payload_route_requires_language_when_not_in_path(client_factory):
    use_case = StubGenerateTextUseCase(
        SurfaceResult(
            text="unused",
            lang_code="en",
            construction_id="copula_equative_classification",
            renderer_backend="family",
            fallback_used=False,
            tokens=["unused"],
            debug_info={"runtime_path": "planner_first"},
            generation_time_ms=0.0,
        )
    )

    payload = {
        "frame_type": "bio",
        "subject": {"name": "Marie Curie", "qid": "Q7186"},
    }

    with client_factory(use_case) as client:
        response = client.post(
            f"{API_PREFIX}/generate",
            json=payload,
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 422
    assert "Missing language" in response.json()["detail"]
    assert use_case.calls == []


def test_generate_validation_error_missing_frame_type_returns_422(client_factory):
    use_case = StubGenerateTextUseCase(
        SurfaceResult(
            text="unused",
            lang_code="en",
            construction_id="copula_equative_classification",
            renderer_backend="family",
            fallback_used=False,
            tokens=["unused"],
            debug_info={"runtime_path": "planner_first"},
            generation_time_ms=0.0,
        )
    )

    payload = {
        "subject": {"name": "Marie Curie", "qid": "Q7186"},
    }

    with client_factory(use_case) as client:
        response = client.post(
            f"{API_PREFIX}/generate/en",
            json=payload,
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 422
    assert "frame_type" in response.json()["detail"]
    assert use_case.calls == []


def test_generate_validation_error_language_mismatch_between_url_and_payload(client_factory):
    use_case = StubGenerateTextUseCase(
        SurfaceResult(
            text="unused",
            lang_code="en",
            construction_id="copula_equative_classification",
            renderer_backend="family",
            fallback_used=False,
            tokens=["unused"],
            debug_info={"runtime_path": "planner_first"},
            generation_time_ms=0.0,
        )
    )

    payload = {
        "lang": "fr",
        "frame_type": "bio",
        "subject": {"name": "Marie Curie", "qid": "Q7186"},
    }

    with client_factory(use_case) as client:
        response = client.post(
            f"{API_PREFIX}/generate/en",
            json=payload,
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 422
    assert "Language mismatch" in response.json()["detail"]
    assert use_case.calls == []


def test_generate_returns_404_when_use_case_reports_unknown_language(client_factory):
    use_case = StubGenerateTextUseCase(LanguageNotFoundError("zzz"))

    payload = {
        "frame_type": "bio",
        "subject": {"name": "Marie Curie", "qid": "Q7186"},
    }

    with client_factory(use_case) as client:
        response = client.post(
            f"{API_PREFIX}/generate/zzz",
            json=payload,
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 404
    assert "zzz" in response.json()["detail"]


def test_generate_returns_422_when_result_cannot_be_mapped_to_public_response(client_factory):
    class BrokenGenerateTextUseCase:
        async def execute(self, lang_code: str, frame: Any) -> Any:
            # Missing required public field "text"; response mapper must reject it.
            return {
                "lang_code": lang_code,
                "construction_id": "copula_equative_classification",
                "renderer_backend": "family",
                "fallback_used": False,
                "tokens": ["broken"],
                "debug_info": {"runtime_path": "planner_first"},
                "generation_time_ms": 1.0,
            }

    payload = {
        "frame_type": "bio",
        "subject": {"name": "Marie Curie", "qid": "Q7186"},
    }

    with client_factory(BrokenGenerateTextUseCase()) as client:
        response = client.post(
            f"{API_PREFIX}/generate/en",
            json=payload,
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 422
    assert "text" in response.json()["detail"]

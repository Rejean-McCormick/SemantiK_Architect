# tests/http_api/test_ai.py
import pytest
from fastapi.testclient import TestClient

# FIX: Import from the correct v2.1 application factory
from app.adapters.api.main import create_app

# FIX: Standardize API Prefix
API_PREFIX = "/api/v1"

@pytest.fixture
def client():
    """
    Fixture to create a fresh TestClient for each test.
    """
    app = create_app()
    with TestClient(app) as c:
        yield c

def test_ai_suggestions_basic(client: TestClient) -> None:
    """
    Smoke test for the AI suggestions endpoint.

    Ensures:
    - Endpoint is reachable.
    - Response is 200 OK.
    - Payload has the expected top-level shape.
    """
    payload = {
        "utterance": "Write a short biography of Marie Curie.",
        "lang": "en",
    }

    # Updated URL to include v1 prefix
    response = client.post(f"{API_PREFIX}/ai/suggestions", json=payload)
    
    # Check if the route is actually mounted (Common issue during refactors)
    if response.status_code == 404:
        pytest.fail(f"Endpoint {API_PREFIX}/ai/suggestions not found. Is the AI router mounted in main.py?")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, dict)
    assert "suggestions" in data

    suggestions = data["suggestions"]
    assert isinstance(suggestions, list)
    assert len(suggestions) > 0

    first = suggestions[0]
    # Minimal contract for one suggestion item
    assert isinstance(first, dict)
    assert "frame_type" in first
    assert "title" in first
    assert "description" in first
    # confidence is optional but recommended
    if "confidence" in first:
        assert isinstance(first["confidence"], (int, float))


def test_ai_suggestions_requires_utterance(client: TestClient) -> None:
    """
    The endpoint should validate input and reject requests without `utterance`.
    """
    payload = {
        "lang": "en"
    }

    response = client.post(f"{API_PREFIX}/ai/suggestions", json=payload)
    
    # If endpoint is missing, skip this test to avoid double reporting failures
    if response.status_code == 404:
        pytest.skip("AI Endpoint not mounted")

    # FastAPI / Pydantic validation error
    assert response.status_code == 422


def test_ai_suggestions_defaults_lang(client: TestClient) -> None:
    """
    Lang should be optional; omitting it should still return a valid response.
    """
    payload = {
        "utterance": "Generate something about a historical figure."
    }

    response = client.post(f"{API_PREFIX}/ai/suggestions", json=payload)
    
    if response.status_code == 404:
        pytest.skip("AI Endpoint not mounted")

    assert response.status_code == 200

    data = response.json()
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)
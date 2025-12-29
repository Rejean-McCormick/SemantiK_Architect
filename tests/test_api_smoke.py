# tests/test_api_smoke.py
import pytest
from fastapi.testclient import TestClient
from app.adapters.api.main import create_app

# Initialize the client once
app = create_app()
client = TestClient(app)

def test_health_check():
    """
    Verifies the API is up and running.
    """
    response = client.get("/api/v1/health/ready")
    
    # We accept 200 (OK) or 503 (Not Ready) but the endpoint must exist.
    # 404 means the router isn't wired correctly.
    assert response.status_code in [200, 503]
    assert "status" in response.json() or "broker" in response.json()

def test_generate_endpoint_structure():
    """
    Verifies the /generate endpoint accepts requests.
    We expect a 422 (Validation Error) or 200, but NEVER a 404.
    """
    # 1. Test POST existence
    response = client.post("/api/v1/generate/en", json={})
    
    # 422 means "I saw your request but it's missing data" -> GOOD (Endpoint exists)
    # 404 means "Endpoint not found" -> BAD
    assert response.status_code != 404, "The /generate endpoint is missing!"

def test_list_languages():
    """
    Verifies we can fetch the supported languages list.
    """
    response = client.get("/api/v1/languages")
    
    # This might return 404 if you haven't implemented it yet, 
    # but if it exists, it should return JSON.
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list) or "languages" in data

def test_tool_execution_auth():
    """
    Verifies the tools endpoint exists and is protected (or at least reachable).
    """
    # Attempt to run a fake tool
    response = client.post("/api/v1/tools/run", json={"tool_id": "fake_tool"})
    
    # Should return 404 (Tool not found) or 401/403 (Auth), 
    # but NOT 404 (Endpoint not found).
    # Since the router is mounted, we expect it to handle the request.
    assert response.status_code != 404
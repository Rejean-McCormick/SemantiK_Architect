# tests/http_api/test_entities.py
from fastapi.routing import APIRoute

# FIX: Import from the correct v2.1 application factory location
from app.adapters.api.main import create_app

# Instantiate the app to inspect its routes
app = create_app()

# FIX: V2.1 API Prefix Standard
API_PREFIX = "/api/v1/entities"

def _get_api_routes() -> list[APIRoute]:
    """Return only FastAPI APIRoute objects (ignore static/docs/etc.)."""
    return [r for r in app.routes if isinstance(r, APIRoute)]


def test_entities_routes_registered_under_api_prefix() -> None:
    """
    The entities router must expose at least one route under /api/v1/entities.
    This ensures the router is included in app.adapters.api.main.
    """
    routes = _get_api_routes()
    
    # We look for routes that start with the correct v2.1 prefix
    entities_paths = {r.path for r in routes if r.path.startswith(API_PREFIX)}

    assert entities_paths, f"Expected at least one route under {API_PREFIX} to be registered."


def test_entities_routes_are_tagged_entities() -> None:
    """
    All /api/v1/entities routes should be tagged with 'Entities' so they are easy
    to discover in OpenAPI / docs and for tooling.
    """
    routes = _get_api_routes()
    entities_routes = [r for r in routes if r.path.startswith(API_PREFIX)]

    # If this fails, the first test will already have pointed out missing routes.
    assert entities_routes, f"No routes found under {API_PREFIX} to check tags."

    for route in entities_routes:
        # Note: In main.py, the tag is capitalized as "Entities"
        assert (
            "Entities" in route.tags or "entities" in route.tags
        ), f"Route {route.path} is missing the 'Entities' tag. Found: {route.tags}"
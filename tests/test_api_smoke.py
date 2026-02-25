# tests/test_api_smoke.py
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.routing import Mount, Router

from app.adapters.api.main import create_app

app = create_app()
client = TestClient(app)

# The backend API prefix (as mounted inside FastAPI)
API_PREFIX = "/api/v1"


def _is_route_missing(resp) -> bool:
    """
    Distinguish FastAPI's default 404 (route not mounted) from app-level 404s.
    """
    if resp.status_code != 404:
        return False
    try:
        data = resp.json()
    except Exception:
        # Non-JSON 404 is usually framework-level; treat as missing.
        return True
    return isinstance(data, dict) and data.get("detail") == "Not Found"


def _default_generate_payload() -> Dict[str, Any]:
    # v2.5 schema compliance: subject is an object (name + qid), not a string
    return {
        "frame_type": "bio",
        "subject": {"name": "Alan Turing", "qid": "Q7251"},
        "properties": {"occupation": "Mathematician"},
    }


def _extract_language_codes(data: Any) -> List[str]:
    """
    Accepts multiple shapes:
      - ["en", "fr", ...]
      - [{"code": "en"}, ...]
      - {"languages": ["en", ...]} or {"languages": [{"code":"en"}, ...]}
      - {"supported_languages": ["en", ...]}
    Returns normalized list of string codes.
    """
    out: List[str] = []

    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict) and item.get("code"):
                out.append(str(item["code"]))
        return out

    if isinstance(data, dict):
        if isinstance(data.get("supported_languages"), list):
            for x in data["supported_languages"]:
                out.append(str(x))
            return out

        langs = data.get("languages")
        if isinstance(langs, list):
            for item in langs:
                if isinstance(item, str):
                    out.append(item)
                elif isinstance(item, dict) and item.get("code"):
                    out.append(str(item["code"]))
            return out

    return out


def _get_languages_if_accessible() -> Optional[List[str]]:
    """
    Returns language codes if /languages is reachable and returns 200.
    Returns None if unauthorized/forbidden or missing.
    """
    for path in (f"{API_PREFIX}/languages", f"{API_PREFIX}/languages/"):
        resp = client.get(path)
        if _is_route_missing(resp):
            continue
        if resp.status_code in (401, 403):
            return None
        if resp.status_code == 200:
            try:
                data = resp.json()
            except Exception:
                return []
            return _extract_language_codes(data)
    return None


def _pick_language_code(candidates: Sequence[str]) -> str:
    """
    Prefer 2-letter codes if present, else first candidate.
    """
    for c in candidates:
        cs = (c or "").strip()
        if len(cs) == 2 and cs.isalpha():
            return cs.lower()
    for c in candidates:
        cs = (c or "").strip()
        if cs:
            return cs.lower()
    return "en"


# -------------------------
# Core backend smoke tests
# -------------------------


def test_health_check_ready_exists():
    resp = client.get(f"{API_PREFIX}/health/ready")
    assert not _is_route_missing(resp), "The /health/ready endpoint is missing!"
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert isinstance(data, dict)


def test_health_check_live_exists():
    resp = client.get(f"{API_PREFIX}/health/live")
    assert not _is_route_missing(resp), "The /health/live endpoint is missing!"
    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, dict)
        assert data.get("status") in ("ok", "ready", "degraded", None)


def test_list_languages_exists():
    resp = client.get(f"{API_PREFIX}/languages")
    if _is_route_missing(resp):
        resp = client.get(f"{API_PREFIX}/languages/")

    assert not _is_route_missing(resp), "The /languages endpoint is missing!"
    assert resp.status_code in (200, 401, 403), f"Unexpected status: {resp.status_code}"

    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, list) or (
            isinstance(data, dict) and ("languages" in data or "supported_languages" in data)
        )


def test_generate_endpoint_structure_exists():
    """
    Smoke-check that a generate endpoint is mounted and doesn't 500.

    Acceptable:
      - 200 (success)
      - 400 (bad request / unsupported language / app-level validation)
      - 401/403 (auth)
      - 404 (app-level "unknown language") BUT not FastAPI default 404
      - 422 (request validation)
    Checks both new and legacy variants.
    """
    payload = _default_generate_payload()

    langs = _get_languages_if_accessible()
    candidate_langs: List[str] = []
    if langs:
        candidate_langs.extend(langs)
    candidate_langs.extend(["en", "eng"])

    lang_code = _pick_language_code(candidate_langs)

    # New style: /generate/{lang_code}
    resp = client.post(f"{API_PREFIX}/generate/{lang_code}", json=payload)

    # If the new style isn't mounted, try legacy style: /generate
    if _is_route_missing(resp):
        resp = client.post(f"{API_PREFIX}/generate", json=payload)

    assert not _is_route_missing(resp), "No generate endpoint is mounted!"
    assert resp.status_code != 500, "Generate endpoint is mounted but crashing."
    assert resp.status_code in (200, 400, 401, 403, 404, 422), f"Unexpected status: {resp.status_code}"

    if resp.status_code == 404:
        data = resp.json()
        assert isinstance(data, dict)
        assert data.get("detail") and data.get("detail") != "Not Found"


def test_tools_run_exists_and_is_not_default_404():
    resp = client.post(f"{API_PREFIX}/tools/run", json={"tool_id": "fake_tool", "args": {}})
    assert not _is_route_missing(resp), "The /tools/run endpoint is missing!"
    assert resp.status_code != 500, "Tools endpoint is mounted but crashing."
    assert resp.status_code in (200, 400, 401, 403, 404, 422), f"Unexpected status: {resp.status_code}"

    if resp.status_code == 404:
        data = resp.json()
        assert isinstance(data, dict)
        assert data.get("detail") and data.get("detail") != "Not Found"


# ------------------------------------------------------------
# NEW: Guardrail for the GUI "Dynamic Test Bench" request catalog
# ------------------------------------------------------------


def _repo_root() -> Path:
    # tests/ is typically at repo_root/tests
    return Path(__file__).resolve().parents[1]


def _normalize_path(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        raw = urlparse(raw).path
    raw = raw.split("?", 1)[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    return raw


def _detect_frontend_base_path(repo: Path) -> str:
    """
    Best-effort: read Next.js basePath from next.config.* or env var.
    If we can detect it, we can catch the exact class of bug:
    requests using '/api/v1/...' instead of '{basePath}/api/v1/...'.
    """
    env_bp = (os.getenv("NEXT_PUBLIC_BASE_PATH") or os.getenv("BASE_PATH") or "").strip()
    if env_bp and env_bp != "/":
        return env_bp if env_bp.startswith("/") else "/" + env_bp

    cfg_candidates = [
        repo / "architect_frontend" / "next.config.js",
        repo / "architect_frontend" / "next.config.mjs",
        repo / "architect_frontend" / "next.config.cjs",
        repo / "architect_frontend" / "next.config.ts",
    ]
    for cfg in cfg_candidates:
        if not cfg.exists():
            continue
        try:
            text = cfg.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # e.g., basePath: "/abstract_wiki_architect"
        m = re.search(r"basePath\s*:\s*['\"](/[^'\"]*)['\"]", text)
        if m:
            bp = m.group(1).strip()
            if bp and bp != "/":
                return bp
    return ""


def _frontend_requests_dir(repo: Path) -> Path:
    return repo / "architect_frontend" / "src" / "data" / "requests"


def _extract_request_objects(payload: Any) -> List[Dict[str, Any]]:
    """
    The request catalog format can vary; accept:
      - single object
      - list of objects
      - {"requests": [...]} or {"items":[...]}
    """
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for k in ("requests", "items", "data"):
            v = payload.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
        return [payload]
    return []


def _get_req_method(req: Dict[str, Any]) -> str:
    for k in ("method", "http_method", "httpMethod"):
        v = req.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip().upper()
    return "POST"


def _get_req_path(req: Dict[str, Any]) -> str:
    for k in ("path", "url", "endpoint", "route"):
        v = req.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _collect_route_matchers() -> List[Tuple[re.Pattern, set]]:
    """
    Build regex matchers for backend routes so we can validate that the
    GUI request catalog points to real endpoints.
    """
    matchers: List[Tuple[re.Pattern, set]] = []

    def add_route(path: str, methods: Optional[Iterable[str]]) -> None:
        parts = []
        for seg in path.strip("/").split("/"):
            if seg.startswith("{") and seg.endswith("}"):
                parts.append(r"[^/]+")
            else:
                parts.append(re.escape(seg))
        pat = r"^/" + "/".join(parts) + r"/?$"
        matchers.append((re.compile(pat), set(methods or [])))

    def walk(router_obj: Any, prefix: str = "") -> None:
        routes = getattr(router_obj, "routes", None)
        if not routes:
            return
        for r in routes:
            if isinstance(r, APIRoute):
                add_route(prefix + r.path, r.methods)
            elif isinstance(r, Mount):
                # Join mount prefix with subroutes
                mp = prefix + (r.path or "")
                for sub in getattr(r, "routes", []) or []:
                    if isinstance(sub, APIRoute):
                        add_route(mp + sub.path, sub.methods)
                    elif isinstance(sub, Router):
                        walk(sub, mp)
            elif isinstance(r, Router):
                walk(r, prefix)

    walk(app, "")
    return matchers


def _matches_backend_route(path: str, method: str, matchers: List[Tuple[re.Pattern, set]]) -> bool:
    for pat, methods in matchers:
        if pat.match(path):
            if not methods:
                return True
            # HEAD often allowed implicitly when GET exists
            if method == "HEAD" and "GET" in methods:
                return True
            return method in methods
    return False


def test_dynamic_test_bench_request_catalog_points_to_real_routes():
    """
    This is the test that catches your current bug class:

    If architect_frontend/src/data/requests/*.json contains paths that don't
    correspond to backend routes, the GUI will hit FastAPI's default 404
    ("detail":"Not Found"). This test fails in that case.

    It also (best-effort) enforces Next.js basePath if detectable, so we catch:
      '/api/v1/...'  (WRONG under basePath)
      '/abstract_wiki_architect/api/v1/...' (RIGHT)
    """
    repo = _repo_root()
    req_dir = _frontend_requests_dir(repo)
    if not req_dir.exists():
        pytest.skip(f"No frontend request catalog found at {req_dir}")

    base_path = _detect_frontend_base_path(repo)  # "" if not detectable
    matchers = _collect_route_matchers()

    failures: List[str] = []
    basepath_failures: List[str] = []

    for jf in sorted(req_dir.glob("*.json")):
        try:
            payload = json.loads(jf.read_text(encoding="utf-8"))
        except Exception as e:
            failures.append(f"{jf}: invalid JSON ({e})")
            continue

        for req in _extract_request_objects(payload):
            method = _get_req_method(req)
            raw_path = _get_req_path(req)
            path = _normalize_path(raw_path)

            if not path:
                continue

            # Skip obvious non-backend/UI paths if they ever appear
            if path.startswith("/_next") or path.startswith("/static"):
                continue

            # If we can detect a Next.js basePath, enforce that request paths include it.
            if base_path and not path.startswith(base_path + "/") and path.startswith("/api"):
                basepath_failures.append(f"{jf}: {method} {path} (expected to start with {base_path}/...)")

            # Validate against backend route table:
            # Strip basePath if present before matching FastAPI routes.
            match_path = path
            if base_path and match_path.startswith(base_path + "/"):
                match_path = match_path[len(base_path) :]

            if not _matches_backend_route(match_path, method, matchers):
                failures.append(f"{jf}: {method} {path}")

    msgs: List[str] = []
    if basepath_failures:
        msgs.append(
            "Some request paths look like they ignore the Next.js basePath (GUI will 404):\n"
            + "\n".join(basepath_failures)
        )
    if failures:
        msgs.append(
            "Some Dynamic Test Bench request definitions do not match any backend route:\n"
            + "\n".join(failures)
        )

    assert not msgs, "\n\n".join(msgs)

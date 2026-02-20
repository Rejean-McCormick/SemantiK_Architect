# tools/language_health/api_runtime.py
"""
Runtime audit (Architect API) for language health checks.

What it does:
  - Discovers supported languages from the Architect API
  - POSTs a small test frame to /generate/{lang} (or /api/v1/generate/{lang})
  - Returns RuntimeResult objects with timing + error context

Design notes:
  - Uses `requests` if available, otherwise falls back to urllib
  - Supports trace ID propagation via header: x-trace-id
  - Avoids leaking API keys (caller should redact in logs)
  - Requests text/plain output (server may still return JSON containing surface_text/meta)
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Tuple

from .models import RuntimeResult


class ArchitectApiRuntimeChecker:
    """
    Notes:
      - timeout_s applies per request; default is higher because first request
        may trigger GF/PGF loading.
      - Supports either X-API-Key or Bearer auth.
    """

    def __init__(
        self,
        api_url: str,
        api_key: Optional[str] = None,
        timeout_s: int = 180,
        trace_id: Optional[str] = None,
        bearer_token: Optional[str] = None,
    ):
        self.api_url = (api_url or "").rstrip("/")
        self.api_key = api_key
        self.bearer_token = bearer_token
        self.timeout_s = int(timeout_s) if timeout_s else 180
        self.trace_id = trace_id

        self._requests = None
        self._session = None
        try:
            import requests  # type: ignore

            self._requests = requests
            self._session = requests.Session()
        except Exception:
            self._requests = None
            self._session = None

        self._languages_endpoint: Optional[str] = None
        self._generate_prefix: Optional[str] = None

    def _headers(self) -> Dict[str, str]:
        # Default output mode is "text/plain" (often still returned as JSON with surface_text + meta).
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "text/plain",
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        if self.trace_id:
            headers["x-trace-id"] = self.trace_id
        return headers

    def _http_get_json(self, url: str) -> Tuple[int, Any, str]:
        # returns: (http_status, parsed_json_or_none, raw_text)
        if self._session:
            try:
                resp = self._session.get(url, headers=self._headers(), timeout=self.timeout_s)
                raw = resp.text
                try:
                    return resp.status_code, resp.json(), raw
                except Exception:
                    return resp.status_code, None, raw
            except Exception as e:
                return 0, None, str(e)

        import urllib.error
        import urllib.request

        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                status = getattr(resp, "status", 200)
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    return status, json.loads(raw), raw
                except Exception:
                    return status, None, raw
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
            return e.code, None, raw
        except Exception as e:
            return 0, None, str(e)

    def _http_post_json(self, url: str, payload: Any) -> Tuple[int, Any, str, float]:
        # returns: (http_status, parsed_json_or_none, raw_text, duration_ms)
        start = time.time()

        if self._session:
            try:
                resp = self._session.post(url, headers=self._headers(), json=payload, timeout=self.timeout_s)
                dur_ms = (time.time() - start) * 1000
                raw = resp.text
                try:
                    return resp.status_code, resp.json(), raw, dur_ms
                except Exception:
                    return resp.status_code, None, raw, dur_ms
            except Exception as e:
                dur_ms = (time.time() - start) * 1000
                return 0, None, str(e), dur_ms

        import urllib.error
        import urllib.request

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                dur_ms = (time.time() - start) * 1000
                status = getattr(resp, "status", 200)
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    return status, json.loads(raw), raw, dur_ms
                except Exception:
                    return status, None, raw, dur_ms
        except urllib.error.HTTPError as e:
            dur_ms = (time.time() - start) * 1000
            raw = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
            return e.code, None, raw, dur_ms
        except Exception as e:
            dur_ms = (time.time() - start) * 1000
            return 0, None, str(e), dur_ms

    def _discover_endpoints(self) -> None:
        """
        Discover languages endpoint + generate prefix.

        We try common layouts and accept the first that returns 200 + JSON.
        If /info or /health is used as the probe, we still try to pick the best
        (api/v1 preferred; otherwise unversioned).
        """
        if not self.api_url:
            self.api_url = "http://localhost:8000"

        candidates = [
            # versioned
            (f"{self.api_url}/api/v1/languages", f"{self.api_url}/api/v1/generate"),
            # unversioned
            (f"{self.api_url}/languages", f"{self.api_url}/generate"),
            # reachability probes
            (f"{self.api_url}/info", f"{self.api_url}/generate"),
            (f"{self.api_url}/health", f"{self.api_url}/generate"),
        ]

        for lang_url, gen_prefix in candidates:
            status, data, _raw = self._http_get_json(lang_url)
            if status == 200 and data is not None:
                # If we probed /info or /health, prefer a real languages endpoint if available.
                if lang_url.endswith("/info") or lang_url.endswith("/health"):
                    st2, data2, _ = self._http_get_json(f"{self.api_url}/api/v1/languages")
                    if st2 == 200 and data2 is not None:
                        self._languages_endpoint = f"{self.api_url}/api/v1/languages"
                        self._generate_prefix = f"{self.api_url}/api/v1/generate"
                        return
                    st3, data3, _ = self._http_get_json(f"{self.api_url}/languages")
                    if st3 == 200 and data3 is not None:
                        self._languages_endpoint = f"{self.api_url}/languages"
                        self._generate_prefix = f"{self.api_url}/generate"
                        return

                self._languages_endpoint = lang_url
                self._generate_prefix = gen_prefix
                return

        # fallback defaults (even if probe fails, keep consistent paths)
        self._languages_endpoint = f"{self.api_url}/api/v1/languages"
        self._generate_prefix = f"{self.api_url}/api/v1/generate"

    def discover_languages(self) -> List[str]:
        """
        Attempts to read supported languages from the API.

        Supports shapes like:
          - {"supported_languages": ["en","fr",...]}
          - {"languages": [{"code":"en"}, ...]}
          - [{"code":"en"}, ...]
          - ["en","fr",...]
        """
        if not self._languages_endpoint:
            self._discover_endpoints()

        assert self._languages_endpoint is not None
        status, data, _raw = self._http_get_json(self._languages_endpoint)
        if status != 200 or data is None:
            return []

        if isinstance(data, dict):
            if isinstance(data.get("supported_languages"), list):
                return [str(x) for x in data["supported_languages"]]
            if isinstance(data.get("languages"), list):
                out: List[str] = []
                for item in data["languages"]:
                    if isinstance(item, dict) and item.get("code"):
                        out.append(str(item["code"]))
                return out
            if isinstance(data.get("langs"), list):
                return [str(x) for x in data["langs"]]
            return []

        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                out2: List[str] = []
                for item in data:
                    if isinstance(item, dict) and item.get("code"):
                        out2.append(str(item["code"]))
                return out2
            return [str(x) for x in data]

        return []

    def check_language(self, lang_code: str, payload: Dict[str, Any]) -> RuntimeResult:
        """
        POST payload to /generate/{lang_code}.

        PASS criteria:
          - HTTP 200
          - Prefer JSON dict response with surface_text/text/result/output
          - If JSON parsing fails but HTTP 200, accept non-empty raw body as success.
        """
        if not self._generate_prefix:
            self._discover_endpoints()
        assert self._generate_prefix is not None

        url = f"{self._generate_prefix}/{lang_code}"
        status, data, raw, dur_ms = self._http_post_json(url, payload)

        if status == 200:
            if isinstance(data, dict):
                txt = (
                    data.get("surface_text")
                    or data.get("text")
                    or data.get("result")
                    or data.get("output")
                )
                sample = (
                    str(txt)[:200]
                    if txt
                    else (raw[:200] if isinstance(raw, str) and raw else None)
                )
                return RuntimeResult(
                    api_lang=lang_code,
                    status="PASS",
                    http_status=status,
                    duration_ms=dur_ms,
                    sample_text=sample,
                )

            # If JSON parsing failed but request succeeded, accept raw text.
            if isinstance(raw, str) and raw.strip():
                return RuntimeResult(
                    api_lang=lang_code,
                    status="PASS",
                    http_status=status,
                    duration_ms=dur_ms,
                    sample_text=raw.strip()[:200],
                )

        # Include short raw for debugging (caller should redact secrets upstream)
        err = raw[:500] if isinstance(raw, str) else str(raw)
        return RuntimeResult(
            api_lang=lang_code,
            status="FAIL",
            http_status=status if status != 0 else None,
            duration_ms=dur_ms,
            error=err,
        )


def default_test_payload() -> Dict[str, Any]:
    """
    Strict Path BioFrame expects a flat JSON object (no nested subject/properties).
    Keep payload shape minimal/safe.
    """
    return {
        "frame_type": "bio",
        "name": "Shaka",
        "profession": "warrior",
        "nationality": "zulu",
        "gender": "m",
    }


__all__ = ["RuntimeResult", "ArchitectApiRuntimeChecker", "default_test_payload"]
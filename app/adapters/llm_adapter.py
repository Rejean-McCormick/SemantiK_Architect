# app/adapters/llm_adapter.py
from __future__ import annotations

import os
from typing import Optional

import structlog

logger = structlog.get_logger()

_INVALID_PLACEHOLDERS = {
    "",
    "your_gemini_api_key_here",
    "YOUR_GEMINI_API_KEY_HERE",
    "your_google_api_key_here",
    "YOUR_GOOGLE_API_KEY_HERE",
    "your_api_key_here",
    "YOUR_API_KEY_HERE",
    "YOUR_API_KEY",
    "api_key",
    "none",
    "None",
}


class GeminiAdapter:
    """
    Driven Adapter for Google's Gemini models (Google GenAI SDK).

    - Supports BYOK (user_api_key from request header) with env fallback.
    - Uses the `google-genai` SDK only (no legacy `google.generativeai` fallback).
    """

    def __init__(self, user_api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key: Optional[str] = None
        self.source: str = "None"

        # google-genai client
        self._client = None

        # Model selection
        self.model_name: str = (
            model_name
            or os.getenv("GEMINI_MODEL")
            or os.getenv("GOOGLE_MODEL")
            or "gemini-2.0-flash"
        )

        # 1) Pick a key (BYOK > env)
        self.api_key, self.source = self._pick_key(user_api_key)

        # 2) If no valid key: do not crash; disable AI features
        if not self.api_key:
            logger.warning(
                "llm_init_skipped",
                msg=(
                    "No valid Gemini API key found (user header, GEMINI_API_KEY, GOOGLE_API_KEY). "
                    "AI features disabled."
                ),
            )
            return

        # 3) Initialize google-genai client
        try:
            # google-genai: pip install google-genai
            from google import genai  # type: ignore

            self._client = genai.Client(api_key=self.api_key)
        except Exception as e:
            logger.error("llm_init_failed", sdk="google-genai", error=str(e))
            self._client = None

    @staticmethod
    def _is_valid_key(key: Optional[str]) -> bool:
        if key is None:
            return False
        k = key.strip()
        if not k:
            return False
        return k not in _INVALID_PLACEHOLDERS

    def _pick_key(self, user_api_key: Optional[str]) -> tuple[Optional[str], str]:
        # 1. Priority: User provided key (from Request Header)
        if self._is_valid_key(user_api_key):
            return user_api_key.strip(), "User-Provided"

        # 2. Fallback: Server env vars (prefer GEMINI_API_KEY, accept GOOGLE_API_KEY)
        for env_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            env_key = os.getenv(env_name)
            if self._is_valid_key(env_key):
                return env_key.strip(), f"Server-Default:{env_name}"

        return None, "None"

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def generate_text(self, prompt: str) -> str:
        if not self.enabled:
            logger.warning("llm_call_skipped", reason="No API key configured / SDK unavailable")
            return "Error: AI generation is disabled because no valid Gemini API key was found."

        try:
            resp = self._client.models.generate_content(  # type: ignore[union-attr]
                model=self.model_name,
                contents=prompt,
            )
            return getattr(resp, "text", None) or str(resp)

        except Exception as e:
            msg = str(e)

            # Quota / rate-limit
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                raise ConnectionError(f"Gemini API quota/rate-limit exceeded ({self.source}).") from e

            # Invalid key / auth failures
            if (
                "API_KEY_INVALID" in msg
                or "invalid api key" in msg.lower()
                or "UNAUTHENTICATED" in msg
                or "PERMISSION_DENIED" in msg
                or "401" in msg
                or "403" in msg
            ):
                logger.error("llm_auth_failed", source=self.source, error=msg)
                return "Error: AI generation is disabled because the provided Gemini API key is invalid."

            raise
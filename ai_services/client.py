# ai_services/client.py
import os
import time
import asyncio
import logging
from typing import Optional

from dotenv import load_dotenv
from google import genai  # NEW: google-genai SDK

# --- Configuration ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
# Default to a fast model, allow override
MODEL_NAME = os.getenv("ARCHITECT_AI_MODEL", "gemini-2.0-flash")

# --- Logging Setup ---
logger = logging.getLogger("ai_services")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - [AI] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# --- Circuit Breaker Pattern ---
class CircuitBreakerOpen(Exception):
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning("🔥 Circuit Breaker OPENED. AI Service paused.")

    def record_success(self) -> None:
        if self.state != "CLOSED":
            logger.info("✅ Circuit Breaker RECOVERED.")
        self.failures = 0
        self.state = "CLOSED"

    def check(self) -> bool:
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True  # Try one request
            raise CircuitBreakerOpen("AI Service is temporarily down.")
        return True


# Global Singletons
_client: Optional["genai.Client"] = None
_breaker = CircuitBreaker()


def _initialize() -> bool:
    """Initializes the Gemini client (Singleton Pattern)."""
    global _client
    if _client is not None:
        return True

    if not API_KEY:
        logger.error("Missing GOOGLE_API_KEY in environment variables.")
        return False

    try:
        _client = genai.Client(api_key=API_KEY)
        logger.info(f"Connected to Google AI ({MODEL_NAME})")
        return True
    except Exception as e:
        logger.critical(f"Connection failed: {e}")
        _client = None
        return False


def _extract_text(resp) -> str:
    # google-genai typically provides .text; fallback to string.
    return (getattr(resp, "text", None) or str(resp) or "").strip()


async def generate_async(prompt: str, max_retries: int = 3) -> str:
    """
    Robust ASYNC wrapper for text generation with Circuit Breaker and Backoff.

    Args:
        prompt (str): The prompt to send.
        max_retries (int): Retry attempts for transient errors.

    Returns:
        str: Generated text content or empty string on failure.
    """
    # 1. Init Check
    if not _initialize():
        return ""

    # 2. Circuit Breaker Check
    try:
        _breaker.check()
    except CircuitBreakerOpen:
        logger.error("Request blocked by Circuit Breaker.")
        return ""

    wait_time = 2  # Start with 2 seconds wait

    for attempt in range(1, max_retries + 1):
        try:
            # 3. Non-blocking Execution (run blocking call in a thread)
            def _call():
                # _client is guaranteed set if _initialize() returned True
                return _client.models.generate_content(  # type: ignore[union-attr]
                    model=MODEL_NAME,
                    contents=prompt,
                )

            response = await asyncio.to_thread(_call)

            # Success!
            _breaker.record_success()
            return _extract_text(response)

        except Exception as e:
            logger.warning(f"Attempt {attempt}/{max_retries} failed: {e}")
            _breaker.record_failure()

            if attempt < max_retries:
                await asyncio.sleep(wait_time)
                wait_time *= 2  # Exponential Backoff (2s -> 4s -> 8s)
            else:
                logger.error("AI Generation failed after max retries.")
                return ""

    return ""


def generate(prompt: str, max_retries: int = 3) -> str:
    """
    Synchronous wrapper for legacy CLI tools (e.g. forge.py).
    WARNING: Do not use this in the FastAPI app; use generate_async instead.
    """
    return asyncio.run(generate_async(prompt, max_retries))
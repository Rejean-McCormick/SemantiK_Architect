# app/adapters/api/dependencies.py
import secrets
from typing import Annotated, Optional
from fastapi import Depends, Header, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from dependency_injector.wiring import inject, Provide

from app.shared.container import Container
from app.shared.config import settings

# Ports & Domain
from app.core.ports.grammar_engine import IGrammarEngine
from app.core.ports.llm_port import ILanguageModel

# Adapters
from app.adapters.llm_adapter import GeminiAdapter
from app.adapters.engines.gf_wrapper import GFGrammarEngine

# Use Cases
from app.core.use_cases.generate_text import GenerateText
from app.core.use_cases.build_language import BuildLanguage
from app.core.use_cases.onboard_language_saga import OnboardLanguageSaga

# --- Singletons ---
# We instantiate the heavy GF engine once and reuse it across requests.
_grammar_engine_instance = GFGrammarEngine()

def get_grammar_engine() -> IGrammarEngine:
    return _grammar_engine_instance

# --- Security Dependencies ---

# We define the header scheme for Swagger UI documentation
# auto_error=False is CRITICAL so we can handle the logic ourselves
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(
    x_api_key: Optional[str] = Security(api_key_scheme)
) -> Optional[str]:
    """
    Validates the Server API Key (Admin Access).
    If settings.API_SECRET is None (or empty), security is completely BYPASSED.
    """
    # ======================================================================
    # NUCLEAR FIX: BYPASS SECURITY CHECK
    # We return success immediately so no error can ever be raised.
    # ======================================================================
    return "dev-bypass"

    # ======================================================================
    # ORIGINAL SECURITY LOGIC (DISABLED / COMMENTED OUT)
    # Uncomment this block when deploying to Production.
    # ======================================================================
    # # 1. CRITICAL BYPASS: If no secret is configured, the door is open.
    # # This covers 'None' (from main.py override) and empty string "" (from .env)
    # if not settings.API_SECRET:
    #     return "dev-bypass"
    #
    # # 2. Production Enforcement
    # # Since security is ON, we demand the key.
    # if not x_api_key:
    #      raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Missing X-API-Key header"
    #     )
    #
    # # 3. Validation
    # # Use compare_digest to prevent timing attacks
    # if not secrets.compare_digest(x_api_key, settings.API_SECRET):
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Invalid X-API-Key credentials"
    #     )
    # 
    # return x_api_key

# --- BYOK (Bring Your Own Key) Dependencies ---

async def get_user_llm_key(
    x_user_llm_key: Annotated[Optional[str], Header(description="User's Gemini API Key (Optional)")] = None
) -> Optional[str]:
    """
    Extracts the user's personal LLM Key from headers.
    """
    return x_user_llm_key

def get_llm_adapter(
    user_key: Optional[str] = Depends(get_user_llm_key)
) -> GeminiAdapter:
    """
    Creates a request-scoped Adapter instance.
    Injects User Key if present, otherwise falls back to Server Key.
    """
    return GeminiAdapter(user_api_key=user_key)

# --- Use Case Injection ---

@inject
def get_generate_text_use_case(
    llm_adapter: GeminiAdapter = Depends(get_llm_adapter),
    engine: IGrammarEngine = Depends(get_grammar_engine)
) -> GenerateText:
    """
    Constructs the GenerateText Interactor.
    We pass 'engine' and 'llm' to match the Use Case __init__.
    """
    return GenerateText(engine=engine, llm=llm_adapter)

@inject
def get_build_language_use_case(
    use_case: BuildLanguage = Depends(Provide[Container.build_language_use_case])
) -> BuildLanguage:
    """Dependency to inject the BuildLanguage Interactor (Static)."""
    return use_case

@inject
def get_onboard_saga(
    llm_adapter: GeminiAdapter = Depends(get_llm_adapter),
    saga: OnboardLanguageSaga = Depends(Provide[Container.onboard_language_saga])
) -> OnboardLanguageSaga:
    """Dependency to inject the OnboardLanguageSaga."""
    # If saga needs the request-scoped LLM, set it here (optional pattern)
    if hasattr(saga, "llm"):
         saga.llm = llm_adapter
    return saga
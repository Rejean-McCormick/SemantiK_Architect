# app/adapters/api/dependencies.py
import secrets
from typing import Annotated, Optional
from fastapi import Depends, Header, HTTPException, status
from dependency_injector.wiring import inject, Provide

from app.shared.container import Container
from app.shared.config import settings
from app.adapters.llm_adapter import GeminiAdapter

# Import Use Cases
from app.core.use_cases.generate_text import GenerateText
from app.core.use_cases.build_language import BuildLanguage
from app.core.use_cases.onboard_language_saga import OnboardLanguageSaga

# --- Security Dependencies ---

async def verify_api_key(
    x_api_key: Annotated[str, Header(description="Secret Key for API Access")]
) -> str:
    """
    Validates the Server API Key (Admin Access).
    Uses constant-time comparison to prevent timing attacks.
    """
    if not settings.API_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: API_SECRET not set"
        )

    if not secrets.compare_digest(x_api_key, settings.API_SECRET):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid X-API-Key credentials"
        )
    return x_api_key

# --- BYOK (Bring Your Own Key) Dependencies ---

async def get_user_llm_key(
    x_user_llm_key: Annotated[Optional[str], Header(description="User's Gemini API Key (Optional)")] = None
) -> Optional[str]:
    """
    Extracts the user's personal LLM Key from headers.
    If provided, this allows them to bypass server quotas/costs.
    """
    return x_user_llm_key

def get_llm_adapter(
    user_key: Optional[str] = Depends(get_user_llm_key)
) -> GeminiAdapter:
    """
    Creates a request-scoped Adapter instance.
    This injects the User Key (if present) or falls back to Server Key.
    """
    return GeminiAdapter(user_api_key=user_key)

# --- Use Case Injection ---

@inject
def get_generate_text_use_case(
    # We inject the dynamic, request-scoped adapter here
    llm_adapter: GeminiAdapter = Depends(get_llm_adapter),
    # If the use case needs other static dependencies (like Repos), we pull them from container
    # language_repo = Depends(Provide[Container.language_repo]) 
) -> GenerateText:
    """
    Constructs the GenerateText Interactor with the correct LLM Adapter.
    """
    # We manually instantiate here to ensure the Use Case uses the *User's* key,
    # not the Singleton adapter cached in the Container.
    return GenerateText(llm_port=llm_adapter)

@inject
def get_build_language_use_case(
    use_case: BuildLanguage = Depends(Provide[Container.build_language_use_case])
) -> BuildLanguage:
    """Dependency to inject the BuildLanguage Interactor (Static)."""
    return use_case

@inject
def get_onboard_saga(
    # Sagas might also need the LLM adapter if they generate initial content
    llm_adapter: GeminiAdapter = Depends(get_llm_adapter),
    # Inject other fixed dependencies manually if bypassing container for Sagas
    # Or, if the Saga doesn't use the LLM directly, just use Provide[]
    saga: OnboardLanguageSaga = Depends(Provide[Container.onboard_language_saga])
) -> OnboardLanguageSaga:
    """Dependency to inject the OnboardLanguageSaga."""
    # If the Saga uses the LLM, you might need to set the adapter manually:
    # saga.llm_port = llm_adapter 
    return saga
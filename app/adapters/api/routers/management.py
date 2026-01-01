# app/adapters/api/routers/management.py
from typing import Optional, Dict, Any
import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, Field

# Core Domain & Use Cases
from app.core.use_cases.onboard_language_saga import OnboardLanguageSaga, LanguageAlreadyExistsError
from app.core.use_cases.build_language import BuildLanguage
from app.core.domain.exceptions import DomainError

# Adapters & Infrastructure
from app.adapters.api.dependencies import (
    get_onboard_saga, 
    get_build_language_use_case, 
    verify_api_key
)

logger = structlog.get_logger()

# -----------------------------------------------------------------------------
# Router Definition
# Resource: /languages
# Mounted at: /api/v1 (in main.py) -> URL: /api/v1/languages
# -----------------------------------------------------------------------------
router = APIRouter(
    prefix="/languages",
    tags=["Management"],
    dependencies=[Depends(verify_api_key)]  # <--- CRITICAL: Enforce Admin Auth
)

# -----------------------------------------------------------------------------
# Request Models
# -----------------------------------------------------------------------------

class LanguageOnboardRequest(BaseModel):
    code: str = Field(..., min_length=3, max_length=3, pattern="^[a-z]{3}$", description="ISO 639-3 code (e.g., 'deu')")
    name: str = Field(..., min_length=1, description="English name of the language")
    family: str = Field("Other", description="Language family (e.g., 'Germanic')")

class BuildRequest(BaseModel):
    strategy: str = Field("fast", pattern="^(fast|full)$", description="Build strategy: 'fast' (Pidgin) or 'full' (GF)")

# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Onboard a New Language",
    response_description="Confirmation of the onboarding start"
)
async def onboard_language(
    request: LanguageOnboardRequest,
    saga: OnboardLanguageSaga = Depends(get_onboard_saga)
) -> Dict[str, Any]:
    """
    **[ADMIN ONLY]** Starts the onboarding process for a new language.
    
    This is a **Long-Running Process** (Saga):
    1. Registers the language in the system.
    2. Creates initial configuration files.
    3. Triggers an asynchronous 'Fast Build' to scaffold resources.
    """
    logger.info("onboard_language_request", code=request.code, name=request.name)
    
    try:
        lang_code = await saga.execute(
            code=request.code,
            name=request.name,
            family=request.family
        )
        
        logger.info("onboard_language_success", code=lang_code)
        
        return {
            "message": f"Language '{lang_code}' successfully onboarded.",
            "code": lang_code,
            "next_step": "Background build started. Check logs or query status."
        }

    except LanguageAlreadyExistsError as e:
        logger.warning("onboard_language_conflict", code=request.code, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Language '{request.code}' already exists."
        )
    except DomainError as e:
        logger.error("onboarding_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post(
    "/{lang_code}/build",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Language Rebuild"
)
async def trigger_build(
    lang_code: str,
    request: BuildRequest = Body(...),
    use_case: BuildLanguage = Depends(get_build_language_use_case)
) -> Dict[str, Any]:
    """
    **[ADMIN ONLY]** Manually triggers a build/compilation for an existing language.
    
    Returns **202 Accepted** immediately, returning an Event ID to track the background task.
    """
    logger.info("trigger_build_request", code=lang_code, strategy=request.strategy)
    
    try:
        event_id = await use_case.execute(lang_code, strategy=request.strategy)
        
        return {
            "message": "Build request queued.",
            "event_id": event_id,
            "lang_code": lang_code,
            "strategy": request.strategy
        }

    except DomainError as e:
        logger.error("build_trigger_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
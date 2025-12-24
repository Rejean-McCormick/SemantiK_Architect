# app/adapters/api/routes.py
from fastapi import APIRouter, Depends, HTTPException, status, Header, Body
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Union

# Domain & Use Cases
from app.core.domain.models import Frame
from app.core.domain.semantic_models import UniversalNode  # <--- NEW: Prototype Path
from ninai.constructors import Statement                   # <--- NEW: Strict Path

from app.core.use_cases.generate_text import GenerateText
from app.core.use_cases.build_language import BuildLanguage
from app.core.use_cases.onboard_language_saga import OnboardLanguageSaga

# Dependencies
from app.adapters.api.dependencies import (
    verify_api_key,
    get_generate_text_use_case,
    get_build_language_use_case,
    get_onboard_saga
)
from app.shared.observability import get_tracer

router = APIRouter()
tracer = get_tracer(__name__)

# --- Pydantic Schemas (DTOs) ---

class OnboardRequest(BaseModel):
    iso_code: str
    english_name: str

class CompilationRequest(BaseModel):
    language_code: str
    force: bool = False

# --- Endpoints ---

@router.post(
    "/generate/{lang}",
    summary="Generate Natural Language",
    description="Dual-Path Generation: Accepts Strict Ninai Statement OR Prototype UniversalNode.",
    response_model=dict
)
async def generate_text(
    lang: str,
    # DUAL-PATH ARGUMENT: Accepts either Strict Ninai OR Prototype Node
    request: Union[Statement, UniversalNode] = Body(...),
    # Security: Protected by API Key
    _auth: str = Depends(verify_api_key),
    use_case: GenerateText = Depends(get_generate_text_use_case)
):
    with tracer.start_as_current_span("api_generate_text") as span:
        span.set_attribute("gen.language", lang)
        
        try:
            # We pass the object (Strict or Prototype) directly to the Use Case.
            # The Use Case and Engine Adapter handle the Duck Typing logic.
            result = await use_case.execute(lang, request)
            
            # The use case usually returns a result object. 
            # If it returns a plain string, wrapping it might be needed, 
            # but usually it returns a structured response which FastAPI serializes.
            return result

        except Exception as e:
            span.record_exception(e)
            # 422 Unprocessable Entity is appropriate for validation/generation errors
            raise HTTPException(status_code=422, detail=f"Generation Error: {str(e)}")

@router.post(
    "/languages",
    summary="Onboard New Language",
    description="Saga: Scaffolds directories, fetches external data, and triggers initial build.",
    status_code=status.HTTP_202_ACCEPTED
)
async def onboard_language(
    request: OnboardRequest,
    _auth: str = Depends(verify_api_key),
    saga: OnboardLanguageSaga = Depends(get_onboard_saga)
):
    with tracer.start_as_current_span("api_onboard_language") as span:
        span.set_attribute("onboard.iso_code", request.iso_code)
        
        try:
            # Trigger the Background Saga
            task_id = await saga.execute(request.iso_code, request.english_name)
            return {
                "status": "accepted",
                "message": f"Onboarding started for {request.english_name} ({request.iso_code})",
                "task_id": str(task_id)
            }
        except Exception as e:
            span.record_exception(e)
            raise HTTPException(status_code=400, detail=str(e))

@router.post(
    "/compile",
    summary="Trigger Grammar Compilation",
    description="Queues a CPU-intensive job to compile GF source files into PGF.",
    status_code=status.HTTP_202_ACCEPTED
)
async def trigger_compilation(
    request: CompilationRequest,
    _auth: str = Depends(verify_api_key),
    use_case: BuildLanguage = Depends(get_build_language_use_case)
):
    with tracer.start_as_current_span("api_trigger_compile") as span:
        span.set_attribute("compile.language", request.language_code)
        
        try:
            job_id = await use_case.execute(request.language_code)
            return {
                "status": "queued",
                "job_id": job_id,
                "language": request.language_code
            }
        except Exception as e:
            span.record_exception(e)
            raise HTTPException(status_code=500, detail=f"Failed to queue compilation: {str(e)}")

@router.get("/health")
async def health_check():
    """K8s Liveness Probe."""
    return {"status": "ok", "version": "1.0.0"}
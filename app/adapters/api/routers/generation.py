from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
import structlog

# Existing imports
from app.core.domain.models import Frame, Sentence
from app.core.use_cases.generate_text import GenerateText
from app.core.domain.exceptions import (
    LanguageNotFoundError, 
    InvalidFrameError, 
    UnsupportedFrameTypeError,
    DomainError
)
from app.adapters.api.dependencies import get_generate_text_use_case, verify_api_key
from app.adapters.ninai import ninai_adapter

# --- NEW v2.0 IMPORTS ---
from app.core.domain.frame import BioFrame  # To detect Biographical contexts
from app.core.domain.context import DiscourseEntity # For creating new focus
from app.adapters.redis_bus import redis_bus # Singleton Adapter for State

logger = structlog.get_logger()

# We apply the API Key security dependency at the router level
router = APIRouter(
    prefix="/generate", 
    tags=["Generation"],
    dependencies=[Depends(verify_api_key)]
)

@router.post(
    "/{lang_code}", 
    response_model=Sentence,
    status_code=status.HTTP_200_OK,
    summary="Generate Text from Abstract Frame"
)
async def generate_text(
    request: Request, # <--- NEW: Need Request object to access Headers
    lang_code: str,
    # Accept generic Dict to support both Ninai (Tree) and Frame (Flat)
    payload: Dict[str, Any] = Body(..., description="Abstract Semantic Frame or Ninai Protocol payload"),
    use_case: GenerateText = Depends(get_generate_text_use_case)
):
    """
    Converts a Semantic Frame (abstract intent) into a concrete Sentence in the target language.
    Supports v2.0 Discourse Planning (Pronominalization) via X-Session-ID.
    """
    try:
        # --- ADAPTER LAYER: Input Normalization ---
        # 1. Check for Ninai Protocol (Recursive Object Tree)
        if "function" in payload:
            try:
                logger.info("ninai_protocol_detected", lang=lang_code)
                # Convert Ninai Tree -> Internal Pydantic Frame
                frame = ninai_adapter.parse(payload)
            except ValueError as e:
                # Adapter parsing failed (Protocol Violation)
                raise InvalidFrameError(f"Ninai Parsing Error: {str(e)}")
        
        else:
            # 2. Assume Internal Flat Frame (Standard API)
            try:
                # Try to instantiate as BioFrame first to support Context Logic
                if payload.get("frame_type") == "bio":
                    frame = BioFrame(**payload)
                else:
                    # Fallback to generic Frame validation
                    frame = Frame(**payload)
            except Exception as e:
                raise InvalidFrameError(f"Invalid Frame format: {str(e)}")

        # --- CONTEXT LAYER: Discourse Planning (The "She" Logic) ---
        session_id = request.headers.get("X-Session-ID")
        
        # Only apply context logic if we have a session AND it's a BioFrame
        if session_id and isinstance(frame, BioFrame):
            # A. Fetch Context from Redis (Async)
            context = await redis_bus.get_session(session_id)
            
            # B. Check Focus (Is the Subject the same as the previous turn?)
            # We compare the stored QID with the current frame's context_id
            if (context.current_focus and 
                frame.context_id and 
                context.current_focus.qid == frame.context_id):
                
                logger.info("pronominalization_triggered", session=session_id)
                
                # MUTATION: Swap Name for Pronoun based on previous gender
                if context.current_focus.gender == "f":
                    frame.name = "She"
                elif context.current_focus.gender == "m":
                    frame.name = "He"
                else:
                    frame.name = "It"

            # C. Update Focus for the NEXT turn
            # The subject of this sentence becomes the focus of the next one
            new_entity = DiscourseEntity(
                label=frame.name,
                gender=frame.gender or "n", 
                qid=frame.context_id or "Q0",
                recency=0
            )
            context.update_focus(new_entity)
            
            # D. Persist State back to Redis
            await redis_bus.save_session(context)

        # --- USE CASE LAYER: Business Logic ---
        # Delegate to the Clean Architecture Use Case
        sentence = await use_case.execute(lang_code, frame)
        return sentence

    except LanguageNotFoundError as e:
        # Map Domain Error -> HTTP 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=str(e)
        )
    
    except (InvalidFrameError, UnsupportedFrameTypeError) as e:
        # Map Validation Errors -> HTTP 422
        logger.warning("generation_bad_request", lang=lang_code, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail=str(e)
        )

    except DomainError as e:
        # Catch-all for other expected domain errors -> HTTP 400
        logger.error("generation_domain_error", lang=lang_code, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Generation failed: {str(e)}"
        )
        
    except Exception as e:
        # Unexpected System Errors -> HTTP 500
        logger.critical("unexpected_generation_crash", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during text generation."
        )
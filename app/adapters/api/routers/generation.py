# app/adapters/api/routers/generation.py
from typing import Any, Dict, Union, Optional
import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, Header

# Core Domain Imports
from app.core.domain.models import Frame, Sentence
from app.core.domain.frame import BioFrame
from app.core.domain.context import DiscourseEntity
from app.core.domain.exceptions import (
    LanguageNotFoundError,
    InvalidFrameError,
    UnsupportedFrameTypeError,
    DomainError
)
from app.core.use_cases.generate_text import GenerateText

# Adapters & Infrastructure
from app.adapters.api.dependencies import get_generate_text_use_case, verify_api_key
from app.adapters.ninai import ninai_adapter
from app.adapters.redis_bus import redis_bus

logger = structlog.get_logger()

# -----------------------------------------------------------------------------
# Router Definition
# Resource: /generate
# Mounted at: /api/v1 (in main.py) -> URL: /api/v1/generate
# -----------------------------------------------------------------------------
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
    request: Request,
    lang_code: str,
    payload: Dict[str, Any] = Body(..., description="Abstract Semantic Frame or Ninai Protocol payload"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    use_case: GenerateText = Depends(get_generate_text_use_case)
):
    """
    Converts a Semantic Frame (abstract intent) into a concrete Sentence in the target language.
    
    Features:
    - **Ninai Protocol Support**: Auto-detects and parses recursive Ninai object trees.
    - **Discourse Planning**: Handles pronominalization context via X-Session-ID.
    - **Validation**: Enforces domain constraints via the Use Case.
    """
    try:
        # ---------------------------------------------------------------------
        # 1. ADAPTER LAYER: Input Normalization (JSON -> Domain Entity)
        # ---------------------------------------------------------------------
        frame = _parse_payload(payload, lang_code)

        # ---------------------------------------------------------------------
        # 2. CONTEXT LAYER: Discourse Planning (Stateful Logic)
        # ---------------------------------------------------------------------
        # TODO v2.2: Move this logic into a specialized 'DiscourseService' 
        # to keep the Router clean and stateless.
        if x_session_id and isinstance(frame, BioFrame):
            await _apply_discourse_context(x_session_id, frame)

        # ---------------------------------------------------------------------
        # 3. USE CASE LAYER: Execution
        # ---------------------------------------------------------------------
        sentence = await use_case.execute(lang_code, frame)
        return sentence

    except (InvalidFrameError, ValueError) as e:
        logger.warning("generation_bad_request", lang=lang_code, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except LanguageNotFoundError as e:
        logger.warning("generation_language_not_found", lang=lang_code, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DomainError as e:
        logger.error("generation_domain_error", lang=lang_code, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Generation failed: {str(e)}"
        )
    except Exception as e:
        logger.critical("unexpected_generation_crash", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during text generation."
        )

# -----------------------------------------------------------------------------
# Helper Functions (Private)
# -----------------------------------------------------------------------------

def _parse_payload(payload: Dict[str, Any], lang_code: str) -> Union[BioFrame, Frame]:
    """
    Determines if the payload is Ninai Protocol or a standard Frame
    and converts it to the appropriate Domain Entity.
    """
    # A. Ninai Protocol (Recursive Object Tree)
    if "function" in payload:
        logger.info("ninai_protocol_detected", lang=lang_code)
        try:
            return ninai_adapter.parse(payload)
        except ValueError as e:
            raise InvalidFrameError(f"Ninai Parsing Error: {str(e)}")

    # B. Standard Flat Frame
    try:
        frame_type = payload.get("frame_type")
        if frame_type == "bio":
            return BioFrame(**payload)
        return Frame(**payload)
    except Exception as e:
        raise InvalidFrameError(f"Invalid Frame format: {str(e)}")

async def _apply_discourse_context(session_id: str, frame: BioFrame):
    """
    Applies pronominalization logic based on the session history.
    Mutates the frame in-place if the subject matches the current focus.
    """
    # 1. Fetch Context
    context = await redis_bus.get_session(session_id)
    
    # 2. Check Focus (Centering Theory)
    # If the new subject QID matches the previous focus QID, we pronominalize.
    if (context.current_focus and 
        frame.context_id and 
        context.current_focus.qid == frame.context_id):
        
        logger.info("pronominalization_triggered", session=session_id)
        
        # Inject GF Pronominalization Strategy
        if frame.meta is None:
            frame.meta = {}

        gender_map = {
            "f": ("She", "she_Pron"),
            "m": ("He", "he_Pron"),
            "n": ("It", "it_Pron")
        }
        
        # Default to 'It' if gender is unknown or 'c' (common)
        pronoun_label, gf_arg = gender_map.get(context.current_focus.gender, ("It", "it_Pron"))

        frame.name = pronoun_label
        frame.meta['gf_function'] = "UsePron"
        frame.meta['gf_arg'] = gf_arg

    # 3. Update Focus for Next Turn
    # The subject of this sentence becomes the Backward-Looking Center (Cb) for the next.
    new_entity = DiscourseEntity(
        label=frame.name,
        gender=frame.gender or "n", 
        qid=frame.context_id or "Q0",
        recency=0
    )
    context.update_focus(new_entity)
    
    # 4. Persist
    await redis_bus.save_session(context)
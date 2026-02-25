# app/adapters/api/routers/frames.py
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class FrameTypeDefinition(BaseModel):
    """
    Metadata about a Semantic Frame supported by the system.
    Used by the frontend to render the 'Create Workspace' grid.
    """
    id: str           # e.g., 'bio', 'event.transitive'
    label: str        # Human-readable title
    description: str  # Short blurb for the UI cards
    schema_ref: str   # API path to the JSON schema (for form validation)
    icon: Optional[str] = None # Optional icon identifier

@router.get("/types", response_model=List[FrameTypeDefinition])
async def list_frame_types():
    """
    Returns the catalogue of available Abstract Semantic Frames.
    The frontend uses this to populate the workspace creation capabilities.
    """
    return [
        {
            "id": "bio",
            "label": "Biographical Fact",
            "description": "Expresses who someone is (Name, Profession, Nationality).",
            "schema_ref": "/api/v1/schemas/frames/bio",
            "icon": "user"
        },
        {
            "id": "event.transitive",
            "label": "Transitive Event",
            "description": "Simple Action: Subject does Action to Object (SVO).",
            "schema_ref": "/api/v1/schemas/frames/event_transitive",
            "icon": "activity"
        },
        {
            "id": "generic",
            "label": "Safe Mode (Generic)",
            "description": "Direct Abstract Syntax Tree construction (Advanced Users).",
            "schema_ref": "/api/v1/schemas/frames/generic",
            "icon": "code"
        }
    ]
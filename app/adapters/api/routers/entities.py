# app/adapters/api/routers/entities.py
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class EntitySummary(BaseModel):
    """
    Minimal representation of a Wikifunctions/Wikidata entity.
    Used for listing recent items in the frontend.
    """
    id: str      # QID (e.g., Q7251)
    label: str   # Name (e.g., Alan Turing)
    description: Optional[str] = None
    type: str = "person" # person, artifact, event, etc.

@router.get("/", response_model=List[EntitySummary])
async def list_entities():
    """
    Returns a list of recently used entities.
    
    TODO: In v2.1, connect this to a 'HistoryService' or Redis cache 
    that tracks what the user has actually generated.
    For now, we return a static demo set to unblock the UI.
    """
    return [
        {
            "id": "Q7251",
            "label": "Alan Turing",
            "description": "British mathematician and computer scientist",
            "type": "person"
        },
        {
            "id": "Q76",
            "label": "Barack Obama",
            "description": "44th President of the United States",
            "type": "person"
        },
        {
            "id": "Q352",
            "label": "Adolf Hitler",
            "description": "Austrian-born German politician",
            "type": "person"
        },
        {
            "id": "Q937",
            "label": "Albert Einstein",
            "description": "Theoretical physicist",
            "type": "person"
        },
        {
            "id": "Q42",
            "label": "Douglas Adams",
            "description": "English author and humorist",
            "type": "person"
        }
    ]
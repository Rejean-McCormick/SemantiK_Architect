# app/adapters/api/routers/languages.py
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException
from dependency_injector.wiring import inject, Provide
from pydantic import BaseModel

from app.shared.container import Container
from app.core.ports import LanguageRepo

router = APIRouter()

# --- DTOs (Data Transfer Objects) ---
class LanguageOut(BaseModel):
    """
    Public API representation of a Language.
    Matches the frontend interface: interface Language { code: string; name: string; z_id?: string; }
    """
    code: str
    name: str
    z_id: Optional[str] = None

# --- Endpoints ---

@router.get("/", response_model=List[LanguageOut])
@inject
async def list_languages(
    repo: LanguageRepo = Depends(Provide[Container.language_repo]),
) -> List[LanguageOut]:
    """
    List all languages available in the system.
    Returns rich objects (Code, Name, ZID) for the UI dropdowns.
    """
    try:
        # Fetch data from the domain repository
        items = await repo.list_languages()
        
        # Map domain entities (or legacy strings) to the DTO
        results = []
        for item in items:
            # Case A: Legacy Repo returns strings (e.g., 'eng') -> Polyfill name
            if isinstance(item, str):
                results.append(LanguageOut(code=item, name=item, z_id=None))
            
            # Case B: Repo returns Dictionaries
            elif isinstance(item, dict):
                results.append(LanguageOut(
                    code=item.get("code"), 
                    name=item.get("name", item.get("code")), # Fallback to code if name missing
                    z_id=item.get("z_id")
                ))
            
            # Case C: Repo returns Domain Entities (Classes)
            else:
                results.append(LanguageOut(
                    code=getattr(item, "code"),
                    name=getattr(item, "name", getattr(item, "code")),
                    z_id=getattr(item, "z_id", None)
                ))

        return results

    except Exception as e:
        # Log the error in a real app
        raise HTTPException(status_code=500, detail=str(e))
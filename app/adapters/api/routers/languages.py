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
    CRITICAL: Filters out legacy ISO-3 codes (e.g. 'eng') and RGL suffixes (e.g. 'Fre').
    Only returns valid ISO-639-1 (2-letter) codes from the Matrix/Repo.
    """
    try:
        # Fetch data from the domain repository
        items = await repo.list_languages()
        
        results = []
        for item in items:
            # 1. Normalize Extraction (Handle Dict/Obj/Str polymorphism)
            code: str = ""
            name: str = ""
            z_id: Optional[str] = None

            if isinstance(item, str):
                # Legacy path: just a string code
                code = item
                name = item
            elif isinstance(item, dict):
                code = item.get("code", "")
                name = item.get("name", code)
                z_id = item.get("z_id")
            else:
                # Domain Entity path
                code = getattr(item, "code", "")
                name = getattr(item, "name", code)
                z_id = getattr(item, "z_id", None)

            # [cite_start]2. THE FILTER (Phase 3 Normalization) [cite: 32, 34]
            # We strictly enforce ISO 639-1 (2-letter) codes for the public API.
            # This drops 'eng' (legacy), 'WikiFre' (internal), and 'French' (folder names).
            if not code or len(code) != 2 or not code.isalpha():
                continue

            results.append(LanguageOut(
                code=code.lower(), # Enforce lowercase standard (fr, en)
                name=name,
                z_id=z_id
            ))

        return results

    except Exception as e:
        # Log the error in a real app
        raise HTTPException(status_code=500, detail=str(e))
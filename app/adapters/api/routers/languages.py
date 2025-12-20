# app/adapters/api/routers/languages.py
from fastapi import APIRouter, Depends, HTTPException
from dependency_injector.wiring import inject, Provide
from typing import List

from app.shared.container import Container
from app.core.ports import LanguageRepo

router = APIRouter()

@router.get("/", response_model=List[str])
@inject
async def list_languages(
    repo: LanguageRepo = Depends(Provide[Container.language_repo]),
) -> List[str]:
    """
    List all language codes currently available in the system.
    """
    try:
        return await repo.list_languages()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
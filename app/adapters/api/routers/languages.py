# app/adapters/api/routers/languages.py
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.ports import LanguageRepo
from app.shared.config import settings
from app.shared.container import Container

router = APIRouter()


class LanguageOut(BaseModel):
    """
    Public API representation of a Language.
    Matches the frontend interface: interface Language { code: string; name: string; z_id?: string; }
    """
    code: str
    name: str
    z_id: Optional[str] = None


@lru_cache(maxsize=1)
def _suffix_to_iso2_map() -> dict[str, str]:
    """
    Build reverse map: wiki suffix (e.g., 'Eng', 'Fre', 'Ger') -> iso2 ('en','fr','de').
    Reads data/config/iso_to_wiki.json (or config/iso_to_wiki.json).
    """
    candidates: list[Path] = []

    repo_root = Path(getattr(settings, "FILESYSTEM_REPO_PATH", "") or "").expanduser()
    if str(repo_root).strip():
        candidates.append(repo_root / "data" / "config" / "iso_to_wiki.json")
        candidates.append(repo_root / "config" / "iso_to_wiki.json")

    project_root = Path(__file__).resolve().parents[4]
    candidates.append(project_root / "data" / "config" / "iso_to_wiki.json")
    candidates.append(project_root / "config" / "iso_to_wiki.json")

    for p in candidates:
        if p.exists():
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                out: dict[str, str] = {}
                for iso2, v in (raw or {}).items():
                    if not isinstance(iso2, str):
                        continue
                    iso2_clean = iso2.lower().strip()
                    if len(iso2_clean) != 2 or not iso2_clean.isalpha():
                        continue

                    suffix: Optional[str] = None
                    if isinstance(v, dict):
                        suffix = v.get("wiki")
                    elif isinstance(v, str):
                        suffix = v.replace("Wiki", "")

                    if isinstance(suffix, str) and suffix.strip():
                        out[suffix.lower().strip()] = iso2_clean
                return out
            except Exception:
                return {}

    return {}


def _normalize_to_iso2(code: str) -> Optional[str]:
    """
    Accept:
      - iso2: "en" -> "en"
      - wiki concrete-ish: "WikiEng" -> "en"
      - suffix/legacy-ish: "Eng" / "eng" / "Fre" -> "en"/"fr"
    Return None if cannot normalize.
    """
    c = (code or "").strip()
    if not c:
        return None

    # ISO-639-1 already
    if len(c) == 2 and c.isalpha():
        return c.lower()

    rev = _suffix_to_iso2_map()

    # "WikiEng" style
    if c.lower().startswith("wiki") and len(c) >= 7:
        suffix = c[4:].strip()
        if suffix:
            iso2 = rev.get(suffix.lower())
            if iso2:
                return iso2

    # 3-letter suffix / legacy
    if len(c) == 3 and c.isalpha():
        iso2 = rev.get(c.lower())
        if iso2:
            return iso2

    return None


@router.get("/", response_model=List[LanguageOut])
@inject
async def list_languages(
    repo: LanguageRepo = Depends(Provide[Container.language_repo]),
) -> List[LanguageOut]:
    """
    List all languages available in the system.
    Public API returns ISO-639-1 (2-letter) codes only; other forms are normalized when possible.
    """
    try:
        items = await repo.list_languages()

        by_code: dict[str, LanguageOut] = {}

        for item in items:
            raw_code: str = ""
            name: str = ""
            z_id: Optional[str] = None

            if isinstance(item, str):
                raw_code = item
                name = item
            elif isinstance(item, dict):
                raw_code = str(item.get("code", "") or item.get("lang_code", "") or item.get("language_code", ""))
                name = str(item.get("name", "") or raw_code)
                z_id = item.get("z_id")
            else:
                raw_code = str(getattr(item, "code", "") or getattr(item, "lang_code", "") or getattr(item, "language_code", ""))
                name = str(getattr(item, "name", "") or raw_code)
                z_id = getattr(item, "z_id", None)

            iso2 = _normalize_to_iso2(raw_code)
            if not iso2:
                continue

            # keep first occurrence; stable + de-duped
            if iso2 not in by_code:
                by_code[iso2] = LanguageOut(code=iso2, name=name or iso2, z_id=z_id)

        return [by_code[k] for k in sorted(by_code.keys())]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
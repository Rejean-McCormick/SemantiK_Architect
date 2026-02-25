# builder/orchestrator/iso_map.py
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .config import ISO_MAP_FILE

logger = logging.getLogger("Orchestrator")

IsoMapValue = Union[str, Dict[str, Any]]
IsoMap = Dict[str, IsoMapValue]


def load_iso_map(path: Path = ISO_MAP_FILE) -> IsoMap:
    """Loads the authoritative ISO -> WikiCode mapping."""
    if not path.exists():
        logger.warning("⚠️ ISO Map not found. Falling back to TitleCase.")
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            logger.warning("⚠️ ISO Map is not a JSON object. Falling back to TitleCase.")
            return {}
        return data  # type: ignore[return-value]
    except Exception as e:
        logger.error(f"❌ Failed to load ISO Map: {e}")
        return {}


# Loaded once by default (mirrors orchestrator.py behavior).
ISO_MAP: IsoMap = load_iso_map()


def get_gf_name(code: str, iso_map: Optional[IsoMap] = None) -> str:
    """
    Standardizes naming using iso_to_wiki.json when present.
    Input:  'en' (ISO-2) OR 'eng' (legacy ISO-3-like token)
    Output: 'WikiEng.gf' (WikiCode module file)
    """
    if not code:
        return "WikiUnknown.gf"

    m = iso_map if iso_map is not None else ISO_MAP
    raw_val = m.get(code, m.get(code.lower()))
    suffix: Optional[str] = None

    if raw_val:
        if isinstance(raw_val, dict):
            val_str = str(raw_val.get("wiki", "") or "")
        else:
            val_str = str(raw_val)

        suffix = val_str.replace("Wiki", "").strip()

    if not suffix:
        suffix = code.title().strip()

    return f"Wiki{suffix}.gf"


def get_wiki_suffix(code: str, iso_map: Optional[IsoMap] = None) -> str:
    """Return 'Eng' from 'en' or 'eng' using ISO_MAP when available."""
    gf = get_gf_name(code, iso_map=iso_map)  # WikiEng.gf
    stem = Path(gf).stem  # WikiEng
    return stem.replace("Wiki", "").strip() or code.title().strip()
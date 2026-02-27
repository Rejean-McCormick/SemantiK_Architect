# utils/grammar_factory.py
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

logger = logging.getLogger("GrammarFactory")

# -----------------------------------------------------------------------------
# REPO PATHS
# -----------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT_DIR / "data" / "config"

FACTORY_TARGETS_FILE = CONFIG_DIR / "factory_targets.json"
TOPOLOGY_WEIGHTS_FILE = CONFIG_DIR / "topology_weights.json"
ISO_MAP_FILE = CONFIG_DIR / "iso_to_wiki.json"

# Optional dependency: app.shared.languages.ISO_2_TO_3
try:
    from app.shared.languages import ISO_2_TO_3 as _ISO_2_TO_3  # type: ignore
except Exception:
    _ISO_2_TO_3 = {}

ISO_2_TO_3: Mapping[str, str] = _ISO_2_TO_3

# -----------------------------------------------------------------------------
# DEFAULTS
# -----------------------------------------------------------------------------
DEFAULT_WEIGHTS: Dict[str, Dict[str, int]] = {
    "SVO": {"nsubj": -10, "root": 0, "obj": 10, "iobj": 5},
    "SOV": {"nsubj": -10, "obj": -5, "iobj": -2, "root": 0},
    "VSO": {"root": -10, "nsubj": 0, "obj": 10, "iobj": 15},
    "VOS": {"root": -10, "obj": 5, "nsubj": 10},
    "OVS": {"obj": -10, "root": 0, "nsubj": 10},
    "OSV": {"obj": -10, "nsubj": -5, "root": 0},
}

_STATIC_TOPOLOGY_OVERRIDES: Dict[str, str] = {
    "jpn": "SOV",
    "hin": "SOV",
    "kor": "SOV",
    "tur": "SOV",
    "urd": "SOV",
    "fas": "SOV",
    "ara": "VSO",
    "heb": "VSO",
}

# -----------------------------------------------------------------------------
# JSON LOADERS (CACHED)
# -----------------------------------------------------------------------------
def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=32)
def load_json_config(path: Path) -> Any:
    """
    Cached JSON reader. Returns {} if missing/unreadable.
    """
    try:
        if not path.exists():
            return {}
        return _read_json(path)
    except Exception as e:
        logger.warning("⚠️  Failed to load config %s: %s", path.name, e)
        return {}


# -----------------------------------------------------------------------------
# LANGUAGE CODE NORMALIZATION
# -----------------------------------------------------------------------------
def _norm_token(code: str) -> str:
    return (code or "").strip()


def normalize_codes(lang_code: str) -> Tuple[str, str]:
    """
    Returns (iso2_or_input, iso3) in lowercase.

    - If lang_code is ISO-2, attempts ISO_2_TO_3 lookup.
    - If lang_code is already ISO-3, uses it as-is.
    """
    raw = _norm_token(lang_code)
    if not raw:
        return "", ""
    lc = raw.lower()

    # ISO-2 -> ISO-3 when available
    if len(lc) == 2 and lc in ISO_2_TO_3:
        return lc, ISO_2_TO_3[lc].lower()

    # Otherwise treat as ISO-3-ish or arbitrary token
    return lc, lc


# -----------------------------------------------------------------------------
# TOPOLOGY
# -----------------------------------------------------------------------------
def get_topology(iso3_code: str) -> str:
    """
    Determine word order topology for an ISO-3 code.
    Priority:
      1) factory_targets.json
      2) static overrides
      3) SVO
    """
    iso3 = (iso3_code or "").strip().lower()
    if not iso3:
        return "SVO"

    targets = load_json_config(FACTORY_TARGETS_FILE)
    if isinstance(targets, dict):
        entry = targets.get(iso3)
        if isinstance(entry, dict):
            order = entry.get("order")
            if isinstance(order, str) and order.strip():
                return order.strip()

    return _STATIC_TOPOLOGY_OVERRIDES.get(iso3, "SVO")


# -----------------------------------------------------------------------------
# ISO -> GF SUFFIX (WikiEng / Eng / WikiEng.gf, v1 or v2 schema)
# -----------------------------------------------------------------------------
def _clean_wiki_suffix(x: str) -> str:
    s = (x or "").strip()
    if not s:
        return ""
    # accept "WikiEng", "WikiEng.gf", "Eng", "Eng.gf"
    if s.lower().startswith("wiki"):
        s = s[4:]
    if s.lower().endswith(".gf"):
        s = s[:-3]
    s = s.strip()
    if not s:
        return ""
    # normalize casing: Eng, Fre, Deu, Cym, ...
    return s[:1].upper() + s[1:].lower()


def get_gf_suffix(lang_code: str) -> str:
    """
    Returns standard GF suffix (e.g., 'Eng') using iso_to_wiki.json.

    Supports:
      - v1: "en": "WikiEng" / "Eng"
      - v2+: "en": {"wiki": "Eng", "tier": 1, ...}

    Lookup strategy:
      - try key = lang_code (as given), key = lower(lang_code)
      - if lang_code is iso2 and iso2->iso3 exists, also try iso3
    """
    raw = _norm_token(lang_code)
    if not raw:
        return "Unknown"

    mapping = load_json_config(ISO_MAP_FILE)
    if not isinstance(mapping, dict):
        return raw.title()

    iso2, iso3 = normalize_codes(raw)

    candidates = []
    # original + lowercase
    candidates.append(raw)
    candidates.append(raw.lower())

    # if iso2->iso3 known, try iso3 too
    if len(iso2) == 2 and iso3 and iso3 != iso2:
        candidates.append(iso3)
        candidates.append(iso3.lower())

    val: Any = None
    for k in candidates:
        if k in mapping:
            val = mapping.get(k)
            break

    if val is None:
        # fallback: TitleCase of whatever token user gave (keeps prior behavior)
        return raw.title()

    if isinstance(val, dict):
        wiki = val.get("wiki")
        if isinstance(wiki, str):
            cleaned = _clean_wiki_suffix(wiki)
            return cleaned or raw.title()
        return raw.title()

    if isinstance(val, str):
        cleaned = _clean_wiki_suffix(val)
        return cleaned or raw.title()

    return raw.title()


def get_gf_lang_name(lang_code: str) -> str:
    """
    Returns concrete module name, e.g. "WikiEng".
    """
    return f"Wiki{get_gf_suffix(lang_code)}"


# -----------------------------------------------------------------------------
# LINEARIZATION
# -----------------------------------------------------------------------------
def _build_linearization(components: list[dict[str, str]], weights: Mapping[str, int]) -> str:
    """
    Sorts components by role weights and joins GF expressions with '++'.
    """
    components.sort(key=lambda x: weights.get(x.get("role", ""), 0))
    return " ++ ".join(item["code"] for item in components)


# -----------------------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------------------
def generate_safe_mode_grammar(lang_code: str) -> str:
    """
    Generates a Safe Mode grammar.
    Uses iso_to_wiki.json to choose the correct concrete name (WikiEng vs WikiEn).
    """
    iso2, iso3 = normalize_codes(lang_code)
    order = get_topology(iso3)

    weights_db = load_json_config(TOPOLOGY_WEIGHTS_FILE)
    if not isinstance(weights_db, dict):
        weights_db = {}
    weights = weights_db.get(order)
    if not isinstance(weights, dict):
        weights = DEFAULT_WEIGHTS.get(order, DEFAULT_WEIGHTS["SVO"])

    # --- 1) Linearization Strategies ---
    bio_prof_lin = _build_linearization(
        [
            {"code": "entity.s", "role": "nsubj"},
            {"code": "\"is a\"", "role": "root"},
            {"code": "prof.s", "role": "obj"},
        ],
        weights,
    )

    bio_nat_lin = _build_linearization(
        [
            {"code": "entity.s", "role": "nsubj"},
            {"code": "\"is\"", "role": "root"},
            {"code": "nat.s", "role": "obj"},
        ],
        weights,
    )

    bio_full_lin = _build_linearization(
        [
            {"code": "entity.s", "role": "nsubj"},
            {"code": "\"is a\"", "role": "root"},
            {"code": "nat.s ++ prof.s", "role": "obj"},
        ],
        weights,
    )

    event_lin = _build_linearization(
        [
            {"code": "entity.s", "role": "nsubj"},
            {"code": "\"participated in\"", "role": "root"},
            {"code": "event.s", "role": "obj"},
        ],
        weights,
    )

    # --- 2) Generate GF Code ---
    lang_name = get_gf_lang_name(lang_code)
    lang_tag = iso3 or (iso2 or lang_code).lower()

    return f"""-- AUTO-GENERATED by utils/grammar_factory.py
-- lang={lang_code!s} iso={lang_tag} order={order}

concrete {lang_name} of SemantikArchitect = open Prelude in {{
  lincat
    Statement = SS ;
    Entity = SS ;
    Profession = SS ;
    Nationality = SS ;
    EventObj = SS ;

  lin
    -- Wrappers (pass-through; inputs already SS)
    mkEntityStr s = s ;
    strProf s = s ;
    strNat s = s ;
    strEvent s = s ;

    -- Bio frames
    mkBioProf entity prof = ss ({bio_prof_lin}) ;
    mkBioNat  entity nat  = ss ({bio_nat_lin}) ;
    mkBioFull entity prof nat = ss ({bio_full_lin}) ;

    -- Event frame
    mkEvent entity event = ss ({event_lin}) ;
}}
"""
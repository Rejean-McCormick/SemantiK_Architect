# tools/everything_matrix/norm.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple


def read_json(path: Path) -> Optional[Any]:
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_iso_to_wiki(iso_map_path: Path) -> Dict[str, Any]:
    """
    Load iso_to_wiki.json from a given path.

    Supported formats:
      - v1: {"eng":"Eng", ...} OR {"en":"Eng", ...}
      - v2: {"eng":{"wiki":"Eng","name":"English"}, "en":{"wiki":"Eng","name":"English"}, ...}

    Returns a dict as-is (empty dict if missing/invalid).
    """
    obj = read_json(iso_map_path)
    return obj if isinstance(obj, dict) else {}


def _discover_iso_map_path(repo_root: Path, iso_map_rel: str) -> Path:
    """
    Historically the project referenced config/iso_to_wiki.json, but the repo layout
    uses data/config/iso_to_wiki.json. Prefer the requested path if it exists,
    otherwise fall back to data/config.
    """
    primary = repo_root / iso_map_rel
    fallback = repo_root / "data" / "config" / "iso_to_wiki.json"
    return primary if primary.is_file() else fallback


def build_wiki_to_iso2(iso_to_wiki: Mapping[str, Any]) -> Dict[str, str]:
    """
    Build a reverse index:
      (iso2 key | iso3 key | wiki code | 'wiki'+wiki code) -> preferred iso2

    Preference rule:
      For a given wiki code, prefer the 2-letter ISO key when present.
    """
    preferred_by_wiki: Dict[str, str] = {}

    # Prefer iso2 keys for each wiki code (v2 objects)
    for k, v in iso_to_wiki.items():
        if not (isinstance(k, str) and isinstance(v, Mapping)):
            continue
        kk = k.strip().casefold()
        if len(kk) != 2:
            continue
        wiki = v.get("wiki")
        if isinstance(wiki, str) and wiki.strip():
            preferred_by_wiki[wiki.strip().casefold()] = kk

    wiki_to_iso2: Dict[str, str] = {}

    # v2 objects: map iso2/iso3 keys and wiki codes back to preferred iso2
    for k, v in iso_to_wiki.items():
        if not (isinstance(k, str) and isinstance(v, Mapping)):
            continue
        kk = k.strip().casefold()
        wiki = v.get("wiki")
        if not (isinstance(wiki, str) and wiki.strip()):
            continue
        wk = wiki.strip().casefold()
        iso2 = preferred_by_wiki.get(wk)
        if iso2 and len(iso2) == 2:
            wiki_to_iso2[kk] = iso2
            wiki_to_iso2[wk] = iso2
            wiki_to_iso2[f"wiki{wk}"] = iso2  # accept wikieng form

    # v1 compatibility: if values are strings (wiki codes), treat them as aliases.
    # For v1 we can only anchor to a 2-letter key (enterprise standard).
    for k, v in iso_to_wiki.items():
        if not isinstance(k, str):
            continue
        kk = k.strip().casefold()
        if len(kk) != 2 or not kk.isalpha():
            continue
        if isinstance(v, str) and v.strip():
            wk = v.strip().casefold()
            wiki_to_iso2[kk] = kk
            wiki_to_iso2[wk] = kk
            wiki_to_iso2[f"wiki{wk}"] = kk

    return wiki_to_iso2


def build_iso2_to_iso3(iso_to_wiki: Mapping[str, Any]) -> Dict[str, str]:
    """
    Build iso2 -> iso3 preference map from iso_to_wiki.json.

    If multiple iso3 map to the same wiki code, pick deterministically
    by sorted key iteration.
    """
    wiki_to_iso3: Dict[str, str] = {}
    for k in sorted(iso_to_wiki.keys(), key=lambda x: str(x).casefold()):
        v = iso_to_wiki.get(k)
        if not (isinstance(k, str) and isinstance(v, Mapping)):
            continue
        kk = k.strip().casefold()
        if len(kk) != 3 or not kk.isalpha():
            continue
        wiki = v.get("wiki")
        if isinstance(wiki, str) and wiki.strip():
            wk = wiki.strip().casefold()
            if wk not in wiki_to_iso3:
                wiki_to_iso3[wk] = kk

    iso2_to_iso3: Dict[str, str] = {}
    for k, v in iso_to_wiki.items():
        if not (isinstance(k, str) and isinstance(v, Mapping)):
            continue
        kk = k.strip().casefold()
        if len(kk) != 2 or not kk.isalpha():
            continue
        wiki = v.get("wiki")
        if not (isinstance(wiki, str) and wiki.strip()):
            continue
        wk = wiki.strip().casefold()
        iso3 = wiki_to_iso3.get(wk)
        if iso3:
            iso2_to_iso3[kk] = iso3

    return iso2_to_iso3


def build_name_map_iso2(
    iso_to_wiki: Mapping[str, Any],
    wiki_to_iso2: Mapping[str, str],
) -> Dict[str, str]:
    """
    Build: iso2 -> display name

    Uses iso_to_wiki entries that provide 'name'. If a name is attached to an iso3
    key, we still map it through wiki_to_iso2 when possible.
    """
    out: Dict[str, str] = {}
    for k, v in iso_to_wiki.items():
        if not (isinstance(k, str) and isinstance(v, Mapping)):
            continue
        name = v.get("name")
        if not (isinstance(name, str) and name.strip()):
            continue
        kk = k.strip().casefold()
        iso2 = wiki_to_iso2.get(kk)
        if iso2 and len(iso2) == 2:
            out[iso2] = name.strip()
        elif len(kk) == 2 and kk.isalpha():
            out[kk] = name.strip()
    return out


def norm_to_iso2(code: str, *, wiki_to_iso2: Mapping[str, str]) -> Optional[str]:
    """
    Normalize a code (iso2/iso3/wiki/wikixxx) -> iso2, using wiki_to_iso2.

    If the input is already a 2-letter code, accept it as-is (lowercased).
    """
    if not isinstance(code, str):
        return None
    k = code.strip().casefold()
    if not k:
        return None

    hit = wiki_to_iso2.get(k)
    if isinstance(hit, str) and len(hit) == 2:
        return hit

    if len(k) == 2 and k.isalpha():
        return k

    return None


def resolve_lang_suffix_to_iso2(
    suffix: str,
    *,
    wiki_to_iso2: Mapping[str, str],
    iso_to_wiki: Mapping[str, Any],
) -> Optional[str]:
    """
    Convert GF module suffix -> iso2.

    Accepted suffix forms:
      - iso2 (2 letters): only if present in iso_to_wiki.json (configured universe)
      - wiki (3 letters): via wiki_to_iso2
      - iso3 (3 letters): via wiki_to_iso2 (if iso_to_wiki contains it)
      - wikixxx (e.g., Wikieng): via wiki_to_iso2
    """
    if not isinstance(suffix, str):
        return None
    s = suffix.strip()
    if not s:
        return None

    key = s.casefold()
    if key.startswith("wiki") and len(key) > 4:
        key = key[4:]

    if len(key) not in (2, 3) or not key.isalpha():
        return None

    iso2 = wiki_to_iso2.get(key)
    if isinstance(iso2, str) and len(iso2) == 2:
        return iso2

    if len(key) == 2 and key in iso_to_wiki:
        return key

    return None


def load_norm_maps(
    repo_root: Path,
    iso_map_rel: str = "config/iso_to_wiki.json",
) -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, str], Dict[str, str]]:
    """
    Convenience: load iso_to_wiki + build derived maps.

    The project historically used config/iso_to_wiki.json, but current layout keeps it
    at data/config/iso_to_wiki.json. This function auto-discovers the file.

    Returns:
      (iso_to_wiki, wiki_to_iso2, iso2_to_iso3, name_map_iso2)
    """
    iso_map_path = _discover_iso_map_path(repo_root, iso_map_rel)
    iso_to_wiki = load_iso_to_wiki(iso_map_path)
    wiki_to_iso2 = build_wiki_to_iso2(iso_to_wiki)
    iso2_to_iso3 = build_iso2_to_iso3(iso_to_wiki)
    name_map = build_name_map_iso2(iso_to_wiki, wiki_to_iso2)
    return iso_to_wiki, wiki_to_iso2, iso2_to_iso3, name_map

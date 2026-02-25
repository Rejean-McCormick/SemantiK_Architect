# tools/language_health/iso_map.py
#
# ISO 639-1 (iso2) <-> Wiki/RGL 3-letter code mapping loader.
#
# Reads iso_to_wiki.json when present and normalizes values such that:
#   {"en": "Eng", "fr": "Fre", "ar": "Ara"}
#
# Accepts values like "Eng", "WikiEng", "WikiEng.gf", or {"wiki": "..."}.
#
# Returns:
#   iso2_to_wiki: {"en": "Eng", ...}
#   wiki_to_iso2: {"Eng": "en", ...}
#   src_path: Path of the mapping file used (or None)

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

from .paths import ISO_TO_WIKI_CANDIDATES, REPO_ROOT

_WIKI_TOKEN_RE = re.compile(r"^[A-Za-z]{3,}$")


def _normalize_iso2(s: str) -> Optional[str]:
    s2 = (s or "").strip().lower()
    if len(s2) != 2 or not s2.isalpha():
        return None
    return s2


def _canonicalize_wiki(w: str) -> str:
    # Canonical 3-letter Wiki/RGL codes are typically TitleCase: "Eng", "Fre", "Ara"
    wl = w.lower()
    return wl[:1].upper() + wl[1:]


def _normalize_wiki_code(raw: str) -> Optional[str]:
    """
    Accepts "WikiEng", "Eng", "WikiEng.gf", etc. and returns canonical "Eng".
    """
    w = (raw or "").strip()
    if not w:
        return None

    wl = w.lower()
    if wl.startswith("wiki"):
        w = w[4:].strip()

    # tolerate "WikiEng.gf" or "Eng.gf"
    if w.lower().endswith(".gf"):
        w = w[:-3].strip()

    # tolerate accidental "WikiWikiEng"
    if w.lower().startswith("wiki"):
        w = w[4:].strip()

    if not w:
        return None

    # strip non-letters (defensive: e.g., "Eng " / "Eng," / "Eng\n")
    w_letters = "".join(ch for ch in w if ch.isalpha())
    if not w_letters:
        return None

    if not _WIKI_TOKEN_RE.match(w_letters):
        return None

    # Most mappings are 3 letters; if longer, keep but still canonicalize case
    return _canonicalize_wiki(w_letters)


def _default_candidates_for_root(root: Path) -> Tuple[Path, ...]:
    return (
        root / "data" / "config" / "iso_to_wiki.json",
        root / "config" / "iso_to_wiki.json",
    )


def load_iso_to_wiki(
    repo_root: Optional[Path] = None,
    candidates: Optional[Sequence[Path]] = None,
) -> Tuple[Dict[str, str], Dict[str, str], Optional[Path]]:
    """
    Returns:
      iso2_to_wiki: {"en": "Eng", "fr": "Fre", ...}
      wiki_to_iso2: {"Eng": "en", "Fre": "fr", ...}
      src: path of the file used, or None if not found

    Behavior:
    - ignores non-string keys
    - only accepts 2-letter iso2 keys
    - supports values as strings or objects containing {"wiki": "..."} (any truthy)
    - tolerates "WikiEng" / "WikiEng.gf" and normalizes to canonical TitleCase
    - on JSON parse error, returns empty maps but preserves src (so caller can warn)
    - wiki_to_iso2 is first-one-wins (stable)
    """
    root = (repo_root or REPO_ROOT).resolve()

    if candidates is None:
        # If caller supplied an alternate root, compute candidates from it.
        # Otherwise use the canonical candidates from paths.py (already repo-rooted).
        cand_seq = (
            tuple(ISO_TO_WIKI_CANDIDATES)
            if repo_root is None
            else _default_candidates_for_root(root)
        )
    else:
        cand_seq = tuple(candidates)

    src: Optional[Path] = None
    for p in cand_seq:
        try:
            pp = (root / p).resolve() if not p.is_absolute() else p.resolve()
            if pp.exists():
                src = pp
                break
        except Exception:
            continue

    if not src:
        return {}, {}, None

    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except Exception:
        return {}, {}, src

    iso2_to_wiki: Dict[str, str] = {}
    items = data.items() if isinstance(data, dict) else ()

    for iso2_raw, v in items:
        if not isinstance(iso2_raw, str):
            continue
        iso2 = _normalize_iso2(iso2_raw)
        if not iso2:
            continue

        wiki_raw: Optional[str] = None
        if isinstance(v, str):
            wiki_raw = v
        elif isinstance(v, dict):
            wv = v.get("wiki")
            if wv is not None and wv != "":
                wiki_raw = str(wv)

        if not wiki_raw:
            continue

        wiki = _normalize_wiki_code(wiki_raw)
        if not wiki:
            continue

        iso2_to_wiki[iso2] = wiki

    wiki_to_iso2: Dict[str, str] = {}
    for iso2, wiki in iso2_to_wiki.items():
        if wiki and wiki not in wiki_to_iso2:
            wiki_to_iso2[wiki] = iso2

    return iso2_to_wiki, wiki_to_iso2, src
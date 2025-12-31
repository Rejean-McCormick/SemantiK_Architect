# app/adapters/persistence/lexicon/index.py
# lexicon/index.py
"""
lexicon/index.py

Enterprise-grade in-memory index over lexicon data.

This index is designed to work with the current codebase reality:
- loader.load_lexicon(lang) returns a flattened mapping:
    Dict[surface_form, Dict[str, Any]]
  where each value is a feature bundle (pos, gender, qid, number, etc.).
- The public lexicon package expects:
    - lookup_by_lemma(lemma, pos=None) -> Lexeme|None
    - lookup_by_qid(qid) -> Lexeme|None
    - lookup_form(lemma, features, pos=None) -> Form|None

Design goals
------------
- No filesystem knowledge (loader handles I/O).
- Deterministic behavior; stable "first writer wins" semantics.
- Case-insensitive lookups, with optional robust normalization
  (underscores/spaces/dashes/punctuation) without mutating stored data.
- Minimal surface area used by engines/routers.

This module does not:
- lemmatize,
- perform fuzzy search,
- call Wikidata.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple

from .types import Form, Lexeme

try:
    from .normalization import normalize_for_lookup  # type: ignore
except Exception:  # pragma: no cover
    normalize_for_lookup = None  # type: ignore[assignment]


def _casefold(s: str) -> str:
    return s.casefold()


def _norm_key(s: str) -> str:
    if not isinstance(s, str):
        return ""
    if normalize_for_lookup is None:
        return s.strip().casefold()
    try:
        n = normalize_for_lookup(s)  # type: ignore[misc]
        return (n or s).strip().casefold()
    except Exception:
        return s.strip().casefold()


@dataclass
class LexiconIndex:
    """
    Index over a flattened lexicon mapping: surface_form -> features dict.

    Primary indices:
      - lemma index: (normalized lemma, pos?) -> Lexeme
      - qid index: normalized qid -> Lexeme
      - form lookup: best-effort from lemma + feature bundle

    Notes:
      - "lemma" in the loader output is represented by the surface_form keys.
        We treat keys as lemmas/surfaces and store them as Lexeme.lemma.
      - Feature bundles are stored in Lexeme.extra for compatibility.
      - Optional normalization adds robustness for lookup inputs.
    """

    lexemes: Dict[str, Dict[str, Any]]

    def __post_init__(self) -> None:
        if not isinstance(self.lexemes, dict):
            raise TypeError("LexiconIndex expects a dict mapping surface_form -> feature dict.")

        # (lemma_norm, pos_norm or None) -> Lexeme
        self._lemma_index: Dict[Tuple[str, Optional[str]], Lexeme] = {}
        # lemma_norm -> Lexeme (first writer wins) to support pos=None queries
        self._lemma_anypos_index: Dict[str, Lexeme] = {}
        # qid_norm -> Lexeme
        self._qid_index: Dict[str, Lexeme] = {}
        # Normalized key -> original surface key (first writer wins)
        self._surface_canon: Dict[str, str] = {}

        self._build()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build(self) -> None:
        for surface, feats in self.lexemes.items():
            if not isinstance(surface, str) or not surface.strip():
                continue
            if not isinstance(feats, Mapping):
                continue

            surface_raw = surface
            surface_norm = _norm_key(surface_raw)

            # keep first-writer-wins canonicalization
            if surface_norm and surface_norm not in self._surface_canon:
                self._surface_canon[surface_norm] = surface_raw

            pos_raw = feats.get("pos")
            pos_norm = _casefold(pos_raw) if isinstance(pos_raw, str) and pos_raw.strip() else None

            # Build Lexeme
            lex = Lexeme(
                key=surface_raw,
                lemma=surface_raw,
                pos=str(pos_raw) if isinstance(pos_raw, str) else (str(pos_raw) if pos_raw is not None else "UNKNOWN"),
                language=str(feats.get("lang") or feats.get("language") or ""),
                human=feats.get("human") if isinstance(feats.get("human"), bool) else None,
                gender=str(feats.get("gender")) if feats.get("gender") is not None else None,
                default_number=str(feats.get("default_number")) if feats.get("default_number") is not None else feats.get("number"),
                wikidata_qid=str(feats.get("qid") or feats.get("wikidata_qid")) if (feats.get("qid") or feats.get("wikidata_qid")) else None,
                forms=dict(feats.get("forms")) if isinstance(feats.get("forms"), Mapping) else {},
                extra=dict(feats),
            )

            # lemma indices
            key_any = (surface_norm, None)
            key_pos = (surface_norm, pos_norm)

            # First-writer-wins for exact-pos bucket and any-pos fallback.
            if surface_norm and surface_norm not in self._lemma_anypos_index:
                self._lemma_anypos_index[surface_norm] = lex

            if surface_norm:
                if pos_norm is not None:
                    if key_pos not in self._lemma_index:
                        self._lemma_index[key_pos] = lex
                else:
                    if key_any not in self._lemma_index:
                        self._lemma_index[key_any] = lex

            # qid index
            qid = lex.wikidata_qid
            if isinstance(qid, str) and qid.strip():
                qid_norm = _norm_key(qid)
                if qid_norm and qid_norm not in self._qid_index:
                    self._qid_index[qid_norm] = lex

    # ------------------------------------------------------------------
    # Public API expected by lexicon.__init__
    # ------------------------------------------------------------------

    def lookup_by_lemma(self, lemma: str, *, pos: Optional[str] = None) -> Optional[Lexeme]:
        if not isinstance(lemma, str) or not lemma.strip():
            return None

        lemma_norm = _norm_key(lemma)
        if not lemma_norm:
            return None

        if pos is not None and isinstance(pos, str) and pos.strip():
            pos_norm = _casefold(pos)
            hit = self._lemma_index.get((lemma_norm, pos_norm))
            if hit is not None:
                return hit

        # Fall back to any-POS match for that lemma
        hit = self._lemma_anypos_index.get(lemma_norm)
        if hit is not None:
            return hit

        # As a last resort, try stored "UNKNOWN"/None pos bucket
        return self._lemma_index.get((lemma_norm, None))

    def lookup_by_qid(self, qid: str) -> Optional[Lexeme]:
        if not isinstance(qid, str) or not qid.strip():
            return None
        qid_norm = _norm_key(qid)
        if not qid_norm:
            return None
        return self._qid_index.get(qid_norm)

    def lookup_form(
        self,
        *,
        lemma: str,
        features: Optional[Dict[str, Any]] = None,
        pos: Optional[str] = None,
    ) -> Optional[Form]:
        """
        Best-effort form lookup from a lemma + features.

        Current flattened loader schema commonly provides:
          - "number" from the expanded tag (sg/pl)
          - "gender" refined from tag (m/f/etc)
          - sometimes "forms" is present on the lemma entry (less common in current loader)

        Strategy:
          1) resolve lexeme by lemma (+ optional pos)
          2) if lexeme.forms exists and features suggest a key like "f.sg" or "sg", use it
          3) else try to find a surface form in the flattened mapping that matches
             requested (pos, gender, number) and shares the same qid if available
          4) fall back to the lemma itself if nothing else fits
        """
        if not isinstance(lemma, str) or not lemma.strip():
            return None

        features = features or {}
        lex = self.lookup_by_lemma(lemma, pos=pos)
        if lex is None:
            # Still allow "raw" lookups: maybe the lemma is already a surface form
            lex = self.lookup_by_lemma(lemma, pos=None)
        if lex is None:
            return None

        req_gender = features.get("gender")
        req_number = features.get("number")

        gender = str(req_gender) if req_gender is not None else None
        number = str(req_number) if req_number is not None else None

        # 2) direct forms map (if present)
        if lex.forms:
            # Most common composite keys: "f.sg" / "m.pl"
            if gender and number:
                k = f"{gender}.{number}"
                if k in lex.forms and isinstance(lex.forms[k], str):
                    return Form(surface=lex.forms[k], features={"gender": gender, "number": number})
            if number and number in lex.forms and isinstance(lex.forms[number], str):
                return Form(surface=lex.forms[number], features={"number": number})
            if gender and gender in lex.forms and isinstance(lex.forms[gender], str):
                return Form(surface=lex.forms[gender], features={"gender": gender})

        # 3) search flattened mapping for matching surface with same qid (if known)
        qid = lex.wikidata_qid
        pos_norm = _casefold(pos) if isinstance(pos, str) and pos.strip() else None

        best_surface: Optional[str] = None

        for surface, feats in self.lexemes.items():
            if not isinstance(surface, str) or not isinstance(feats, Mapping):
                continue

            # Must share qid if we have one; otherwise skip this constraint
            cand_qid = feats.get("qid") or feats.get("wikidata_qid")
            if qid and isinstance(cand_qid, str) and cand_qid.strip():
                if _norm_key(cand_qid) != _norm_key(qid):
                    continue
            elif qid:
                continue  # if lex has qid, require candidate qid too

            # POS constraint if provided
            if pos_norm is not None:
                cand_pos = feats.get("pos")
                cand_pos_norm = _casefold(cand_pos) if isinstance(cand_pos, str) and cand_pos.strip() else None
                if cand_pos_norm != pos_norm:
                    continue

            # Feature constraints
            if gender is not None:
                cand_gender = feats.get("gender")
                if cand_gender is None or str(cand_gender) != gender:
                    continue
            if number is not None:
                cand_number = feats.get("number") or feats.get("default_number")
                if cand_number is None or str(cand_number) != number:
                    continue

            best_surface = surface
            break  # first-writer-wins / deterministic traversal order depends on dict order

        if best_surface:
            out_features: Dict[str, Any] = {}
            if gender is not None:
                out_features["gender"] = gender
            if number is not None:
                out_features["number"] = number
            return Form(surface=best_surface, features=out_features)

        # 4) fallback to lemma itself
        return Form(surface=lex.lemma, features={k: v for k, v in (("gender", gender), ("number", number)) if v is not None})


__all__ = ["LexiconIndex"]

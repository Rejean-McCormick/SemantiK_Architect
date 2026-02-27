# app/adapters/engines/gf_engine.py
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Optional, Any, Dict

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import structlog
import pgf  # GF Python Bindings

from app.core.domain.models import Frame, Sentence
from app.core.domain.exceptions import LanguageNotReadyError, DomainError, ExternalServiceError
from app.core.ports.grammar_engine import IGrammarEngine
from app.shared.config import settings

logger = structlog.get_logger()

GF_TIMEOUT_SECONDS = 30

# Exceptions we will retry on (e.g., transient network/GF errors)
RETRYABLE_EXCEPTIONS = (ExternalServiceError, subprocess.TimeoutExpired)


def _normalize_pgf_path(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return value
    if value.endswith(("/", "\\")) or not value.lower().endswith(".pgf"):
        return os.path.join(value, "semantik_architect.pgf")
    return value


def _effective_pgf_path() -> str:
    """
    Prefer explicit env overrides (containers/tests), then validated settings.
    Supports both PGF_PATH (preferred) and legacy AW_PGF_PATH.
    """
    env_path = os.getenv("PGF_PATH") or os.getenv("AW_PGF_PATH")
    if env_path:
        return _normalize_pgf_path(env_path)
    return _normalize_pgf_path(getattr(settings, "PGF_PATH", "") or "")


def _repo_root() -> Path:
    for attr in ("REPO_ROOT", "ROOT_DIR", "PROJECT_ROOT"):
        if hasattr(settings, attr):
            val = getattr(settings, attr)
            if val:
                return Path(val).resolve()
    # .../app/adapters/engines/gf_engine.py -> repo root is typically 4 levels up
    return Path(__file__).resolve().parents[3]


def _load_iso_to_wiki_map() -> Dict[str, Any]:
    """
    Load ISO->Wiki mapping from data/config/iso_to_wiki.json (canonical),
    falling back to gf/data/config/iso_to_wiki.json (legacy).
    """
    root = _repo_root()
    candidates = [
        root / "data" / "config" / "iso_to_wiki.json",
        root / "gf" / "data" / "config" / "iso_to_wiki.json",
    ]
    for p in candidates:
        try:
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    logger.info("iso_map_loaded", path=str(p), entries=len(data))
                    return data
        except Exception as e:
            logger.warning("iso_map_load_failed", path=str(p), error=str(e))
    logger.warning("iso_map_missing", tried=[str(p) for p in candidates])
    return {}


def _extract_wiki_suffix(raw_val: Any) -> Optional[str]:
    """
    iso_to_wiki.json values may be:
      - "WikiEng" or "Eng"
      - {"wiki": "WikiEng", ...}
    Returns suffix like "Eng".
    """
    if raw_val is None:
        return None
    if isinstance(raw_val, dict):
        raw_val = raw_val.get("wiki")
    if raw_val is None:
        return None
    s = str(raw_val).strip()
    if not s:
        return None
    return s.replace("Wiki", "").strip() or None


class GFEngine(IGrammarEngine):
    """
    Adapter implementation for IGrammarEngine using the Grammatical Framework (GF)
    C++ library via the Python 'pgf' bindings.
    """

    def __init__(self):
        self._iso_map: Dict[str, Any] = _load_iso_to_wiki_map()
        # Build reverse lookup: "Eng" -> "en"
        self._wiki_to_iso2: Dict[str, str] = {}
        for k, v in self._iso_map.items():
            suf = _extract_wiki_suffix(v)
            if suf:
                self._wiki_to_iso2[suf] = str(k).lower()

        self._pgf = self._load_pgf()
        self._supported_gf_langs = self._get_supported_gf_langs()
        self._supported_languages = self._get_supported_languages()  # ISO2 where possible

    def _load_pgf(self) -> Optional[pgf.PGF]:
        """Loads the master PGF file (semantik_architect.pgf) into memory."""
        pgf_file = _effective_pgf_path()
        if not pgf_file or not os.path.exists(pgf_file):
            logger.error("pgf_file_missing", path=pgf_file or "(empty)")
            return None

        try:
            pgf_grammar = pgf.readPGF(pgf_file)
            logger.info("pgf_loaded", path=pgf_file, languages=len(pgf_grammar.languages))
            return pgf_grammar
        except Exception as e:
            logger.error("pgf_load_failed", path=pgf_file, error=str(e))
            return None

    def _get_supported_gf_langs(self) -> set[str]:
        """Raw GF concrete module names: {'WikiEng', 'WikiGer', ...}."""
        if self._pgf:
            return set(self._pgf.languages.keys())
        return set()

    def _get_supported_languages(self) -> set[str]:
        """
        Preferred output: ISO-2 codes (e.g. {'en','de',...}) when iso_to_wiki.json provides a reverse map.
        Fallback: wiki suffix lowercased (e.g. {'eng','ger',...}) if reverse map is unavailable.
        """
        out: set[str] = set()
        for name in self._supported_gf_langs:
            suf = str(name).replace("Wiki", "").strip()
            if not suf:
                continue
            iso2 = self._wiki_to_iso2.get(suf)
            out.add(iso2 if iso2 else suf.lower())
        return out

    def _gf_lang_name(self, lang_code: str) -> str:
        """
        Convert incoming language code into a GF concrete module name.
        Accepts:
          - ISO2 ('de')
          - existing wiki suffix ('Ger')
          - existing GF module name ('WikiGer')
        """
        code = (lang_code or "").strip()
        if not code:
            return "WikiUnknown"

        if code.startswith("Wiki") and len(code) > 4:
            return code

        # Try authoritative iso_to_wiki.json mapping first (keyed by ISO2 in this project)
        raw_val = self._iso_map.get(code) or self._iso_map.get(code.lower())
        suf = _extract_wiki_suffix(raw_val)

        # If mapping isn't present, fall back to TitleCase heuristic
        if not suf:
            suf = code.replace("Wiki", "").strip().title()

        return f"Wiki{suf}"

    def is_language_ready(self, lang_code: str) -> bool:
        """Checks if the required concrete syntax is loaded in the PGF."""
        if not self._pgf:
            return False
        gf_lang_name = self._gf_lang_name(lang_code)
        return gf_lang_name in self._pgf.languages

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        reraise=True,
    )
    async def generate(self, lang_code: str, frame: Frame) -> Sentence:
        """Converts the semantic Frame into text using the GF engine."""
        if not self._pgf:
            raise ExternalServiceError("GF Engine is not initialized. PGF file missing or corrupt.")

        gf_lang_name = self._gf_lang_name(lang_code)

        if gf_lang_name not in self._pgf.languages:
            raise LanguageNotReadyError(
                f"Language '{lang_code}' not found (expected concrete '{gf_lang_name}')."
            )

        # 1) Map Frame -> AST
        try:
            ast_string = self._map_frame_to_ast(frame)
            if not ast_string:
                raise DomainError(f"Frame mapping failed for type: {frame.frame_type}")
            ast_expr = pgf.readExpr(ast_string)
        except Exception as e:
            logger.error("ast_mapping_failed", frame_type=frame.frame_type, error=str(e))
            raise DomainError(f"Failed to convert frame to AST: {str(e)}")

        # 2) Linearization
        concrete_syntax = self._pgf.languages[gf_lang_name]
        try:
            text = concrete_syntax.linearize(ast_expr)

            return Sentence(
                text=text,
                lang_code=lang_code,
                source_engine="gf",
            )
        except pgf.ParseError as e:
            logger.error("gf_linearization_failed", lang=lang_code, ast=ast_string, error=str(e))
            raise DomainError(f"GF Linearization failed (ParseError): {str(e)}")
        except Exception as e:
            logger.error("gf_runtime_error", lang=lang_code, error=str(e))
            raise ExternalServiceError(f"GF Runtime Error during linearization: {str(e)}")

    def _map_frame_to_ast(self, frame: Frame) -> Optional[str]:
        """
        [PLACEHOLDER] Maps a Pydantic Frame object into a GF Abstract Syntax Tree string.
        """
        if frame.frame_type == "bio":
            concept = frame.subject.get("name", "John")
            return f"SimpNP {concept}_N"
        return None

    async def health_check(self) -> bool:
        """Verifies the engine is initialized and the PGF file is accessible."""
        is_ready = self._pgf is not None and bool(self._supported_gf_langs)
        if not is_ready:
            logger.warning("gf_health_check_failed", reason="PGF not loaded or no languages found")
        return is_ready
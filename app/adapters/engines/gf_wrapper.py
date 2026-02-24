# app/adapters/engines/gf_wrapper.py
import asyncio
import json
import os
import threading
import structlog
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pgf
except ImportError:
    pgf = None

from app.core.domain.frame import BioFrame
from app.core.domain.models import Frame, Sentence
from app.shared.config import settings

logger = structlog.get_logger()


class GFGrammarEngine:
    """
    Primary Grammar Engine using the compiled PGF binary.

    Key runtime behavior:
    - Async (API server): lazy-load via await _ensure_grammar() (non-blocking startup).
    - Sync (CLI/tools): first access to .grammar triggers a safe synchronous load.
      This fixes tools like universal_test_runner which check engine.grammar is not None.
    """

    # Accept common external frame types that represent “person bio” payloads
    _BIO_FRAME_TYPES = {
        "bio",
        "biography",
        "entity.person",
        "entity_person",
        "person",
        "entity.person.v1",
        "entity.person.v2",
    }

    def __init__(self, lib_path: str | None = None):
        # NOTE: lib_path kept for compatibility; PGF path is controlled by env/settings.
        # IMPORTANT: read os.environ first so CLI/tool overrides (e.g. universal_test_runner --pgf) work reliably.
        configured = (
            os.getenv("PGF_PATH")
            or getattr(settings, "PGF_PATH", None)
            or os.getenv("AW_PGF_PATH")
            or getattr(settings, "AW_PGF_PATH", "gf/AbstractWiki.pgf")
        )
        self.pgf_path: str = str(self._resolve_path(configured))

        # Internal storage (do NOT access directly outside this file)
        self._grammar: Optional[Any] = None

        self.inventory: Dict[str, Any] = {}
        self.iso_map: Dict[str, str] = {}

        # ✅ Diagnostics (so callers can explain WHY it's unavailable)
        self.last_load_error: Optional[str] = None
        self.last_load_error_type: Optional[str] = None  # "pgf_missing" | "pgf_file_missing" | "pgf_read_failed"

        # Concurrency controls:
        # - async lock prevents concurrent loads in event loop
        # - thread lock prevents concurrent loads across threads/process tool runners
        self._async_load_lock: asyncio.Lock = asyncio.Lock()
        self._thread_load_lock: threading.Lock = threading.Lock()

        self._load_inventory()
        self._load_iso_config()
        # DEFERRED: load happens lazily. Sync tools will load on first .grammar access.

    # ----------------------------
    # Path helpers
    # ----------------------------
    def _resolve_path(self, p: str | Path) -> Path:
        """
        Resolve PGF path robustly for:
        - API server (cwd may vary)
        - GUI/tool runner subprocess (cwd may vary)
        - CLI overrides via env (may pass a directory)
        """
        path = Path(p)

        # If a directory is provided, assume AbstractWiki.pgf inside it.
        if path.exists() and path.is_dir():
            path = path / "AbstractWiki.pgf"

        if path.is_absolute():
            return path

        base = getattr(settings, "FILESYSTEM_REPO_PATH", None)
        if base:
            return (Path(base) / path).resolve()

        # Fallback: project root (app/.. -> repo root)
        project_root = Path(__file__).resolve().parents[3]
        return (project_root / path).resolve()

    # ----------------------------
    # Grammar access (the key fix)
    # ----------------------------
    @property
    def grammar(self) -> Optional[Any]:
        """
        Returns the loaded grammar.

        - In sync contexts (no running event loop): auto-loads on first access.
        - In async contexts: never blocks; returns None until async load is done.
        """
        if self._grammar is not None:
            return self._grammar

        # If we're inside a running event loop, do NOT block.
        try:
            asyncio.get_running_loop()
            return None
        except RuntimeError:
            # No running loop => safe to load synchronously (tools/CLI)
            self._load_grammar_sync()
            return self._grammar

    @grammar.setter
    def grammar(self, value: Optional[Any]) -> None:
        self._grammar = value

    # ----------------------------
    # Loading helpers
    # ----------------------------
    def _load_inventory(self) -> None:
        try:
            candidates: list[Path] = []
            if settings and getattr(settings, "FILESYSTEM_REPO_PATH", None):
                repo_root = Path(settings.FILESYSTEM_REPO_PATH)
                candidates.append(repo_root / "data" / "indices" / "rgl_inventory.json")

            candidates.append(Path(__file__).resolve().parents[3] / "data" / "indices" / "rgl_inventory.json")

            inventory_path: Optional[Path] = None
            for p in candidates:
                if p.exists():
                    inventory_path = p
                    break

            if inventory_path:
                with inventory_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.inventory = data.get("languages", {}) or {}
        except Exception:
            self.inventory = {}

    def _load_iso_config(self) -> None:
        try:
            candidates: list[Path] = []
            if settings and getattr(settings, "FILESYSTEM_REPO_PATH", None):
                repo_root = Path(settings.FILESYSTEM_REPO_PATH)
                candidates.append(repo_root / "data" / "config" / "iso_to_wiki.json")
                candidates.append(repo_root / "config" / "iso_to_wiki.json")

            project_root = Path(__file__).resolve().parents[3]
            candidates.append(project_root / "data" / "config" / "iso_to_wiki.json")
            candidates.append(project_root / "config" / "iso_to_wiki.json")

            config_path: Optional[Path] = None
            for p in candidates:
                if p.exists():
                    config_path = p
                    break

            if not config_path:
                self.iso_map = {}
                return

            with config_path.open("r", encoding="utf-8") as f:
                raw_data = json.load(f)

            # Normalize to: iso(lower) -> wiki suffix (e.g., "Eng", "Ger", "Fra", "Deu")
            iso_map: Dict[str, str] = {}
            for code, value in (raw_data or {}).items():
                if not isinstance(code, str):
                    continue
                key = code.lower().strip()
                if not key:
                    continue

                if isinstance(value, dict):
                    suffix = value.get("wiki")
                    if isinstance(suffix, str) and suffix.strip():
                        iso_map[key] = suffix.strip().replace("Wiki", "")
                elif isinstance(value, str) and value.strip():
                    iso_map[key] = value.strip().replace("Wiki", "")

            self.iso_map = iso_map
        except Exception:
            self.iso_map = {}

    def _load_grammar_sync(self) -> None:
        """
        Synchronous method to load the heavy PGF binary.
        Sets detailed diagnostics so callers can report actionable failures.

        Thread-safe: multiple threads/tools won't race-load.
        """
        with self._thread_load_lock:
            # Double-check inside lock
            if self._grammar is not None:
                return

            # reset last error on every attempt
            self.last_load_error = None
            self.last_load_error_type = None

            if not pgf:
                self._grammar = None
                self.last_load_error_type = "pgf_missing"
                self.last_load_error = "Python module 'pgf' is not installed/available in this runtime."
                logger.error("pgf_module_missing")
                return

            path = Path(self.pgf_path)
            if path.exists() and path.is_dir():
                path = path / "AbstractWiki.pgf"

            if not path.exists():
                self._grammar = None
                self.last_load_error_type = "pgf_file_missing"
                self.last_load_error = f"PGF file not found at: {path}"
                logger.error("pgf_file_missing", pgf_path=str(path))
                return

            try:
                logger.info("loading_pgf_binary", path=str(path))
                self._grammar = pgf.readPGF(str(path))
                logger.info(
                    "pgf_binary_loaded_successfully",
                    language_count=len(getattr(self._grammar, "languages", {}) or {}),
                )
            except Exception as e:
                self._grammar = None
                self.last_load_error_type = "pgf_read_failed"
                self.last_load_error = f"pgf.readPGF failed: {e}"
                logger.error("gf_load_failed", error=str(e), pgf_path=str(path))

    async def _ensure_grammar(self) -> None:
        """
        Ensures the grammar is loaded without blocking the async event loop.
        """
        if self._grammar is not None:
            return

        async with self._async_load_lock:
            if self._grammar is None:
                await asyncio.to_thread(self._load_grammar_sync)

    # ----------------------------
    # Public API (IGrammarEngine)
    # ----------------------------
    async def status(self) -> Dict[str, Any]:
        """
        Tool-friendly status for diagnostics and demos.
        Safe to call repeatedly.
        """
        await self._ensure_grammar()
        payload: Dict[str, Any] = {
            "loaded": self._grammar is not None,
            "pgf_path": str(self.pgf_path),
            "error_type": self.last_load_error_type,
            "error": self.last_load_error,
        }
        if self._grammar is not None:
            payload["language_count"] = len(getattr(self._grammar, "languages", {}) or {})
        return payload

    async def generate(self, lang_code: str, frame: Any) -> Sentence:
        """
        Generate text from:
          - BioFrame
          - Frame (domain)
          - dict (either BioFrame-like payload or Ninai/UniversalNode)
        """
        await self._ensure_grammar()

        if not self._grammar:
            dbg = {
                "pgf_path": str(self.pgf_path),
                "error_type": self.last_load_error_type,
                "error": self.last_load_error,
            }
            return Sentence(text="<GF Runtime Not Loaded>", lang_code=lang_code, debug_info=dbg)

        # 1) Ninai/UniversalNode dict
        if isinstance(frame, dict) and ("function" in frame or "args" in frame):
            ast_str = self._convert_to_gf_ast(frame, lang_code)
            text = self.linearize(ast_str, lang_code)
            if not text:
                text = "<LinearizeError>"
            return Sentence(text=text, lang_code=lang_code, debug_info={"ast": ast_str})

        # 2) Bio-ish domain object or dict payload
        bio = self._coerce_to_bio_frame(frame)
        ast_str = self._convert_to_gf_ast(bio, lang_code)
        text = self.linearize(ast_str, lang_code)

        if not text or text.strip() in {"[]", ""}:
            name = (bio.name or "").strip() or "<Unknown>"
            text = name

        return Sentence(text=text, lang_code=lang_code, debug_info={"ast": ast_str})

    def parse(self, sentence: str, language: str):
        # Sync parse: ensure grammar exists (this will auto-load in sync contexts via property)
        g = self.grammar
        if not g:
            return []

        language_resolved = self._resolve_concrete_name(language)
        if not language_resolved:
            return []

        concrete_grammar = g.languages[language_resolved]
        try:
            return concrete_grammar.parse(sentence)
        except Exception:
            return []

    def linearize(self, expr: Any, language: str) -> str:
        # Sync linearize: ensure grammar exists (auto-loads in sync contexts)
        g = self.grammar
        if not g:
            return "<GF Runtime Not Loaded>"

        language_resolved = self._resolve_concrete_name(language)
        if not language_resolved:
            return f"<Language '{language}' not found>"

        concrete_grammar = g.languages[language_resolved]

        if isinstance(expr, str):
            try:
                expr_obj = pgf.readExpr(expr) if pgf else expr
            except Exception as e:
                return f"<LinearizeError: {e}>"
        else:
            expr_obj = expr

        try:
            return concrete_grammar.linearize(expr_obj)
        except Exception as e:
            return f"<LinearizeError: {e}>"

    async def get_supported_languages(self) -> List[str]:
        await self._ensure_grammar()
        if not self._grammar:
            return []
        return list(self._grammar.languages.keys())

    async def reload(self) -> None:
        self._load_inventory()
        self._load_iso_config()

        async with self._async_load_lock:
            with self._thread_load_lock:
                self._grammar = None
                self.last_load_error = None
                self.last_load_error_type = None

        await self._ensure_grammar()

    async def health_check(self) -> bool:
        await self._ensure_grammar()
        return self._grammar is not None

    # ----------------------------
    # Language resolution
    # ----------------------------
    def _resolve_concrete_name(self, lang_code: str) -> Optional[str]:
        """
        Robustly resolve external language inputs (iso2/iso3/wiki codes) into a concrete
        PGF language key present in grammar.languages.

        Tries, in order:
        - exact match (case-sensitive)
        - case-insensitive exact match
        - iso_to_wiki mapping (e.g. "de" -> "Ger" => "WikiGer")
        - inventory iso3 mapping (e.g. "de" -> "deu" => "WikiDeu")
        - direct iso3 fallback (e.g. "deu" => "WikiDeu")
        - heuristic suffix matching across available grammar.languages
        """
        g = self._grammar
        if not g:
            return None

        raw = (lang_code or "").strip()
        if not raw:
            return None

        # 0) Exact match
        if raw in g.languages:
            return raw

        # 1) Case-insensitive exact match
        lower_to_key = {k.lower(): k for k in g.languages.keys()}
        raw_lower = raw.lower()
        if raw_lower in lower_to_key:
            return lower_to_key[raw_lower]

        iso_clean = raw_lower

        # Helper to try a list of candidates (case-sensitive first, then case-insensitive)
        def _try_candidates(cands: List[str]) -> Optional[str]:
            for c in cands:
                if not c:
                    continue
                if c in g.languages:
                    return c
                c_low = c.lower()
                if c_low in lower_to_key:
                    return lower_to_key[c_low]
            return None

        suffix = self.iso_map.get(iso_clean)
        iso3 = None

        # Pull iso3 from inventory when available (inventory keys are often iso2)
        inv = self.inventory.get(iso_clean)
        if isinstance(inv, dict):
            iso3_val = inv.get("iso3") or inv.get("iso_639_3")
            if isinstance(iso3_val, str) and iso3_val.strip():
                iso3 = iso3_val.strip().lower()

        # Also accept inventory keyed by iso3
        if iso3 is None and len(iso_clean) == 3:
            iso3 = iso_clean

        # 2) iso_to_wiki mapping (might be "Ger"/"Fre"/"Fra"/"Deu", etc)
        if suffix:
            # Try common shapes: "Wiki{Suffix}", plain suffix, and capitalization variants
            cands = []
            s = suffix.strip()
            if s:
                cands.append(s)
                cands.append(s.capitalize())
                cands.append(s.upper())
                cands.append(s.lower())
                cands.append(f"Wiki{s}")
                cands.append(f"Wiki{s.capitalize()}")
            hit = _try_candidates(cands)
            if hit:
                return hit

        # 3) iso3-based mapping (often matches actual concrete module names in this repo: WikiDeu, WikiFra, etc)
        if iso3:
            cands = [
                f"Wiki{iso3.capitalize()}",
                iso3,
                iso3.upper(),
                iso3.lower(),
            ]
            hit = _try_candidates(cands)
            if hit:
                return hit

        # 4) Heuristic: find any available language key ending with mapped suffix / iso3
        # (useful when PGF contains WikiDeu but iso_to_wiki maps "de" -> "Ger", or vice-versa)
        probes: List[str] = []
        if suffix:
            probes.append(suffix.lower())
        if iso3:
            probes.append(iso3.lower())

        for p in probes:
            for k in g.languages.keys():
                kl = k.lower()
                if kl.endswith(p):
                    return k
                if kl.endswith(f"wiki{p}"):
                    return k

        return None

    # ----------------------------
    # Conversion helpers
    # ----------------------------
    @staticmethod
    def _escape_gf_str(s: str) -> str:
        return (s or "").replace("\\", "\\\\").replace('"', '\\"')

    def _coerce_to_bio_frame(self, obj: Any) -> BioFrame:
        if isinstance(obj, BioFrame):
            return obj

        if isinstance(obj, Frame):
            return BioFrame(
                frame_type="bio",
                subject=obj.subject,
                properties=getattr(obj, "properties", {}) or {},
                context_id=getattr(obj, "context_id", "") or "",
                meta=getattr(obj, "meta", {}) or {},
            )

        if isinstance(obj, dict):
            frame_type_raw = obj.get("frame_type") or obj.get("type") or ""
            frame_type = str(frame_type_raw).lower().strip() if frame_type_raw is not None else ""

            # “looks like a bio/person payload” heuristic for external tools/tests
            looks_like_person = any(k in obj for k in ("name", "profession", "nationality", "gender", "subject"))

            if frame_type in self._BIO_FRAME_TYPES or (frame_type.startswith("entity.") and "person" in frame_type) or looks_like_person:
                subject = obj.get("subject") if isinstance(obj.get("subject"), dict) else {}
                props = obj.get("properties") if isinstance(obj.get("properties"), dict) else {}

                # Support “flat” convenience keys (used by Tools Command Center + API payloads)
                if isinstance(subject, dict):
                    if obj.get("name"):
                        subject = {**subject, "name": obj.get("name")}
                    if obj.get("profession"):
                        subject = {**subject, "profession": obj.get("profession")}
                    if obj.get("nationality"):
                        subject = {**subject, "nationality": obj.get("nationality")}
                    if obj.get("gender"):
                        subject = {**subject, "gender": obj.get("gender")}

                return BioFrame(
                    frame_type="bio",
                    subject=subject,
                    properties=props,
                    context_id=obj.get("context_id") or "",
                    meta=obj.get("meta") or {},
                )

        raise ValueError("Unsupported frame payload for Bio generation")

    def _bio_fields(self, frame: BioFrame) -> tuple[str, Optional[str], Optional[str], Optional[str]]:
        name = (getattr(frame, "name", None) or "").strip()
        gender = getattr(frame, "gender", None)

        profession = None
        nationality = None

        subj = getattr(frame, "subject", None)
        if isinstance(subj, dict):
            profession = subj.get("profession")
            nationality = subj.get("nationality")
            if not name:
                name = (subj.get("name") or "").strip()
            if gender is None:
                gender = subj.get("gender")
        else:
            profession = getattr(subj, "profession", None)
            nationality = getattr(subj, "nationality", None)
            if not name:
                name = (getattr(subj, "name", None) or "").strip()
            if gender is None:
                gender = getattr(subj, "gender", None)

        return name, profession, nationality, gender

    def _convert_to_gf_ast(self, node: Any, lang_code: str) -> str:
        if isinstance(node, BioFrame):
            name, prof, nat, _gender = self._bio_fields(node)
            name_esc = self._escape_gf_str(name or "Unknown")
            prof_esc = self._escape_gf_str(prof or "person")
            nat_esc = self._escape_gf_str(nat or "")

            entity = f'mkEntityStr "{name_esc}"'
            prof_expr = f'strProf "{prof_esc}"'

            if nat_esc:
                nat_expr = f'strNat "{nat_esc}"'
                return f"mkBioFull ({entity}) ({prof_expr}) ({nat_expr})"

            return f"mkBioProf ({entity}) ({prof_expr})"

        if isinstance(node, dict):
            func = node.get("function")
            if not func:
                raise ValueError("Missing function attribute")

            args = node.get("args", [])
            processed = [self._convert_to_gf_ast(a, lang_code) for a in (args or [])]

            def needs_parens(expr: str) -> bool:
                expr = (expr or "").strip()
                if not expr:
                    return False
                if expr.startswith('"') and expr.endswith('"'):
                    return False
                if " " in expr or expr.startswith("("):
                    return True
                return False

            arg_str = " ".join([f"({a})" if needs_parens(a) else a for a in processed]).strip()
            candidate = f"{func} {arg_str}".strip()

            if func == "mkCl":
                if self._linearizes_as_placeholder(candidate, lang_code):
                    return self._flatten_ninai_to_literal(node)

            return candidate

        if isinstance(node, str):
            return f'"{self._escape_gf_str(node)}"'
        if node is None:
            return '""'
        return f'"{self._escape_gf_str(str(node))}"'

    def _linearizes_as_placeholder(self, expr_str: str, lang_code: str) -> bool:
        if not (self._grammar and pgf):
            return False

        conc_name = self._resolve_concrete_name(lang_code)
        if not conc_name or conc_name not in self._grammar.languages:
            return False

        try:
            expr_obj = pgf.readExpr(expr_str)
            out = self._grammar.languages[conc_name].linearize(expr_obj)
        except Exception:
            return True

        out_s = (out or "").strip()
        return (out_s.startswith("[") and out_s.endswith("]")) or ("[mkCl]" in out_s)

    def _flatten_ninai_to_literal(self, node: Any) -> str:
        tokens: list[str] = []

        def walk(n: Any) -> None:
            if isinstance(n, dict):
                fn = n.get("function")
                if isinstance(fn, str) and fn:
                    tokens.append(fn)
                for a in (n.get("args") or []):
                    walk(a)
            elif isinstance(n, str):
                if n:
                    tokens.append(n)
            else:
                if n is not None:
                    tokens.append(str(n))

        walk(node)
        joined = " ".join(tokens).strip() or "unsupported"
        return f'"{self._escape_gf_str(joined)}"'
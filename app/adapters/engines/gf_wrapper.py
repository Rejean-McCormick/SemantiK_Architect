# app/adapters/engines/gf_wrapper.py
import sys
import structlog
from typing import List, Optional, Any
from pathlib import Path

try:
    import pgf
except ImportError:
    pgf = None

from app.core.ports.grammar_engine import IGrammarEngine
from app.core.domain.models import Sentence
from app.core.domain.exceptions import (
    LanguageNotFoundError, 
    DomainError
)
from app.shared.config import settings
# NEW: Import the Cache Manager for the "Lemma-First" architecture
from app.services.lexicon_store import LexiconStore

logger = structlog.get_logger()

class GFGrammarEngine(IGrammarEngine):
    """
    Primary Grammar Engine using the compiled PGF binary.
    Supports Dual-Path: Strict Ninai and Prototype UniversalNode.
    Integrated with LexiconStore for "Lemma-First" QID resolution.
    """

    def __init__(self, lib_path: str = None):
        self.pgf_path = settings.PGF_PATH
        self.grammar: Optional[pgf.PGF] = None
        
        print(f"[DEBUG] GFGrammarEngine initializing from: {self.pgf_path}")
        self._load_grammar()

    def _load_grammar(self):
        """Loads the .pgf file into memory."""
        if not pgf:
            logger.warning("gf_runtime_missing", msg="pgf library not installed.")
            return

        path = Path(self.pgf_path)
        if path.exists():
            try:
                self.grammar = pgf.readPGF(str(path))
                logger.info("gf_grammar_loaded", path=str(path))
            except Exception as e:
                logger.error("gf_load_failed", error=str(e))
        else:
            logger.error("gf_file_not_found", path=str(path))

    async def generate(self, lang_code: str, frame: Any) -> Sentence:
        """
        Generates text from an abstract frame (Ninai or UniversalNode).
        """
        if not self.grammar:
            raise DomainError("GF Runtime is not loaded.")

        # 1. Resolve Concrete Language
        conc_name = self._resolve_concrete_name(lang_code)
        if not conc_name:
            avail = list(self.grammar.languages.keys())
            raise LanguageNotFoundError(f"Language '{lang_code}' not found. Available: {avail}")
        
        concrete = self.grammar.languages[conc_name]

        # 2. Construct GF AST String (The Bridge)
        try:
            # UPDATED: Pass lang_code to allow Lexicon resolution during conversion
            expr_str = self._convert_to_gf_ast(frame, lang_code)
        except Exception as e:
            logger.error("gf_ast_conversion_failed", error=str(e))
            raise DomainError(f"Failed to convert frame to GF AST: {str(e)}")

        # 3. Parse and Linearize
        try:
            # Parse the string command into a PGF Expression
            # e.g. "mkFact (mkLiteral "Sky") (mkProp "Blue")"
            expr = pgf.readExpr(expr_str)
            
            # Linearize
            text = concrete.linearize(expr)
        except Exception as e:
            logger.error("gf_linearization_failed", lang=conc_name, command=expr_str, error=str(e))
            raise DomainError(f"Linearization failed for command '{expr_str}': {str(e)}")

        return Sentence(
            text=text,
            lang_code=lang_code,
            debug_info={
                "engine": "gf_rgl",
                "concrete_grammar": conc_name,
                "command": expr_str
            }
        )

    def _resolve_concrete_name(self, lang_code: str) -> Optional[str]:
        target_suffix = lang_code.capitalize() 
        candidate = f"Wiki{target_suffix}"
        if candidate in self.grammar.languages:
            return candidate
        for name in self.grammar.languages.keys():
            if name.endswith(target_suffix):
                return name
        return None

    def _convert_to_gf_ast(self, node: Any, lang_code: str) -> str:
        """
        Recursively converts the input object (Ninai or UniversalNode) into a GF linearize command.
        Now resolves Q-IDs via LexiconStore.
        
        Example Input:  mkN("Q42")
        Example Output: mkN "Douglas Adams"
        """
        # A. Handle Primitives (Strings/Ints)
        if isinstance(node, (str, int, float)):
            s_node = str(node)
            
            # NEW: Resolve QID/Concept to Lemma using the Store
            # If s_node is "Q42", this returns "Douglas Adams"
            # If s_node is "Sky", it returns "Sky" (or localized version if in lexicon)
            lemma = LexiconStore.get_lemma(lang_code, s_node)

            # Smart Quoting for GF
            # If it's a number, return as is (GF treats ints as literals)
            if lemma.replace('.', '', 1).isdigit():
                return lemma
            
            # If it's already quoted, trust it
            if lemma.startswith('"'):
                return lemma
                
            # Otherwise, force quotes. This ensures "Douglas Adams" is treated as a String, not 2 identifiers.
            return f'"{lemma}"'

        # B. Extract Function Name (Duck Typing)
        # Works for Pydantic (UniversalNode/Ninai) and Dicts
        func_name = getattr(node, "function", None) or (node.get("function") if isinstance(node, dict) else None)
        
        if not func_name:
             raise ValueError(f"Invalid Node: Missing 'function' attribute. Got {type(node)}")

        # C. Extract Arguments
        args = getattr(node, "args", [])
        if isinstance(node, dict):
            args = node.get("args", [])

        # D. Recursively Process Arguments (Passing lang_code down)
        processed_args = [self._convert_to_gf_ast(arg, lang_code) for arg in args]
        
        # E. Format: func (arg1) (arg2)
        if not processed_args:
             return func_name
             
        # Wrapping args in parens () is crucial for GF parsing order
        args_str = " ".join([f"({arg})" for arg in processed_args])
        return f"{func_name} {args_str}"

    async def get_supported_languages(self) -> List[str]:
        if not self.grammar: return []
        return [name[-3:].lower() for name in self.grammar.languages.keys()]

    async def reload(self) -> None:
        self._load_grammar()

    async def health_check(self) -> bool:
        return self.grammar is not None
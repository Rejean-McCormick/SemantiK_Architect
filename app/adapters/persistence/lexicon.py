# app/adapters/persistence/lexicon.py
import json
import structlog
from pathlib import Path
from typing import List, Dict, Any, Optional

# [CRITICAL] Import the correct Port from __init__.py
from app.core.ports import LanguageRepo

logger = structlog.get_logger()

class FileSystemLexiconRepository(LanguageRepo):
    """
    Implementation of LanguageRepo that reads from the 'Everything Matrix'.
    This allows the API to list languages based on the daily system scan.
    """
    
    def __init__(self, base_path: str = "."):
        # Resolve path relative to project root
        self.root = Path(base_path).resolve()
        
        # Fallback logic for Docker vs Local paths
        if (self.root / "data").exists():
            self.matrix_path = self.root / "data" / "indices" / "everything_matrix.json"
        else:
            # Try jumping up one level if we are inside 'app'
            self.matrix_path = self.root.parent / "data" / "indices" / "everything_matrix.json"

    async def list_languages(self) -> List[Dict[str, Any]]:
        """
        Reads data/indices/everything_matrix.json and returns a list of languages.
        Matches the LanguageOut DTO expected by the API.
        """
        if not self.matrix_path.exists():
            logger.warning("matrix_not_found", path=str(self.matrix_path))
            # Fallback for fresh installs to prevent UI crash
            return [
                {"code": "eng", "name": "English (Fallback)", "z_id": "Z1002"},
                {"code": "fra", "name": "French (Fallback)", "z_id": "Z1004"}
            ]

        try:
            with open(self.matrix_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            languages = []
            # Parse the Matrix format defined in docs/02-BUILD_SYSTEM.md
            # Schema: { "languages": { "fr": { "meta": { "name": "French" } } } }
            for iso_code, details in data.get("languages", {}).items():
                meta = details.get("meta", {})
                
                languages.append({
                    # Prefer the explicit ISO code in meta, fallback to key
                    "code": meta.get("iso", iso_code),
                    "name": meta.get("name", iso_code.upper()),
                    "z_id": meta.get("z_id", None)
                })
            
            # Sort alphabetically for better UI UX
            return sorted(languages, key=lambda x: x["name"])

        except Exception as e:
            logger.error("list_languages_failed", error=str(e))
            return []

    # --- Required Stubs for Interface Compliance ---
    # These must exist because the abstract base class requires them.
    
    async def save_grammar(self, language_code: str, content: str) -> None:
        """Stub: Will implement when Admin UI is built."""
        pass

    async def get_grammar(self, language_code: str) -> Optional[str]:
        """Stub: Will implement when Admin UI is built."""
        return None
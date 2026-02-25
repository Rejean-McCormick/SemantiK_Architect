# app/adapters/persistence/languages.py
import json
import os
import structlog
from pathlib import Path
from typing import List, Dict, Any, Optional

# [CRITICAL] Import the correct Port from __init__.py
from app.core.ports import LanguageRepo

logger = structlog.get_logger()

class MatrixLanguageRepository(LanguageRepo):
    """
    Implementation of LanguageRepo that reads from the 'Everything Matrix'.
    
    This acts as the 'Inventory System', allowing the API to list available 
    languages based on the daily system scan.
    
    It also handles 'Onboarding' by scaffolding the necessary file structure
    on disk so the scanners can pick it up.
    """
    
    def __init__(self, base_path: str = "."):
        # Resolve path relative to project root
        self.root = Path(base_path).resolve()
        
        # Fallback logic for Docker vs Local paths
        # Detect if we are at root or inside app/
        if (self.root / "data").exists():
            self.matrix_path = self.root / "data" / "indices" / "everything_matrix.json"
        else:
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
                {"code": "en", "name": "English (Fallback)", "z_id": "Z1002"},
                {"code": "fr", "name": "French (Fallback)", "z_id": "Z1004"}
            ]

        try:
            with open(self.matrix_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            languages = []
            # Parse the Matrix format defined in docs/02-BUILD_SYSTEM.md
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

    async def save_grammar(self, language_code: str, content: str) -> None:
        """
        Implements the 'Scaffolding' phase of onboarding.
        
        Instead of saving a single grammar file, this method creates the 
        directory structure required for the 'Everything Matrix' scanners 
        to detect the new language (Zone B Lexicon).
        
        1. Creates data/lexicon/{code}/
        2. Writes a minimal core.json seed.
        """
        # Ensure lowercase ISO code
        code = language_code.lower().strip()
        
        # Define target directory: data/lexicon/{code}
        # We assume self.root points to the project root (where 'data' exists)
        if (self.root / "data").exists():
            base_dir = self.root
        else:
            base_dir = self.root.parent

        target_dir = base_dir / "data" / "lexicon" / code
        
        try:
            # 1. Create Directory
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
                logger.info("scaffold_directory_created", path=str(target_dir))
            
            # 2. Create seed 'core.json'
            # The LexiconScanner requires this file to grant a non-zero score.
            core_file = target_dir / "core.json"
            if not core_file.exists():
                seed_data = {
                    "meta": {
                        "language": code,
                        "created_at": "onboarding_saga",
                        "description": "Scaffolded by MatrixLanguageRepository"
                    },
                    "entries": {}
                }
                # Sync write is acceptable for administrative actions (rare events)
                with open(core_file, "w", encoding="utf-8") as f:
                    json.dump(seed_data, f, indent=2)
                
                logger.info("scaffold_seed_written", file=str(core_file))
                
        except Exception as e:
            logger.error("save_grammar_failed", code=code, error=str(e))
            raise e

    async def get_grammar(self, language_code: str) -> Optional[str]:
        """Stub: Will implement when Admin UI allows grammar editing."""
        return None
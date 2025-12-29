# app/adapters/persistence/filesystem_repo.py
import json
import os
import aiofiles
from pathlib import Path
from typing import Optional, List, Dict, Any
import structlog

# [FIX] Import from the centralized ports package (NO MORE 'lexicon_port.py')
from app.core.ports import LanguageRepo, LexiconRepo

from app.core.domain.models import LexiconEntry
from app.core.domain.exceptions import LexiconEntryNotFoundError
from app.shared.config import settings

logger = structlog.get_logger()

class FileSystemLexiconRepository(LanguageRepo, LexiconRepo):
    """
    Concrete implementation of the Repository using local JSON files.
    - Acts as LanguageRepo (reading 'everything_matrix.json')
    - Acts as LexiconRepo (reading 'lexicon/{lang}/lexicon.json')
    """

    def __init__(self, base_path: str):
        self.root = Path(base_path).resolve()
        
        # Path for Lexicon Data (Zone B)
        self.lexicon_base = self.root / "data" / "lexicon"
        self.lexicon_base.mkdir(parents=True, exist_ok=True)
        
        # Path for Matrix Index (Zone A)
        self.matrix_path = self.root / "data" / "indices" / "everything_matrix.json"

    # =========================================================
    # PART 1: LanguageRepo Implementation (Fixes API 500 Error)
    # =========================================================
    async def list_languages(self) -> List[Dict[str, Any]]:
        """
        Reads the dynamic registry to populate the Frontend Language Selector.
        """
        if not self.matrix_path.exists():
            logger.warning("matrix_not_found", path=str(self.matrix_path))
            return [
                {"code": "eng", "name": "English (Fallback)", "z_id": "Z1002"},
                {"code": "fra", "name": "French (Fallback)", "z_id": "Z1004"}
            ]

        try:
            async with aiofiles.open(self.matrix_path, mode='r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
            
            languages = []
            for iso_code, details in data.get("languages", {}).items():
                meta = details.get("meta", {})
                languages.append({
                    "code": meta.get("iso", iso_code),
                    "name": meta.get("name", iso_code.upper()),
                    "z_id": meta.get("z_id", None)
                })
            return sorted(languages, key=lambda x: x["name"])
        except Exception as e:
            logger.error("list_languages_failed", error=str(e))
            return []

    # =========================================================
    # PART 2: LexiconRepo Implementation (Your Logic)
    # =========================================================
    
    def _get_file_path(self, lang_code: str) -> Path:
        return self.lexicon_base / lang_code / "lexicon.json"

    async def _load_file(self, lang_code: str) -> Dict[str, Any]:
        path = self._get_file_path(lang_code)
        if not path.exists():
            return {}
        try:
            async with aiofiles.open(path, mode='r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content) if content else {}
        except Exception as e:
            logger.error("repo_read_failed", lang=lang_code, error=str(e))
            return {}

    async def _save_file(self, lang_code: str, data: Dict[str, Any]) -> None:
        path = self._get_file_path(lang_code)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            async with aiofiles.open(path, mode='w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.error("repo_write_failed", lang=lang_code, error=str(e))
            raise IOError(f"Could not save lexicon for {lang_code}")

    async def get_entry(self, iso_code: str, word: str) -> Optional[LexiconEntry]:
        data = await self._load_file(iso_code)
        raw_entry = data.get(word)
        if not raw_entry:
            return None
        return LexiconEntry(**raw_entry)

    async def save_entry(self, iso_code: str, entry: LexiconEntry) -> None:
        data = await self._load_file(iso_code)
        
        try:
            val = entry.model_dump()
        except AttributeError:
            val = entry.dict()

        key = entry.lemma if entry.lemma else entry.word
        data[key] = val
        
        await self._save_file(iso_code, data)
        logger.info("lexicon_entry_saved", lang=iso_code, lemma=key)

    async def get_entries_by_concept(self, lang_code: str, qid: str) -> List[LexiconEntry]:
        data = await self._load_file(lang_code)
        results = []
        for key, raw_entry in data.items():
            concepts = raw_entry.get("concepts", [])
            if qid in concepts:
                results.append(LexiconEntry(**raw_entry))
        return results

    # --- Compliance Stubs (Required by LanguageRepo ABC) ---
    async def save_grammar(self, language_code: str, content: str) -> None:
        pass

    async def get_grammar(self, language_code: str) -> Optional[str]:
        return None
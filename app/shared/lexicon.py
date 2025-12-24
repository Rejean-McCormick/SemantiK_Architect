# app/shared/lexicon.py
import json
import structlog
from pathlib import Path
from typing import Dict, Optional, Union
from dataclasses import dataclass

from app.shared.config import settings

logger = structlog.get_logger()

@dataclass
class LexiconEntry:
    lemma: str
    pos: str
    gf_fun: str
    qid: Optional[str] = None

class LexiconRuntime:
    """
    Singleton In-Memory Database for Zone B (Lexicon).
    Maps Abstract IDs (Q42, 02756049-n) -> Concrete Linearizations.
    """
    _instance = None
    _data: Dict[str, Dict[str, LexiconEntry]] = {} # {lang: {qid/lemma: Entry}}
    _loaded_langs = set()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LexiconRuntime, cls).__new__(cls)
        return cls._instance

    def load_language(self, lang_code: str):
        """
        Lazy-loads the 'wide.json' shard for a specific language.
        Prevents RAM explosion by only loading requested languages.
        """
        if lang_code in self._loaded_langs:
            return

        # Path: data/lexicon/{lang}/wide.json
        shard_path = Path(settings.FILESYSTEM_REPO_PATH) / "data" / "lexicon" / lang_code / "wide.json"
        
        if not shard_path.exists():
            logger.warning("lexicon_shard_missing", lang=lang_code, path=str(shard_path))
            return

        try:
            logger.info("lexicon_loading_shard", lang=lang_code)
            with open(shard_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)

            lang_index = {}
            
            for key, val in raw_data.items():
                # Handle list (v1) or dict (v2) format
                entry_data = val[0] if isinstance(val, list) else val

                entry_obj = LexiconEntry(
                    lemma=entry_data['lemma'],
                    pos=entry_data.get('pos', 'noun'),
                    gf_fun=entry_data['gf_fun'],
                    qid=entry_data.get('qid') or entry_data.get('wnid')
                )

                # Index by QID if available (Critical for Abstract Wiki)
                if entry_obj.qid:
                    lang_index[entry_obj.qid] = entry_obj
                
                # Index by Lemma (lowercase) for fallback
                lang_index[entry_obj.lemma.lower()] = entry_obj

            self._data[lang_code] = lang_index
            self._loaded_langs.add(lang_code)
            logger.info("lexicon_loaded_success", lang=lang_code, count=len(lang_index))

        except Exception as e:
            logger.error("lexicon_load_failed", lang=lang_code, error=str(e))

    def lookup(self, key: str, lang_code: str) -> Optional[LexiconEntry]:
        """
        Universal Lookup: Accepts QID (Q42) or Word (Apple).
        """
        self.load_language(lang_code)
        
        lang_db = self._data.get(lang_code)
        if not lang_db:
            return None

        # Try exact match
        return lang_db.get(key) or lang_db.get(key.lower())

# Global Instance
lexicon = LexiconRuntime()
# app/services/lexicon_store.py
import json
import os
from pathlib import Path

class LexiconStore:
    _instance = None
    _cache = {} # Structure: { 'eng': { 'Q42': {'lemma': 'Douglas', ...} } }

    @classmethod
    def get_lemma(cls, lang: str, qid: str) -> str:
        """
        Returns the lemma for a QID. 
        Priority:
        1. Manual Override (overrides.json)
        2. Harvested Lexicon (people.json)
        3. Fallback (The QID itself)
        """
        # Lazy Load Language
        if lang not in cls._cache:
            cls._load_language(lang)
            
        lang_data = cls._cache.get(lang, {})
        entry = lang_data.get(qid)
        
        if entry:
            return entry.get("lemma")
        return qid # Fallback to "Q42" if truly missing

    @classmethod
    def _load_language(cls, lang: str):
        print(f"⚡ Hydrating Lexicon for {lang}...")
        cls._cache[lang] = {}
        base_path = Path(f"data/lexicon/{lang}")
        
        # 1. Load all JSON shards in the folder
        if base_path.exists():
            for file in base_path.glob("*.json"):
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Merge into main dict
                    cls._cache[lang].update(data)
        
        # 2. Load Overrides (Last to ensure priority)
        override_path = base_path / "overrides.json"
        if override_path.exists():
             with open(override_path, 'r', encoding='utf-8') as f:
                cls._cache[lang].update(json.load(f))
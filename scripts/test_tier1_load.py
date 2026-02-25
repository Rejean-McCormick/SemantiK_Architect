# ========== FILE: test_tier1_load.py ==========
# Path: C:\MyCode\AbstractWiki\abstract-wiki-architect\scripts\test_tier1_load.py

import json
import pgf


def wiki_lang_from_iso(iso: str) -> str:
    """Resolve ISO code (e.g. 'fr') to a PGF language key (e.g. 'WikiFre') via iso_to_wiki.json."""
    with open("data/config/iso_to_wiki.json", "r", encoding="utf-8") as f:
        mapping = json.load(f)
    suffix = mapping[iso]["wiki"]
    return f"Wiki{suffix}"


try:
    print("🔄 Loading PGF...")
    grammar = pgf.readPGF("gf/AbstractWiki.pgf")
    print("✅ PGF Loaded Successfully!")

    langs = grammar.languages.keys()
    print(f"🌍 Detected Languages: {list(langs)}")

    en_key = wiki_lang_from_iso("en")
    fr_key = wiki_lang_from_iso("fr")

    if en_key in langs and fr_key in langs:
        print(f"🚀 SYSTEM READY: {en_key} and {fr_key} are linked.")
    else:
        missing = [k for k in [en_key, fr_key] if k not in langs]
        print(f"⚠️ CRITICAL: Languages missing from PGF: {missing}")

except Exception as e:
    print(f"❌ Error: {e}")
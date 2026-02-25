import json
import pgf

PGF_PATH = "gf/AbstractWiki.pgf"

def wiki_lang_from_iso(iso: str) -> str:
    with open("data/config/iso_to_wiki.json", "r", encoding="utf-8") as f:
        mapping = json.load(f)
    return f"Wiki{mapping[iso]['wiki']}"

g = pgf.readPGF(PGF_PATH)
langs = g.languages

expr = pgf.readExpr('mkBioNat (mkEntityStr "Marie Curie") (strNat "Polish")')

print(f"\n[Abstract]: {expr}")
print("-" * 30)

for iso in ["en", "fr", "de", "es", "it"]:
    key = wiki_lang_from_iso(iso)
    if key in langs:
        print(f"[{iso} {key}]: {langs[key].linearize(expr)}")
    else:
        print(f"[{iso} {key}]: MISSING_IN_PGF")
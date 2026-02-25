import json
import pgf

PGF_PATH = "gf/AbstractWiki.pgf"
ISO_MAP_PATH = "data/config/iso_to_wiki.json"

def wiki_lang_from_iso(iso: str) -> str:
    with open(ISO_MAP_PATH, "r", encoding="utf-8") as f:
        mapping = json.load(f)
    return f"Wiki{mapping[iso]['wiki']}"

g = pgf.readPGF(PGF_PATH)

eng_key = wiki_lang_from_iso("en")
fr_key = wiki_lang_from_iso("fr")

available = sorted(g.languages.keys())
if eng_key not in g.languages:
    raise KeyError(f"{eng_key} not in PGF. Available: {available}")
if fr_key not in g.languages:
    raise KeyError(f"{fr_key} not in PGF. Available: {available}")

eng = g.languages[eng_key]
fra = g.languages[fr_key]

expr_str = 'mkBioProf (mkEntityStr "Alan Turing") (strProf "computer scientist")'
expr = pgf.readExpr(expr_str)

# Sanity: ensure the expression is well-typed for this PGF
# inferExpr returns (normalized_expr, type) in this binding
try:
    inferred_expr, inferred_type = g.inferExpr(expr)
except Exception as e:
    raise RuntimeError(f"Expression not valid for this PGF: {expr_str}\nError: {e}")

print(f"[PGF]      : {PGF_PATH}")
print(f"[StartCat] : {g.startCat}")
print(f"[Expr]     : {expr_str}")
print(f"[Type]     : {inferred_type}")
print(f"[English]  : {eng.linearize(expr)}")
print(f"[French]   : {fra.linearize(expr)}")
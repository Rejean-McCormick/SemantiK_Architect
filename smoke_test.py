import pgf
import sys

# Load the compiled binary
pgf_path = "gf/AbstractWiki.pgf"
try:
    grammar = pgf.readPGF(pgf_path)
except FileNotFoundError:
    print(f"❌ Error: Could not find {pgf_path}. Did the build finish?")
    sys.exit(1)

# Grab the languages
try:
    eng = grammar.languages["WikiEng"]
    que = grammar.languages["WikiQue"]
except KeyError as e:
    print(f"❌ Error: Language {e} not found in PGF. The build failed to link it.")
    sys.exit(1)

# Construct the Semantic Tree: "Shaka walks"
# Abstract: mkFact (mkLiteral "Shaka") lex_walk_V
expr_str = 'mkFact (mkLiteral "Shaka") lex_walk_V'

try:
    expr = pgf.readExpr(expr_str)
    print(f"\n✨ ABSTRACT TREE: {expr_str}")
    print("-" * 30)
    print(f"🇬🇧 Eng (Tier 1): {eng.linearize(expr)}")
    print(f"🇧🇴 Que (Tier 3): {que.linearize(expr)}")
    print("-" * 30)
    print("✅ SMOKE TEST PASSED: The system is ready.")
except Exception as e:
    print(f"❌ Error parsing expression: {e}")

# tools/harvest_lexicon.py
# "The Universal Harvester" - v2.8 (Auto-Pilot + Layout-Aware Edition)
#
# Fixes:
#   - Smart gf-wordnet layout resolution:
#       * accepts --root as repo root (gf-wordnet/) OR gf dir (gf-wordnet/gf/) OR WordNet.gf path
#       * finds WordNet.gf and WordNet{Lang}.gf regardless of where you point it
#   - When WordNet{Lang}.gf is missing, prints available WordNet languages found (diagnostic)
#   - Robust concrete entry parsing:
#       * parses multiline RHS safely (ignores ; inside "strings" and inside --comments)
#       * captures optional trailing comment after ';'
#   - Optional marking of "--guessed" entries (default ON; use --no-mark-guessed to disable)
#   - Repo-relative default output path (CWD independent)
#
# Notes:
#   - Keeps WordNet harvesting stable: frame is harvested into data/lexicon/{iso2}/wide.json

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Tuple, List, Any, Iterator

import requests


# --- CONFIGURATION: SINGLE SOURCE OF TRUTH ---
BASE_DIR = Path(__file__).resolve().parent.parent

# Prefer repo-root config if present, otherwise data/config
ISO_MAP_CANDIDATES = [
    BASE_DIR / "config" / "iso_to_wiki.json",
    BASE_DIR / "data" / "config" / "iso_to_wiki.json",
]

# Optional matrix fallback (ISO-2 keys)
MATRIX_PATH = BASE_DIR / "data" / "indices" / "everything_matrix.json"

# Global Maps (Populated on Startup)
ISO2_TO_RGL: Dict[str, str] = {}  # 'en' -> 'Eng'
RGL_TO_ISO2: Dict[str, str] = {}  # 'Eng' -> 'en' (also 'WikiEng' -> 'en')

logger = logging.getLogger(__name__)

HARVESTER_VERSION = "harvester/2.8-layout-aware"

# --- HARVESTER LOGIC ---
# Abstract: fun apple_N : N ; -- 02756049-n  OR -- Q1234
# Capture the first token after "--" (e.g. Q1234 or 02756049-n)
RE_ABSTRACT = re.compile(r"\bfun\s+([^\s:]+).*?--\s*([^\s;]+)")

# String literals in RHS
RE_STRING = re.compile(r'"([^"]+)"')
RE_QID = re.compile(r"^Q[1-9]\d*$")
RE_WNID = re.compile(r"^\d{8}-[a-z]$")  # WordNet synset ID: 02756049-n

# GF identifiers can contain apostrophes; accept underscores/digits after start.
RE_GFID = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")

# Find starts of concrete definitions:
#   lin foo = ...
RE_LIN_START = re.compile(r"(?m)^\s*lin\s+(" + RE_GFID.pattern + r")\s*=\s*")

# guessed marker (support variations like "-- guessed" too)
RE_GUESSED = re.compile(r"--\s*guessed\b", re.IGNORECASE)


SPARQL_TEMPLATE = """
SELECT ?item ?itemLabel ?itemDescription ?job ?nat WHERE {
  VALUES ?item { %s }
  OPTIONAL { ?item wdt:P106 ?job . }
  OPTIONAL { ?item wdt:P27 ?nat . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "%s". }
}
"""


def _find_iso_map_path() -> Path:
    for p in ISO_MAP_CANDIDATES:
        if p.exists():
            return p
    return ISO_MAP_CANDIDATES[-1]


def load_iso_map() -> None:
    config_path = _find_iso_map_path()
    logger.debug(f"Loading ISO map from: {config_path}")

    if not config_path.exists():
        logger.error(f"❌ Critical: Config file missing (tried: {', '.join(map(str, ISO_MAP_CANDIDATES))})")
        sys.exit(1)

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"❌ Failed to parse language config: {e}")
        sys.exit(1)

    ISO2_TO_RGL.clear()
    RGL_TO_ISO2.clear()

    count = 0
    for iso_code_raw, value in (data or {}).items():
        if not isinstance(iso_code_raw, str):
            continue
        iso_code = iso_code_raw.strip().lower()
        if len(iso_code) != 2:
            continue

        rgl_full = value.get("wiki") if isinstance(value, dict) else value
        if not isinstance(rgl_full, str) or not rgl_full.strip():
            continue

        rgl_full = rgl_full.strip()
        rgl_suffix = rgl_full.replace("Wiki", "").replace("wiki", "").strip()
        if not rgl_suffix:
            continue

        # normalize (Eng not eng)
        rgl_suffix = rgl_suffix[:1].upper() + rgl_suffix[1:]

        ISO2_TO_RGL[iso_code] = rgl_suffix
        RGL_TO_ISO2[rgl_suffix] = iso_code
        RGL_TO_ISO2[rgl_full] = iso_code
        count += 1

    logger.debug(f"Loaded ISO map entries: {count}")


def resolve_and_validate_language(input_code: str) -> Optional[Tuple[str, str]]:
    clean = (input_code or "").strip()
    if not clean:
        return None

    clean_norm = clean.lower().replace(".gf", "").strip()
    clean_suffix = (
        clean.replace("Wiki", "")
        .replace("wiki", "")
        .replace(".gf", "")
        .strip()
    )

    clean_suffix_cap = clean_suffix[:1].upper() + clean_suffix[1:] if clean_suffix else clean_suffix

    # ISO-2
    if clean_norm in ISO2_TO_RGL:
        return ISO2_TO_RGL[clean_norm], clean_norm

    # RGL suffix (Eng/Fre/...)
    if clean_suffix in RGL_TO_ISO2:
        return clean_suffix, RGL_TO_ISO2[clean_suffix]
    if clean_suffix_cap in RGL_TO_ISO2:
        return clean_suffix_cap, RGL_TO_ISO2[clean_suffix_cap]

    return None


def _normalize_qids(raw: Any) -> List[str]:
    if isinstance(raw, dict):
        candidates = list(raw.keys())
    elif isinstance(raw, list):
        candidates = raw
    else:
        raise ValueError("Input JSON must be a list of QIDs or an object keyed by QIDs.")

    seen = set()
    out: List[str] = []
    for x in candidates:
        if isinstance(x, str) and x.strip() and RE_QID.match(x.strip()):
            q = x.strip()
            if q not in seen:
                seen.add(q)
                out.append(q)
    return out


# --- AUTO DISCOVERY ---
def auto_detect_gf_root() -> Optional[Path]:
    """
    Returns a path that the user would logically call the 'root':
      - Prefer gf-wordnet repo root if found
      - Otherwise return the gf dir containing WordNet.gf
    """
    candidates = [
        BASE_DIR.parent / "gf-wordnet",
        BASE_DIR / "gf-wordnet",
        BASE_DIR / "lib" / "gf-wordnet",
        BASE_DIR / "gf",
        Path("/mnt/c/MyCode/AbstractWiki/gf-wordnet"),
        Path("/mnt/c/MyCode/AbstractWiki/gf-wordnet/gf"),
    ]

    for c in candidates:
        if (c / "gf" / "WordNet.gf").exists():
            return c  # repo root
        if (c / "WordNet.gf").exists():
            return c  # gf dir (or repo root with WordNet.gf at top)

    # Deep search if standard paths fail
    try:
        found = list(BASE_DIR.rglob("WordNet.gf"))
        if found:
            # return repo root if it looks like .../gf/WordNet.gf
            gf_dir = found[0].parent
            if gf_dir.name == "gf":
                return gf_dir.parent
            return gf_dir
    except Exception:
        pass

    return None


def _resolve_wordnet_layout(root_path: Path) -> Tuple[Path, Path, Path]:
    """
    Accepts:
      - repo root: gf-wordnet/
      - gf dir: gf-wordnet/gf/
      - file path: .../WordNet.gf

    Returns:
      (repo_root, gf_dir, wordnet_abstract_path)
    """
    root_path = root_path.expanduser().resolve()

    # If user passed WordNet.gf directly
    if root_path.is_file() and root_path.name == "WordNet.gf":
        gf_dir = root_path.parent
        repo_root = gf_dir.parent if gf_dir.name == "gf" else gf_dir
        return repo_root, gf_dir, root_path

    # If user passed a directory that contains WordNet.gf
    if root_path.is_dir() and (root_path / "WordNet.gf").exists():
        gf_dir = root_path
        repo_root = gf_dir.parent if gf_dir.name == "gf" else gf_dir
        return repo_root, gf_dir, gf_dir / "WordNet.gf"

    # If user passed repo root containing gf/WordNet.gf
    if root_path.is_dir() and (root_path / "gf" / "WordNet.gf").exists():
        repo_root = root_path
        gf_dir = repo_root / "gf"
        return repo_root, gf_dir, gf_dir / "WordNet.gf"

    # Deep search under provided root
    if root_path.is_dir():
        try:
            hits = list(root_path.rglob("WordNet.gf"))
            if hits:
                wordnet = hits[0].resolve()
                gf_dir = wordnet.parent
                repo_root = gf_dir.parent if gf_dir.name == "gf" else root_path
                return repo_root, gf_dir, wordnet
        except Exception:
            pass

    raise FileNotFoundError(f"WordNet.gf not found under root={root_path}")


def _list_available_wordnet_lang_suffixes(gf_dir: Path, limit: int = 60) -> List[str]:
    """
    Returns list of suffixes for WordNet{Suffix}.gf found under gf_dir.
    Excludes WordNet.gf itself.
    """
    out: List[str] = []
    try:
        for p in gf_dir.rglob("WordNet*.gf"):
            if p.name == "WordNet.gf":
                continue
            stem = p.stem  # WordNetEng
            if not stem.startswith("WordNet"):
                continue
            suf = stem.replace("WordNet", "")
            if suf and suf not in out:
                out.append(suf)
    except Exception:
        pass
    out.sort()
    return out[:limit]


def _find_wordnet_lang_file(repo_root: Path, gf_dir: Path, rgl_code: str) -> Optional[Path]:
    """
    Find concrete lexicon file for a language, robust to minor layout differences.
    Primary expectation: gf/WordNet{Lang}.gf
    """
    candidates = [
        f"WordNet{rgl_code}.gf",
        f"WordNet{rgl_code[:1].upper() + rgl_code[1:]}.gf",
        f"WordNet{rgl_code.lower().capitalize()}.gf",
    ]

    search_roots = [
        gf_dir,
        repo_root / "gf",
        repo_root,
        repo_root / "src",
        repo_root / "grammars",
        repo_root / "grammars" / "gf",
        repo_root / "grammars" / "wordnet",
    ]

    # First: direct existence checks in likely folders
    for sr in search_roots:
        if not sr.exists():
            continue
        for name in candidates:
            p = sr / name
            if p.exists():
                return p.resolve()

    # Second: rglob in likely roots (cheap first)
    for sr in search_roots:
        if not sr.exists():
            continue
        for name in candidates:
            try:
                hits = list(sr.rglob(name))
                if hits:
                    return hits[0].resolve()
            except Exception:
                continue

    # Third: module-name sniffing as a last resort
    # If filenames differ, scan WordNet*.gf and look for "concrete WordNet{Lang} of WordNet"
    expected_mod = f"WordNet{rgl_code}"
    try:
        for p in gf_dir.rglob("WordNet*.gf"):
            if p.name == "WordNet.gf":
                continue
            # cheap read head
            head = p.read_text(encoding="utf-8", errors="ignore")[:8000]
            if f"concrete {expected_mod} " in head and " of WordNet" in head:
                return p.resolve()
    except Exception:
        pass

    return None


def _iter_concrete_lin_defs(content: str) -> Iterator[Tuple[str, str, str]]:
    """
    Yields (gf_fun, rhs, trailing_comment) for each:
        lin <Fun> = <RHS> ; [-- comment]

    Parsing rules:
      - Finds 'lin ... = ' at start-of-line (ignores indentation)
      - Scans forward to the first ';' that is NOT inside:
          * a double-quoted string
          * a '--' line comment
      - Captures trailing comment only if it begins with '--' after the ';' on the same line.
    """
    for m in RE_LIN_START.finditer(content):
        func = m.group(1)
        i = m.end()

        in_str = False
        esc = False
        in_comment = False

        rhs_start = i
        rhs_end = None
        trailing = ""

        while i < len(content):
            ch = content[i]

            # comment mode
            if in_comment:
                if ch == "\n":
                    in_comment = False
                i += 1
                continue

            # string mode
            if in_str:
                if esc:
                    esc = False
                else:
                    if ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                i += 1
                continue

            # normal mode
            if ch == '"':
                in_str = True
                i += 1
                continue

            # '--' comment start (only outside strings)
            if ch == "-" and i + 1 < len(content) and content[i + 1] == "-":
                in_comment = True
                i += 2
                continue

            # statement terminator
            if ch == ";":
                rhs_end = i
                i += 1

                # capture trailing comment on the same line (after ';')
                j = i
                while j < len(content) and content[j] in " \t":
                    j += 1
                if j + 1 < len(content) and content[j] == "-" and content[j + 1] == "-":
                    k = j
                    while k < len(content) and content[k] != "\n":
                        k += 1
                    trailing = content[j:k].strip()
                    i = k
                break

            i += 1

        if rhs_end is None:
            # Malformed or unusual file; skip safely.
            continue

        rhs = content[rhs_start:rhs_end].strip()
        yield func, rhs, trailing


class GFWordNetHarvester:
    def __init__(self, root_path: str):
        self.user_root = Path(root_path)
        self.repo_root: Path
        self.gf_dir: Path
        self.wordnet_abstract: Path
        self.semantic_map: Dict[str, str] = {}

        try:
            self.repo_root, self.gf_dir, self.wordnet_abstract = _resolve_wordnet_layout(self.user_root)
        except Exception as e:
            logger.error(f"❌ Critical: cannot resolve gf-wordnet layout from --root {root_path}: {e}")
            sys.exit(1)

        logger.debug(f"Resolved gf-wordnet layout:")
        logger.debug(f"  repo_root = {self.repo_root}")
        logger.debug(f"  gf_dir    = {self.gf_dir}")
        logger.debug(f"  WordNet   = {self.wordnet_abstract}")

    def load_semantics(self) -> None:
        path = self.wordnet_abstract
        logger.info(f"📖 Indexing semantics from {path}...")
        try:
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                match = RE_ABSTRACT.search(line)
                if match:
                    func, sem_id = match.groups()
                    self.semantic_map[func.strip()] = sem_id.strip()
        except Exception as e:
            logger.error(f"❌ Failed to read WordNet.gf: {e}")
            sys.exit(1)

    def harvest_lang(
        self,
        rgl_code: str,
        iso2_code: str,
        out_dir: str,
        lemma_mode: str = "first",
        mark_guessed: bool = True,
    ) -> int:
        src_file = _find_wordnet_lang_file(self.repo_root, self.gf_dir, rgl_code)

        if not src_file:
            avail = _list_available_wordnet_lang_suffixes(self.gf_dir)
            logger.warning(f"⚠️  Skipping {rgl_code}: Could not find WordNet{rgl_code}.gf under:")
            logger.warning(f"    gf_dir={self.gf_dir}")
            logger.warning(f"    repo_root={self.repo_root}")
            if avail:
                logger.warning(f"    Found WordNet languages: {', '.join(avail)}")
                if "Eng" not in avail:
                    logger.warning("    NOTE: 'Eng' is not present in the repo scan; verify gf-wordnet contains WordNetEng.gf.")
            else:
                logger.warning("    Found no WordNet{Lang}.gf files at all (repo may be incomplete / wrong root).")
            return 0

        logger.info(f"🚜 Harvesting {rgl_code} from {src_file}...")
        lexicon: Dict[str, Any] = {}
        count = 0

        try:
            content = src_file.read_text(encoding="utf-8", errors="ignore")

            for func, rhs, trailing in _iter_concrete_lin_defs(content):
                if "variants {}" in rhs:
                    continue

                strings = RE_STRING.findall(rhs)
                if not strings:
                    continue

                # Lemma heuristic
                if lemma_mode == "join" and len(strings) > 1:
                    lemma = " ".join(strings).strip()
                else:
                    lemma = strings[0].strip()

                if not lemma:
                    continue

                sem_id = self.semantic_map.get(func, "")
                entry: Dict[str, Any] = {"lemma": lemma, "gf_fun": func, "source": "gf-wordnet"}

                # guessed marker (optional)
                if mark_guessed and (RE_GUESSED.search(trailing) or RE_GUESSED.search(rhs)):
                    entry["status"] = "guessed"

                # semantic id routing
                if sem_id.startswith("Q") and RE_QID.match(sem_id):
                    entry["qid"] = sem_id
                elif sem_id and RE_WNID.match(sem_id):
                    entry["wnid"] = sem_id
                elif sem_id:
                    entry["sem"] = sem_id  # unknown format, keep for debugging

                # Optional: preserve multi-string evidence
                if len(strings) > 1:
                    entry["strings"] = strings

                # Key by lemma lowercase (existing behavior)
                k = lemma.lower()
                if k not in lexicon:
                    lexicon[k] = entry
                    count += 1
                else:
                    # Keep first entry stable; attach collision info to avoid silent loss
                    prev = lexicon[k]
                    if isinstance(prev, dict):
                        prev.setdefault("collisions", 0)
                        prev["collisions"] += 1

            out_root = Path(out_dir)
            if not out_root.is_absolute():
                # make output repo-relative, not CWD-relative
                out_root = (BASE_DIR / out_root).resolve()

            out_path = out_root / iso2_code / "wide.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(lexicon, indent=2, ensure_ascii=False), encoding="utf-8")

            logger.info(f"✅ Saved {count} words to {out_path}")
            return count

        except Exception as e:
            logger.error(f"❌ Error processing {src_file}: {e}")
            return 0


class WikidataHarvester:
    def _http_get_with_retry(self, url, params, headers, max_retries=3):
        backoff = 1
        for attempt in range(1, max_retries + 1):
            try:
                r = requests.get(url, params=params, headers=headers, timeout=30)
                r.raise_for_status()
                return r.json()
            except Exception as e:
                logger.warning(f"  ⚠️ Attempt {attempt} failed: {e}")
                time.sleep(backoff)
                backoff *= 2
        return None

    def fetch(self, qids, iso2_code, domain="people"):
        # Placeholder (kept for compatibility)
        return {}


def main() -> None:
    # --- AUTO-PILOT INJECTION ---
    if len(sys.argv) == 1:
        print("🤖 Auto-Pilot: No arguments detected. Configuring defaults...")

        detected_root = auto_detect_gf_root()
        if not detected_root:
            print("❌ Auto-Pilot Failed: Could not find 'WordNet.gf' in any standard location.")
            print("   Please run manually with: python3 tools/harvest_lexicon.py wordnet --root /path/to/gf-wordnet --lang en")
            sys.exit(1)

        print(f"📍 Auto-detected Root: {detected_root}")
        sys.argv.extend(["wordnet", "--root", str(detected_root), "--lang", "en"])

    # --- STANDARD ARGUMENT PARSING ---
    parser = argparse.ArgumentParser(description="Universal Lexicon Harvester")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="source", required=True)

    # WordNet Subparser
    wn_parser = subparsers.add_parser("wordnet", help="Mine local GF WordNet files")
    wn_parser.add_argument("--root", required=True, help="Path to gf-wordnet repo OR its gf/ subdir OR WordNet.gf path")
    wn_parser.add_argument("--lang", required=True, help="Target Language (e.g. en, fr, Eng, WikiEng)")
    wn_parser.add_argument(
        "--out",
        default=str(Path("data") / "lexicon"),
        help="Output root (repo-relative if not absolute)",
    )
    wn_parser.add_argument(
        "--lemma-mode",
        choices=["first", "join"],
        default="first",
        help='If multiple string literals exist, use "first" or join them with spaces.',
    )
    wn_parser.add_argument(
        "--no-mark-guessed",
        dest="mark_guessed",
        action="store_false",
        help="Do not set entry['status']='guessed' when '--guessed' is detected.",
    )
    wn_parser.set_defaults(mark_guessed=True)

    # Wikidata Subparser
    wd_parser = subparsers.add_parser("wikidata", help="Fetch from Wikidata")
    wd_parser.add_argument("--lang", required=True, help="Target Language")
    wd_parser.add_argument("--input", required=True, help="JSON file containing QIDs")
    wd_parser.add_argument("--domain", default="people", help="Shard name")
    wd_parser.add_argument("--out", default=str(Path("data") / "lexicon"), help="Output root")

    args = parser.parse_args()

    # --- LOGGING ---
    log_level = logging.DEBUG if getattr(args, "verbose", False) else logging.INFO
    logging.basicConfig(level=log_level, format="%(message)s", stream=sys.stdout, force=True)

    print(f"=== LEXICON HARVESTER ({HARVESTER_VERSION}) ===")
    load_iso_map()

    resolved = resolve_and_validate_language(args.lang)
    if not resolved:
        logger.error(f"❌ Unknown/unsupported language code: {args.lang}")
        sys.exit(1)

    rgl_code, iso2_code = resolved

    if args.source == "wordnet":
        harvester = GFWordNetHarvester(args.root)
        harvester.load_semantics()
        harvester.harvest_lang(
            rgl_code,
            iso2_code,
            args.out,
            lemma_mode=args.lemma_mode,
            mark_guessed=getattr(args, "mark_guessed", True),
        )

    elif args.source == "wikidata":
        # Placeholder path
        pass


if __name__ == "__main__":
    main()

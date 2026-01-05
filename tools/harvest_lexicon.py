# tools/harvest_lexicon.py
import argparse
import json
import re
import requests
import sys
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Tuple, List, Any

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
RGL_TO_ISO2: Dict[str, str] = {}  # 'Eng' -> 'en'

logger = logging.getLogger(__name__)

HARVESTER_VERSION = "harvester/2.2"

# --- HARVESTER LOGIC ---
RE_ABSTRACT = re.compile(r"fun\s+([^\s:]+).*?--\s*([Q\d]+-?[a-z0-9]*)")
RE_CONCRETE = re.compile(r"lin\s+(\w+)\s*=\s*(.*?)\s*;")
RE_STRING = re.compile(r'"([^"]+)"')
RE_QID = re.compile(r"^Q[1-9]\d*$")

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
    """
    Loads iso_to_wiki.json to build ISO2 <-> RGL suffix mappings.
    """
    config_path = _find_iso_map_path()
    logger.info(f"Loading ISO map from: {config_path}")

    if not config_path.exists():
        logger.error(f"❌ Critical: Config file missing (tried: {', '.join(map(str, ISO_MAP_CANDIDATES))})")
        sys.exit(1)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for iso_code, value in data.items():
            if len(iso_code) != 2:
                continue

            rgl_full = value.get("wiki") if isinstance(value, dict) else value
            if not isinstance(rgl_full, str) or not rgl_full:
                continue

            rgl_suffix = rgl_full.replace("Wiki", "")
            ISO2_TO_RGL[iso_code] = rgl_suffix
            RGL_TO_ISO2[rgl_suffix] = iso_code
            RGL_TO_ISO2[rgl_full] = iso_code
            count += 1

        logger.info(f"✅ Loaded {count} ISO-2 entries")
    except Exception as e:
        logger.error(f"❌ Failed to parse language config: {e}")
        sys.exit(1)


def resolve_and_validate_language(input_code: str) -> Optional[Tuple[str, str]]:
    """
    Resolves any input (en, eng, WikiEng) to canonical (RGL_Suffix, ISO2).
    Returns: (rgl_code, iso2_code) e.g. ('Eng', 'en')
    """
    clean = (input_code or "").strip()
    if not clean:
        logger.error("❌ Empty language code.")
        return None

    clean_norm = clean.lower()
    clean_suffix = clean.replace("Wiki", "").replace("wiki", "")
    clean_suffix_cap = clean_suffix[:1].upper() + clean_suffix[1:] if clean_suffix else clean_suffix

    if clean_norm in ISO2_TO_RGL:
        return ISO2_TO_RGL[clean_norm], clean_norm

    if clean_suffix in RGL_TO_ISO2:
        return clean_suffix, RGL_TO_ISO2[clean_suffix]
    if clean_suffix_cap in RGL_TO_ISO2:
        return clean_suffix_cap, RGL_TO_ISO2[clean_suffix_cap]

    if MATRIX_PATH.exists():
        try:
            with open(MATRIX_PATH, "r", encoding="utf-8") as f:
                matrix = json.load(f)
            langs = matrix.get("languages", {})
            if clean_norm in langs:
                return clean_norm.capitalize(), clean_norm
        except Exception:
            pass

    logger.error(f"❌ Language '{input_code}' is not recognized in system configuration.")
    return None


def _normalize_qids(raw: Any) -> List[str]:
    """
    Accepts either:
      - list[str] of QIDs
      - dict (keys are QIDs)
    Returns a deduped list preserving first-seen order.
    """
    if isinstance(raw, dict):
        candidates = list(raw.keys())
    elif isinstance(raw, list):
        candidates = raw
    else:
        raise ValueError("Input JSON must be a list of QIDs or an object keyed by QIDs.")

    seen = set()
    out: List[str] = []
    for x in candidates:
        if not isinstance(x, str):
            continue
        q = x.strip()
        if not q:
            continue
        if not RE_QID.match(q):
            continue
        if q in seen:
            continue
        seen.add(q)
        out.append(q)

    return out


class GFWordNetHarvester:
    def __init__(self, root_path: str):
        self.root = Path(root_path)
        self.semantic_map: Dict[str, str] = {}

    def load_semantics(self) -> None:
        path = self.root / "WordNet.gf"
        if not path.exists():
            logger.error(f"❌ Critical: WordNet.gf not found at {path}")
            sys.exit(1)

        logger.info(f"📖 Indexing semantics from {path}...")
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                match = RE_ABSTRACT.search(line)
                if match:
                    func, sem_id = match.groups()
                    self.semantic_map[func.strip()] = sem_id.strip()
                    count += 1
        logger.info(f"    Indexed {count} semantic keys.")

    def harvest_lang(self, rgl_code: str, iso2_code: str, out_dir: str) -> int:
        """
        Harvests from the RGL WordNet file (using rgl_code, e.g. 'Eng')
        but saves to storage folder (using iso2_code, e.g. 'en').
        """
        candidates = [
            f"WordNet{rgl_code}.gf",
            f"WordNet{rgl_code.capitalize()}.gf",
        ]

        src_file: Optional[Path] = None
        for c in candidates:
            found = list(self.root.rglob(c))
            if found:
                src_file = found[0]
                break

        if not src_file:
            logger.warning(f"⚠️  Skipping {rgl_code}: Could not find WordNet file in {self.root}")
            return 0

        logger.info(f"🚜 Harvesting {rgl_code} from {src_file.name}...")
        lexicon: Dict[str, Any] = {}
        count = 0

        with open(src_file, "r", encoding="utf-8") as f:
            content = f.read()

        for match in RE_CONCRETE.finditer(content):
            func, rhs = match.groups()
            if "variants {}" in rhs:
                continue

            strings = RE_STRING.findall(rhs)
            if strings:
                lemma = strings[0]
                sem_id = self.semantic_map.get(func, "")

                entry: Dict[str, Any] = {"lemma": lemma, "gf_fun": func, "source": "gf-wordnet"}
                if sem_id.startswith("Q"):
                    entry["qid"] = sem_id
                elif sem_id:
                    entry["wnid"] = sem_id

                lexicon[lemma.lower()] = entry
                count += 1

        out_path = Path(out_dir) / iso2_code / "wide.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(lexicon, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Saved {count} words to {out_path}")
        return count


class WikidataHarvester:
    def _http_get_with_retry(
        self,
        url: str,
        params: Dict[str, Any],
        headers: Dict[str, str],
        max_retries: int = 3,
    ) -> Optional[Dict[str, Any]]:
        backoff = 1
        for attempt in range(1, max_retries + 1):
            try:
                r = requests.get(url, params=params, headers=headers, timeout=30)
                r.raise_for_status()
                return r.json()
            except Exception as e:
                logger.warning(f"  ⚠️ Attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error(f"  ❌ Failed after {max_retries} attempts.")
                    return None
        return None

    def fetch(self, qids: List[str], iso2_code: str, domain: str = "people") -> Dict[str, Any]:
        logger.info(f"☁️  Fetching {len(qids)} items from Wikidata for '{iso2_code}'...")

        chunk_size = 50
        all_results: Dict[str, Any] = {}
        total_chunks = (len(qids) + chunk_size - 1) // chunk_size

        for i in range(0, len(qids), chunk_size):
            chunk = qids[i : i + chunk_size]
            chunk_idx = (i // chunk_size) + 1
            logger.info(f"  Processing chunk {chunk_idx}/{total_chunks} ({len(chunk)} items)...")

            values = " ".join([f"wd:{qid}" for qid in chunk])
            lang_string = f"{iso2_code},en"
            query = SPARQL_TEMPLATE % (values, lang_string)

            data = self._http_get_with_retry(
                "https://query.wikidata.org/sparql",
                params={"format": "json", "query": query},
                headers={"User-Agent": f"AbstractWikiArchitect/{HARVESTER_VERSION}"},
            )
            if not data:
                continue

            bindings = data.get("results", {}).get("bindings", [])
            for row in bindings:
                try:
                    qid = row["item"]["value"].split("/")[-1]
                    if qid not in all_results:
                        lemma = row.get("itemLabel", {}).get("value") or ""
                        desc = row.get("itemDescription", {}).get("value", "") or ""
                        all_results[qid] = {
                            "qid": qid,
                            "lemma": lemma,
                            "desc": desc,
                            "source": "wikidata-harvester",
                            "domain": domain,
                            "facts": {"P106": [], "P27": []},
                        }

                    if "job" in row and "value" in row["job"]:
                        job_qid = row["job"]["value"].split("/")[-1]
                        if RE_QID.match(job_qid) and job_qid not in all_results[qid]["facts"]["P106"]:
                            all_results[qid]["facts"]["P106"].append(job_qid)

                    if "nat" in row and "value" in row["nat"]:
                        nat_qid = row["nat"]["value"].split("/")[-1]
                        if RE_QID.match(nat_qid) and nat_qid not in all_results[qid]["facts"]["P27"]:
                            all_results[qid]["facts"]["P27"].append(nat_qid)

                except Exception:
                    continue

        return all_results


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout, force=True)
    start_time = time.time()

    print(f"=== LEXICON HARVESTER ({HARVESTER_VERSION}) ===")
    print(f"Timestamp: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    print("-" * 40)

    load_iso_map()

    parser = argparse.ArgumentParser(description="Universal Lexicon Harvester")
    subparsers = parser.add_subparsers(dest="source", required=True)

    wn_parser = subparsers.add_parser("wordnet", help="Mine local GF WordNet files")
    wn_parser.add_argument("--root", required=True, help="Path to gf-wordnet folder")
    wn_parser.add_argument("--lang", required=True, help="Target Language (e.g. en, fr)")
    wn_parser.add_argument("--out", default=str(Path("data") / "lexicon"), help="Output root (default: data/lexicon)")

    wd_parser = subparsers.add_parser("wikidata", help="Fetch from Wikidata for explicit QIDs")
    wd_parser.add_argument("--lang", required=True, help="Target Language (e.g. en, fr)")
    wd_parser.add_argument("--input", required=True, help="JSON file containing QIDs (list or object keyed by QIDs)")
    wd_parser.add_argument("--domain", default="people", help="Shard/domain name (default: people)")
    wd_parser.add_argument("--out", default=str(Path("data") / "lexicon"), help="Output root (default: data/lexicon)")

    args = parser.parse_args()

    resolved = resolve_and_validate_language(args.lang)
    if not resolved:
        sys.exit(1)

    rgl_code, iso2_code = resolved
    logger.info(f"🔧 Target: RGL='{rgl_code}' | ISO='{iso2_code}'")

    entries_count = 0
    output_file = ""

    if args.source == "wordnet":
        harvester = GFWordNetHarvester(args.root)
        harvester.load_semantics()
        entries_count = harvester.harvest_lang(rgl_code, iso2_code, args.out)
        output_file = str(Path(args.out) / iso2_code / "wide.json")

    elif args.source == "wikidata":
        input_path = Path(args.input)
        if not input_path.exists():
            logger.error(f"❌ Input file not found: {args.input}")
            sys.exit(1)

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                raw_input = json.load(f)
            target_qids = _normalize_qids(raw_input)
        except Exception as e:
            logger.error(f"❌ Failed to read/parse input JSON: {e}")
            sys.exit(1)

        if not target_qids:
            logger.error("❌ No valid QIDs found in input.")
            sys.exit(1)

        harvester = WikidataHarvester()
        data = harvester.fetch(target_qids, iso2_code, args.domain)
        entries_count = len(data)

        out_path = Path(args.out) / iso2_code / f"{args.domain}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        output_file = str(out_path)
        logger.info(f"✅ Saved {entries_count} entries to {out_path}")

    duration = time.time() - start_time

    print("\n=== SUMMARY ===")
    print(f"Language: {iso2_code}")
    print(f"Source:   {args.source}")
    print(f"Entries:  {entries_count}")
    print(f"Output:   {output_file}")
    print(f"Duration: {duration:.2f}s")


if __name__ == "__main__":
    main()

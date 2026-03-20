# tools/qa/eval_bios.py
"""
Evaluate biography generation against the live SemantiK Architect API.

This version is aligned with the final EN/FR cutover and the current public
generation contract.

Primary target
--------------

- POST /api/v1/generate/{lang_code}

Canonical success envelope
--------------------------

A successful response is centered on:

- text
- lang_code
- construction_id
- renderer_backend
- fallback_used
- tokens
- debug_info
- generation_time_ms

Final EN/FR evaluator rules
---------------------------

For EN/FR bio/person evaluation, this tool validates:

- public response contract shape,
- returned lang_code,
- explicit construction_id / renderer_backend / fallback_used,
- runtime_path,
- top-level vs debug_info parity,
- surface-language plausibility,
- resolved language when available,
- and final acceptance semantics.

For the final EN/FR slice, the evaluator treats the following as failures:

- invalid public envelope,
- runtime_path != "planner_first",
- fallback_used != False,
- missing or contradictory canonical metadata,
- FR resolved to WikiFre but surfacing obvious English,
- EN resolved to WikiEng but surfacing obvious French,
- contract-valid but language-invalid output.

The evaluator is intentionally lightweight and offline-friendly:

- It can:
    * read a preprocessed local JSON / JSONL / CSV file of people, OR
    * optionally query Wikidata SPARQL directly if `requests` is installed.

- For each person, it:
    * builds a bio-compatible payload,
    * calls the local SemantiK API,
    * validates the public response contract,
    * validates planner-first acceptance expectations,
    * records runtime metadata,
    * flags obvious language-surface mismatches,
    * optionally compares against gold bios if present in the input.

Input schema (LOCAL MODE, recommended)
--------------------------------------

Each record should contain at least:

    {
        "id": "Q7186",
        "label": "Marie Curie",
        "gender": "female",
        "profession_lemmas": ["physicist"],
        "nationality_lemmas": ["polish"],

        "gold_bios": {
            "en": "Marie Curie was a Polish-French physicist and chemist.",
            "fr": "Marie Curie était une physicienne et chimiste polonaise-française."
        }
    }

You can store these as:

- JSON array
- JSONL / NDJSON
- CSV with columns:
    * id, label, gender,
    * profession_lemmas (comma-separated),
    * nationality_lemmas (comma-separated),
    * gold_bios (optional JSON string)

Usage
-----

From project root:

    python tools/qa/eval_bios.py \
        --source local \
        --input data/samples/wikidata_people_sample.jsonl \
        --langs en fr \
        --limit 100 \
        --print-samples 5

or:

    python tools/qa/eval_bios.py \
        --source wikidata \
        --langs en fr \
        --limit 50

You can also point to a non-default API:

    python tools/qa/eval_bios.py \
        --api-base http://localhost:8000/api/v1 \
        --source local \
        --input data/samples/wikidata_people_sample.jsonl \
        --langs en fr

Exit code
---------

- 0: no contract / runtime-path / language failures detected
- 1: one or more contract / runtime-path / language failures detected
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib import error as urlerror
from urllib import request as urlrequest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NOMINAL_RUNTIME_PATH = "planner_first"
EXPECTED_PUBLIC_FIELDS = (
    "text",
    "lang_code",
    "construction_id",
    "renderer_backend",
    "fallback_used",
    "tokens",
    "debug_info",
    "generation_time_ms",
)
REQUIRED_DEBUG_FIELDS = (
    "runtime_path",
    "construction_id",
    "renderer_backend",
    "lang_code",
    "fallback_used",
    "slot_keys",
)
EXPECTED_RESOLVED_LANGUAGE_BY_LANG = {
    "en": "WikiEng",
    "fr": "WikiFre",
}

# ---------------------------------------------------------------------------
# Project bootstrap (run reliably from anywhere)
# ---------------------------------------------------------------------------


def _find_project_root(start: Path) -> Optional[Path]:
    for p in [start, *start.parents]:
        if (p / "manage.py").exists() and (p / "app").exists():
            return p
        if (p / "pyproject.toml").exists() and (p / "app").exists():
            return p
    return None


THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _find_project_root(THIS_DIR) or _find_project_root(Path.cwd())

if PROJECT_ROOT and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if PROJECT_ROOT:
    try:
        os.chdir(str(PROJECT_ROOT))
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Optional project logger
# ---------------------------------------------------------------------------

try:
    from utils.tool_logger import ToolLogger  # type: ignore

    log = ToolLogger("eval_bios")
except Exception:
    class _FallbackLog:
        def info(self, msg: str) -> None:
            print(msg)

        def warning(self, msg: str) -> None:
            print(f"[WARN] {msg}")

        def error(self, msg: str, fatal: bool = False) -> None:
            print(f"[ERROR] {msg}")
            if fatal:
                raise SystemExit(1)

        def stage(self, title: str, msg: str) -> None:
            print(f"\n[{title}] {msg}")

        def header(self, data: Dict[str, Any]) -> None:
            print("=== eval_bios ===")
            for k, v in data.items():
                print(f"{k}: {v}")

        def summary(self, data: Dict[str, Any]) -> None:
            print("\n=== summary ===")
            for k, v in data.items():
                print(f"{k}: {v}")

    log = _FallbackLog()

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class PersonRecord:
    id: str
    label: str
    gender: str = "unknown"
    profession_lemmas: List[str] = field(default_factory=list)
    nationality_lemmas: List[str] = field(default_factory=list)
    gold_bios: Dict[str, str] = field(default_factory=dict)


@dataclass
class EvalResult:
    person_id: str
    lang: str
    rendered: bool
    output: str
    has_gold: bool
    exact_match: bool

    contract_ok: bool
    contract_errors: List[str] = field(default_factory=list)

    acceptance_ok: bool = False
    acceptance_errors: List[str] = field(default_factory=list)

    response_lang_code: str = ""
    construction_id: str = ""
    renderer_backend: str = ""
    runtime_path: str = ""
    resolved_language: str = ""
    fallback_used: bool = False
    generation_time_ms: float = 0.0

    language_surface_ok: bool = True
    language_surface_reason: str = ""

    raw_response: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers: normalization & IO
# ---------------------------------------------------------------------------


def _normalize_gender(raw: Any) -> str:
    if raw is None:
        return ""
    s = str(raw).strip().lower()
    if s in {"male", "m", "man", "masculine", "q6581097"}:
        return "m"
    if s in {"female", "f", "woman", "feminine", "q6581072"}:
        return "f"
    return ""


def _normalize_lang(raw: Any) -> str:
    return str(raw or "").strip().lower()


def _ensure_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        if "," in value:
            return [v.strip() for v in value.split(",") if v.strip()]
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _load_json_records(path: Path) -> List[Dict[str, Any]]:
    log.info(f"Loading JSON records from {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text[0] == "[":
        return json.loads(text)
    records: List[Dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def _load_csv_records(path: Path) -> List[Dict[str, Any]]:
    log.info(f"Loading CSV records from {path}")
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return records


def load_local_persons(path: Path) -> List[PersonRecord]:
    suffix = path.suffix.lower()
    if suffix in {".json", ".jsonl", ".ndjson"}:
        raw_records = _load_json_records(path)
    elif suffix == ".csv":
        raw_records = _load_csv_records(path)
    else:
        raise ValueError(f"Unsupported input extension: {suffix}")

    persons: List[PersonRecord] = []

    for rec in raw_records:
        try:
            pid = str(rec.get("id") or rec.get("qid") or "").strip()
            if not pid:
                log.warning(f"Skipping record without id: {rec}")
                continue

            label = str(rec.get("label") or rec.get("name") or pid).strip()
            gender = str(rec.get("gender") or "").strip()

            prof_lemmas = _ensure_list(
                rec.get("profession_lemmas")
                or rec.get("occupations")
                or rec.get("occupation_lemmas")
            )
            nat_lemmas = _ensure_list(
                rec.get("nationality_lemmas")
                or rec.get("nationalities")
                or rec.get("citizenship_lemmas")
            )

            gold_bios_raw = rec.get("gold_bios") or {}
            gold_bios: Dict[str, str] = {}

            if isinstance(gold_bios_raw, str):
                try:
                    gold_bios = json.loads(gold_bios_raw)
                except json.JSONDecodeError:
                    log.warning(f"Could not parse gold_bios JSON for id={pid}: {gold_bios_raw}")
            elif isinstance(gold_bios_raw, dict):
                gold_bios = {
                    _normalize_lang(k): str(v).strip()
                    for k, v in gold_bios_raw.items()
                    if str(v).strip()
                }

            persons.append(
                PersonRecord(
                    id=pid,
                    label=label,
                    gender=gender,
                    profession_lemmas=prof_lemmas,
                    nationality_lemmas=nat_lemmas,
                    gold_bios=gold_bios,
                )
            )
        except Exception as exc:
            log.error(f"Error processing record {rec}: {exc}")

    log.info(f"Loaded {len(persons)} person records from {path}")
    return persons


# ---------------------------------------------------------------------------
# Wikidata SPARQL helper (optional)
# ---------------------------------------------------------------------------


def fetch_wikidata_persons(limit: int) -> List[PersonRecord]:
    try:
        import requests  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "The 'requests' library is required for --source wikidata. "
            "Install it with 'pip install requests' or use --source local."
        ) from exc

    log.info(f"Querying Wikidata SPARQL endpoint for {limit} humans…")

    endpoint = "https://query.wikidata.org/sparql"
    sparql = f"""
    SELECT ?person ?personLabel ?genderLabel ?occLabel ?natLabel
    WHERE {{
      ?person wdt:P31 wd:Q5 .
      OPTIONAL {{ ?person wdt:P21 ?gender. }}
      OPTIONAL {{ ?person wdt:P106 ?occ. }}
      OPTIONAL {{ ?person wdt:P27 ?nat. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT {limit * 5}
    """

    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "semantik-architect-eval-bios/0.3 (tooling)",
    }

    resp = requests.get(endpoint, params={"query": sparql}, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    bindings = data.get("results", {}).get("bindings", [])
    agg: Dict[str, Dict[str, Any]] = {}

    def get_id(uri: str) -> str:
        return uri.rsplit("/", 1)[-1]

    for row in bindings:
        person_uri = row.get("person", {}).get("value")
        if not person_uri:
            continue
        pid = get_id(person_uri)

        rec = agg.setdefault(
            pid,
            {"id": pid, "label": "", "gender": "", "professions": set(), "nationalities": set()},
        )

        label = row.get("personLabel", {}).get("value")
        if label:
            rec["label"] = label

        gender_label = row.get("genderLabel", {}).get("value")
        if gender_label and not rec["gender"]:
            rec["gender"] = gender_label

        occ_label = row.get("occLabel", {}).get("value")
        if occ_label:
            rec["professions"].add(occ_label)

        nat_label = row.get("natLabel", {}).get("value")
        if nat_label:
            rec["nationalities"].add(nat_label)

    persons: List[PersonRecord] = []
    for pid, rec in list(agg.items())[:limit]:
        label = rec.get("label") or pid
        gender = rec.get("gender") or ""
        prof_lemmas = [p.lower() for p in sorted(rec.get("professions") or [])]
        nat_lemmas = [n.lower() for n in sorted(rec.get("nationalities") or [])]
        persons.append(
            PersonRecord(
                id=pid,
                label=label,
                gender=gender,
                profession_lemmas=prof_lemmas,
                nationality_lemmas=nat_lemmas,
            )
        )

    log.info(f"Retrieved {len(persons)} distinct persons from Wikidata")
    return persons


# ---------------------------------------------------------------------------
# HTTP API adapter
# ---------------------------------------------------------------------------


def _api_post_json(url: str, payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body.strip() else {}
    except urlerror.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from generation API: {body}") from exc
    except urlerror.URLError as exc:
        raise RuntimeError(f"Could not reach generation API: {exc}") from exc


def _build_bio_payload(
    *,
    person_id: str,
    name: str,
    gender_raw: str,
    profession_lemma: str,
    nationality_lemma: str,
) -> Dict[str, Any]:
    gender = _normalize_gender(gender_raw)

    subject = {
        "qid": person_id,
        "name": name,
        "gender": gender,
        "profession": profession_lemma,
        "nationality": nationality_lemma,
    }

    properties = {
        "profession": profession_lemma,
        "nationality": nationality_lemma,
    }

    payload = {
        "frame_type": "bio",
        "name": name,
        "profession": profession_lemma,
        "nationality": nationality_lemma,
        "gender": gender,
        "subject": subject,
        "properties": properties,
    }

    return payload


# ---------------------------------------------------------------------------
# Contract and acceptance validation
# ---------------------------------------------------------------------------


def _validate_public_response_contract(response: Dict[str, Any], requested_lang: str) -> List[str]:
    errors: List[str] = []

    if not isinstance(response, dict):
        return ["response is not a JSON object"]

    for field_name in EXPECTED_PUBLIC_FIELDS:
        if field_name not in response:
            errors.append(f"missing top-level '{field_name}'")

    text = response.get("text")
    if not _is_nonempty_string(text):
        errors.append("missing or invalid top-level 'text'")

    lang_code = response.get("lang_code")
    if not isinstance(lang_code, str):
        errors.append("missing or invalid top-level 'lang_code'")
    elif _normalize_lang(lang_code) != _normalize_lang(requested_lang):
        errors.append(
            f"top-level lang_code mismatch: expected {requested_lang}, got {lang_code}"
        )

    construction_id = response.get("construction_id")
    if not _is_nonempty_string(construction_id):
        errors.append("missing or invalid top-level 'construction_id'")

    renderer_backend = response.get("renderer_backend")
    if not _is_nonempty_string(renderer_backend):
        errors.append("missing or invalid top-level 'renderer_backend'")

    if not isinstance(response.get("fallback_used"), bool):
        errors.append("missing or invalid top-level 'fallback_used'")

    tokens = response.get("tokens")
    if not isinstance(tokens, list) or not tokens or any(not isinstance(t, str) for t in tokens):
        errors.append("missing or invalid top-level 'tokens'")

    debug_info = response.get("debug_info")
    if not isinstance(debug_info, dict):
        errors.append("missing or invalid top-level 'debug_info'")
    else:
        for key in REQUIRED_DEBUG_FIELDS:
            if key not in debug_info:
                errors.append(f"debug_info missing '{key}'")

        if not _is_nonempty_string(debug_info.get("runtime_path")):
            errors.append("invalid debug_info.runtime_path")

        slot_keys = debug_info.get("slot_keys")
        if not isinstance(slot_keys, list) or any(not isinstance(k, str) for k in slot_keys):
            errors.append("invalid debug_info.slot_keys")

        # Required parity with top-level fields
        for key in ("construction_id", "renderer_backend", "lang_code", "fallback_used"):
            if key in debug_info and response.get(key) != debug_info.get(key):
                errors.append(f"top-level {key} does not match debug_info.{key}")

    generation_time_ms = response.get("generation_time_ms")
    if not isinstance(generation_time_ms, (int, float)):
        errors.append("missing or invalid top-level 'generation_time_ms'")

    return errors


def _looks_obviously_english(text: str) -> bool:
    s = f" {text.strip().lower()} "
    markers = [
        " is ",
        " is a ",
        " was ",
        " were ",
        " participated in ",
        " british ",
        " mathematician ",
        " physicist ",
        " chemist ",
        " writer ",
        " scientist ",
    ]
    return any(m in s for m in markers)


def _looks_obviously_french(text: str) -> bool:
    s = f" {text.strip().lower()} "
    markers = [
        " est ",
        " était ",
        " participe à ",
        " participé à ",
        " français ",
        " française ",
        " britannique ",
        " mathématicien ",
        " mathématicienne ",
        " physicien ",
        " physicienne ",
        " chimiste ",
        " écrivain ",
        " écrivaine ",
        " scientifique ",
    ]
    return any(m in s for m in markers)


def _check_language_surface(
    *,
    requested_lang: str,
    resolved_language: str,
    output: str,
) -> tuple[bool, str]:
    if not output.strip():
        return False, "empty_output"

    lang = _normalize_lang(requested_lang)
    resolved = str(resolved_language or "").strip()

    if lang == "fr":
        if resolved == "WikiFre" and _looks_obviously_english(output):
            return False, "resolved_wikifre_but_surface_looks_english"
        if _looks_obviously_english(output) and not _looks_obviously_french(output):
            return False, "requested_fr_but_surface_looks_english"

    if lang == "en":
        if resolved == "WikiEng" and _looks_obviously_french(output):
            return False, "resolved_wikieng_but_surface_looks_french"
        if _looks_obviously_french(output) and not _looks_obviously_english(output):
            return False, "requested_en_but_surface_looks_french"

    return True, ""


def _validate_acceptance_semantics(response: Dict[str, Any], requested_lang: str) -> List[str]:
    """
    Validate final EN/FR cutover semantics, not just transport shape.
    """
    errors: List[str] = []

    if not isinstance(response, dict):
        return ["response is not a JSON object"]

    debug_info = response.get("debug_info") if isinstance(response.get("debug_info"), dict) else {}

    runtime_path = str(debug_info.get("runtime_path") or "").strip()
    if runtime_path != NOMINAL_RUNTIME_PATH:
        errors.append(
            f"runtime_path is not nominal planner-first: expected {NOMINAL_RUNTIME_PATH}, got {runtime_path or '<missing>'}"
        )

    fallback_used = response.get("fallback_used")
    if fallback_used is not False:
        errors.append(
            f"fallback_used must be false for EN/FR nominal acceptance, got {fallback_used!r}"
        )

    lang = _normalize_lang(requested_lang)
    expected_resolved = EXPECTED_RESOLVED_LANGUAGE_BY_LANG.get(lang)
    resolved_language = str(debug_info.get("resolved_language") or "").strip()

    if expected_resolved:
        if not resolved_language:
            errors.append(
                f"missing debug_info.resolved_language for requested language {lang}"
            )
        elif resolved_language != expected_resolved:
            errors.append(
                f"resolved_language mismatch: expected {expected_resolved}, got {resolved_language}"
            )

    return errors


def _normalize_text_for_match(text: str) -> str:
    return " ".join(str(text or "").strip().split()).casefold()


def _render_bio_via_api(
    *,
    api_base: str,
    timeout: int,
    person_id: str,
    name: str,
    gender_raw: str,
    profession_lemma: str,
    nationality_lemma: str,
    lang_code: str,
) -> Dict[str, Any]:
    payload = _build_bio_payload(
        person_id=person_id,
        name=name,
        gender_raw=gender_raw,
        profession_lemma=profession_lemma,
        nationality_lemma=nationality_lemma,
    )
    url = f"{api_base.rstrip('/')}/generate/{_normalize_lang(lang_code)}"
    return _api_post_json(url, payload, timeout=timeout)


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------


def evaluate_persons(
    persons: Iterable[PersonRecord],
    langs: List[str],
    *,
    api_base: str,
    timeout: int,
    max_items: Optional[int] = None,
) -> List[EvalResult]:
    results: List[EvalResult] = []
    count = 0

    for person in persons:
        if max_items is not None and count >= max_items:
            break
        count += 1

        for lang in langs:
            prof_lemma = person.profession_lemmas[0] if person.profession_lemmas else ""
            nat_lemma = person.nationality_lemmas[0] if person.nationality_lemmas else ""

            try:
                response = _render_bio_via_api(
                    api_base=api_base,
                    timeout=timeout,
                    person_id=person.id,
                    name=person.label,
                    gender_raw=person.gender,
                    profession_lemma=prof_lemma,
                    nationality_lemma=nat_lemma,
                    lang_code=lang,
                )
            except Exception as exc:
                response = {
                    "text": "",
                    "lang_code": _normalize_lang(lang),
                    "construction_id": "",
                    "renderer_backend": "",
                    "fallback_used": False,
                    "tokens": [],
                    "debug_info": {
                        "runtime_path": "evaluation_error",
                        "lang_code": _normalize_lang(lang),
                        "construction_id": "",
                        "renderer_backend": "",
                        "fallback_used": False,
                        "slot_keys": [],
                        "error": str(exc),
                    },
                    "generation_time_ms": 0.0,
                }

            contract_errors = _validate_public_response_contract(response, lang)
            contract_ok = not contract_errors

            acceptance_errors = _validate_acceptance_semantics(response, lang)
            acceptance_ok = not acceptance_errors

            output = str(response.get("text") or "").strip()
            rendered = bool(output)

            debug_info = response.get("debug_info") if isinstance(response.get("debug_info"), dict) else {}
            resolved_language = str(debug_info.get("resolved_language") or "")
            runtime_path = str(debug_info.get("runtime_path") or "")
            fallback_used = bool(response.get("fallback_used", False))
            response_lang_code = _normalize_lang(response.get("lang_code"))
            construction_id = str(response.get("construction_id") or "")
            renderer_backend = str(
                response.get("renderer_backend")
                or debug_info.get("renderer_backend")
                or ""
            )

            try:
                generation_time_ms = float(response.get("generation_time_ms") or 0.0)
            except (TypeError, ValueError):
                generation_time_ms = 0.0

            language_surface_ok, language_surface_reason = _check_language_surface(
                requested_lang=lang,
                resolved_language=resolved_language,
                output=output,
            )

            gold = person.gold_bios.get(_normalize_lang(lang), "")
            has_gold = bool(gold.strip())
            exact_match = bool(
                has_gold and _normalize_text_for_match(gold) == _normalize_text_for_match(output)
            )

            results.append(
                EvalResult(
                    person_id=person.id,
                    lang=_normalize_lang(lang),
                    rendered=rendered,
                    output=output,
                    has_gold=has_gold,
                    exact_match=exact_match,
                    contract_ok=contract_ok,
                    contract_errors=contract_errors,
                    acceptance_ok=acceptance_ok,
                    acceptance_errors=acceptance_errors,
                    response_lang_code=response_lang_code,
                    construction_id=construction_id,
                    renderer_backend=renderer_backend,
                    runtime_path=runtime_path,
                    resolved_language=resolved_language,
                    fallback_used=fallback_used,
                    generation_time_ms=generation_time_ms,
                    language_surface_ok=language_surface_ok,
                    language_surface_reason=language_surface_reason,
                    raw_response=response,
                )
            )

    return results


def summarize_results(results: List[EvalResult]) -> None:
    if not results:
        print("No evaluation results.")
        return

    by_lang: Dict[str, List[EvalResult]] = {}
    for r in results:
        by_lang.setdefault(r.lang, []).append(r)

    print("\n=== Biography evaluation summary ===\n")
    print(f"Total person-language pairs: {len(results)}\n")

    header = (
        f"{'Lang':<6} {'Pairs':>8} {'Rendered':>10} {'Coverage%':>10} "
        f"{'HasGold':>8} {'Exact':>8} {'ContractOK':>11} {'AcceptOK':>10} {'LangOK':>8}"
    )
    print(header)
    print("-" * len(header))

    for lang, rs in sorted(by_lang.items()):
        total = len(rs)
        rendered = sum(1 for r in rs if r.rendered)
        has_gold = sum(1 for r in rs if r.has_gold)
        exact = sum(1 for r in rs if r.exact_match)
        contract_ok = sum(1 for r in rs if r.contract_ok)
        acceptance_ok = sum(1 for r in rs if r.acceptance_ok)
        lang_ok = sum(1 for r in rs if r.language_surface_ok)
        coverage = 100.0 * rendered / total if total else 0.0

        print(
            f"{lang:<6} {total:>8} {rendered:>10} {coverage:>9.1f}% "
            f"{has_gold:>8} {exact:>8} {contract_ok:>11} {acceptance_ok:>10} {lang_ok:>8}"
        )

    print()


def dump_results_csv(results: List[EvalResult], path: Path) -> None:
    log.info(f"Writing detailed results CSV to {path}")
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "person_id",
                "lang",
                "rendered",
                "has_gold",
                "exact_match",
                "contract_ok",
                "contract_errors",
                "acceptance_ok",
                "acceptance_errors",
                "response_lang_code",
                "construction_id",
                "renderer_backend",
                "runtime_path",
                "resolved_language",
                "fallback_used",
                "generation_time_ms",
                "language_surface_ok",
                "language_surface_reason",
                "output",
            ]
        )
        for r in results:
            writer.writerow(
                [
                    r.person_id,
                    r.lang,
                    int(r.rendered),
                    int(r.has_gold),
                    int(r.exact_match),
                    int(r.contract_ok),
                    "; ".join(r.contract_errors),
                    int(r.acceptance_ok),
                    "; ".join(r.acceptance_errors),
                    r.response_lang_code,
                    r.construction_id,
                    r.renderer_backend,
                    r.runtime_path,
                    r.resolved_language,
                    int(r.fallback_used),
                    r.generation_time_ms,
                    int(r.language_surface_ok),
                    r.language_surface_reason,
                    r.output,
                ]
            )


def print_sample_outputs(
    persons: List[PersonRecord],
    results: List[EvalResult],
    langs: List[str],
    n_samples: int,
) -> None:
    if n_samples <= 0:
        return

    by_lang: Dict[str, List[EvalResult]] = {}
    for r in results:
        if r.rendered:
            by_lang.setdefault(r.lang, []).append(r)

    persons_by_id: Dict[str, PersonRecord] = {p.id: p for p in persons}

    print("\n=== Sample outputs ===\n")

    for lang in langs:
        lang_rs = by_lang.get(_normalize_lang(lang), [])
        if not lang_rs:
            print(f"[{lang}] No rendered outputs.")
            continue

        print(f"[{lang}]")
        sample = random.sample(lang_rs, min(n_samples, len(lang_rs)))
        for r in sample:
            person = persons_by_id.get(r.person_id)
            name = person.label if person else r.person_id
            suffix = []
            if not r.contract_ok:
                suffix.append("CONTRACT_FAIL")
            if not r.acceptance_ok:
                suffix.extend(r.acceptance_errors)
            if not r.language_surface_ok:
                suffix.append(r.language_surface_reason or "LANG_FAIL")
            tag = f" [{' | '.join(suffix)}]" if suffix else ""
            print(f"- {name}: {r.output}{tag}")
        print()


def compute_failure_count(results: List[EvalResult]) -> int:
    count = 0
    for r in results:
        if not r.contract_ok:
            count += 1
        elif not r.acceptance_ok:
            count += 1
        elif not r.language_surface_ok:
            count += 1
    return count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate bio generation against the live SemantiK Architect API."
    )

    parser.add_argument(
        "--source",
        choices=["local", "wikidata"],
        default="local",
        help="Data source: 'local' JSON/CSV file or live 'wikidata' SPARQL.",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Path to local JSON/JSONL/CSV file (required for --source local).",
    )
    parser.add_argument(
        "--langs",
        nargs="+",
        default=["en"],
        help="Language codes, e.g. --langs en fr OR --langs en,fr",
    )
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of persons to evaluate.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling / sample selection.")
    parser.add_argument("--output-csv", type=str, help="Write detailed person-language results to this CSV path.")
    parser.add_argument("--print-samples", type=int, default=0, help="Print up to N rendered samples per language.")
    parser.add_argument(
        "--api-base",
        type=str,
        default=os.getenv("SEMANTIK_API_BASE", "http://localhost:8000/api/v1"),
        help="Base URL for the SemantiK API.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP timeout in seconds for generation calls.",
    )
    parser.add_argument(
        "--no-fail-on-issues",
        action="store_true",
        help="Always exit 0 even if contract, acceptance, or language-surface failures are found.",
    )

    return parser.parse_args(argv)


def _parse_langs(raw_parts: List[str]) -> List[str]:
    langs: List[str] = []
    for part in raw_parts:
        for tok in str(part).split(","):
            tok = _normalize_lang(tok)
            if tok:
                langs.append(tok)

    seen = set()
    out: List[str] = []
    for lang in langs:
        if lang not in seen:
            seen.add(lang)
            out.append(lang)
    return out


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)

    langs = _parse_langs(args.langs)
    random.seed(args.seed)

    log.header(
        {
            "Source": args.source,
            "Langs": ",".join(langs),
            "Limit": args.limit,
            "API": args.api_base,
        }
    )

    if not langs:
        log.error("No languages specified via --langs.", fatal=True)

    if args.source == "local":
        if not args.input:
            log.error("--input is required when --source local.", fatal=True)

        input_path = Path(args.input)
        if not input_path.exists():
            log.error(f"Input file not found: {input_path}", fatal=True)

        log.stage("Fetch", f"Loading persons from {input_path}...")
        persons = load_local_persons(input_path)
    else:
        log.stage("Fetch", f"Querying Wikidata for {args.limit} persons...")
        persons = fetch_wikidata_persons(limit=args.limit)

    if not persons:
        log.error("No person records loaded; nothing to evaluate.", fatal=True)

    if args.source == "local" and len(persons) > args.limit:
        log.info(f"Subsampling {args.limit} persons out of {len(persons)} with seed={args.seed}")
        persons = random.sample(persons, args.limit)

    log.stage("Evaluate", f"Rendering bios for {len(persons)} persons in {len(langs)} languages...")
    results = evaluate_persons(
        persons,
        langs,
        api_base=args.api_base,
        timeout=args.timeout,
        max_items=args.limit,
    )

    summarize_results(results)

    if args.output_csv:
        log.stage("Export", f"Writing results to {args.output_csv}")
        dump_results_csv(results, Path(args.output_csv))

    if args.print_samples > 0:
        print_sample_outputs(persons, results, langs, args.print_samples)

    failure_count = compute_failure_count(results)
    contract_failures = sum(1 for r in results if not r.contract_ok)
    acceptance_failures = sum(1 for r in results if not r.acceptance_ok)
    language_failures = sum(1 for r in results if not r.language_surface_ok)

    log.summary(
        {
            "Total Pairs": len(results),
            "Contract Failures": contract_failures,
            "Acceptance Failures": acceptance_failures,
            "Language Failures": language_failures,
            "Exit Code": 0 if args.no_fail_on_issues or failure_count == 0 else 1,
        }
    )

    if not args.no_fail_on_issues and failure_count > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()


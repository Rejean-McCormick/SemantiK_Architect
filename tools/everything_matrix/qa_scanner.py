# tools/everything_matrix/qa_scanner.py
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Set

try:
    import pgf  # type: ignore
except ImportError:
    pgf = None

# Aligned with the suite:
# - Side-effect free by default
# - Provides one-shot API for build_index.py:
#     scan_all_artifacts(gf_root) -> {iso2: {"BIN": float, "TEST": float}}
# - Keeps scan_artifacts(iso2, gf_root) for debug / compatibility
# - Uses shared normalization (iso2 canonical) via norm.py
# - No printing by default (library mode); CLI/debug can print
import norm
import scoring

SCANNER_VERSION = "qa_scanner/2.5"

# --- GLOBAL CACHE ---
# Prevent reloading the ~50MB PGF binary many times.
_CACHED_GRAMMAR: Any = None
_CACHED_PGF_PATH: Optional[Path] = None

# -------------------------
# PGF loading (singleton)
# -------------------------


def load_grammar_once(pgf_path: Path):
    """
    Singleton loader for the PGF binary.
    Loads it once into memory and returns the reference for subsequent calls.
    """
    global _CACHED_GRAMMAR, _CACHED_PGF_PATH

    if _CACHED_GRAMMAR is not None and _CACHED_PGF_PATH == pgf_path:
        return _CACHED_GRAMMAR

    if not pgf:
        _CACHED_GRAMMAR = None
        _CACHED_PGF_PATH = pgf_path
        return None

    if pgf_path.is_file():
        try:
            _CACHED_GRAMMAR = pgf.readPGF(str(pgf_path))
            _CACHED_PGF_PATH = pgf_path
            return _CACHED_GRAMMAR
        except Exception:
            _CACHED_GRAMMAR = None
            _CACHED_PGF_PATH = pgf_path
            return None

    _CACHED_GRAMMAR = None
    _CACHED_PGF_PATH = pgf_path
    return None


# -------------------------
# JUnit parsing
# -------------------------

_LANG_TOKEN_RE_TEMPLATE = r"(^|[^a-z0-9]){tok}([^a-z0-9]|$)"


def _compile_lang_matchers(iso2: str) -> Set[re.Pattern]:
    """
    Regex matchers for attributing a testcase to a language.
    We are strict enough to avoid many false positives.
    """
    tok = (iso2 or "").strip().casefold()
    matchers: Set[re.Pattern] = set()
    if not tok:
        return matchers

    patterns = [
        rf"_{re.escape(tok)}(\b|[^a-z0-9])",
        rf"-{re.escape(tok)}(\b|[^a-z0-9])",
        rf"\[{re.escape(tok)}\]",
        rf"\({re.escape(tok)}\)",
        rf"lang\s*=\s*{re.escape(tok)}(\b|[^a-z0-9])",
        rf"language\s*=\s*{re.escape(tok)}(\b|[^a-z0-9])",
        _LANG_TOKEN_RE_TEMPLATE.format(tok=re.escape(tok)),
    ]

    for p in patterns:
        matchers.add(re.compile(p, re.IGNORECASE))

    return matchers


def _testcase_text(testcase: ET.Element) -> str:
    parts = [
        testcase.get("name", "") or "",
        testcase.get("classname", "") or "",
        testcase.get("file", "") or "",
    ]
    return " ".join(parts).lower()


def _is_failure(testcase: ET.Element) -> bool:
    return testcase.find("failure") is not None or testcase.find("error") is not None


def _is_skipped(testcase: ET.Element) -> bool:
    return testcase.find("skipped") is not None


def _parse_junit_report_pass_rates(path: Path, *, iso2s: Set[str]) -> Dict[str, float]:
    """
    Parses a JUnit XML file once and returns per-iso2 pass rates.

    Rules:
    - Only counts testcases whose identifiers appear to reference that iso2.
    - Skipped tests are excluded from the denominator.
    - If no matching testcases are found for a language, rate is 0.0.
    """
    rates: Dict[str, float] = {k: 0.0 for k in iso2s}
    if not path.is_file() or not iso2s:
        return rates

    try:
        tree = ET.parse(path)
        root = tree.getroot()

        # Precompile all matchers once
        matchers_by_iso2: Dict[str, Set[re.Pattern]] = {
            iso2: _compile_lang_matchers(iso2) for iso2 in iso2s
        }

        totals: Dict[str, int] = {k: 0 for k in iso2s}
        passed: Dict[str, int] = {k: 0 for k in iso2s}

        for testcase in root.iter("testcase"):
            text = _testcase_text(testcase)

            if _is_skipped(testcase):
                continue

            # Determine attribution (can match multiple; we count each match independently)
            hit_any = False
            for iso2, matchers in matchers_by_iso2.items():
                if not matchers:
                    continue
                if any(m.search(text) for m in matchers):
                    hit_any = True
                    totals[iso2] += 1
                    if not _is_failure(testcase):
                        passed[iso2] += 1

            if not hit_any:
                continue

        for iso2 in iso2s:
            t = totals.get(iso2, 0)
            if t <= 0:
                rates[iso2] = 0.0
            else:
                rates[iso2] = round(passed.get(iso2, 0) / t, 4)

        return rates

    except ET.ParseError:
        return rates
    except Exception:
        return rates


def _resolve_junit_path(*, repo: Path, cfg: Mapping[str, Any]) -> Path:
    """
    Default expected path: <repo>/data/tests/reports/junit.xml
    Optional override via env var: AWA_JUNIT_XML
    Optional override via config: cfg["qa"]["junit_xml"]
    """
    env_override = os.getenv("AWA_JUNIT_XML", "").strip()
    if env_override:
        return Path(env_override)

    qa_cfg = cfg.get("qa") if isinstance(cfg.get("qa"), dict) else {}
    rel = qa_cfg.get("junit_xml")
    if isinstance(rel, str) and rel.strip():
        return repo / rel

    return repo / "data" / "tests" / "reports" / "junit.xml"


# -------------------------
# Zone D scanning
# -------------------------


def scan_artifacts(iso2: str, gf_root: Path) -> Dict[str, float]:
    """
    Debug / compatibility API: per-language scan.

    Returns (0.0 - 10.0 scale):
      BIN: 10.0 if language is present in AbstractWiki.pgf, else 0.0.
      TEST: pass_rate * 10 from junit attribution (single-language parse here).
            (Build Index will use scan_all_artifacts for one-shot parsing instead.)
    """
    iso2 = (iso2 or "").strip().casefold()
    stats: Dict[str, float] = {"BIN": 0.0, "TEST": 0.0}

    if len(iso2) != 2 or not isinstance(gf_root, Path):
        return stats

    ctx = norm.NormContext.load()
    repo = ctx.repo

    # 1) BIN via PGF
    pgf_path = gf_root / "AbstractWiki.pgf"
    grammar = load_grammar_once(pgf_path)
    if grammar:
        try:
            # old naming: WikiFr / WikiFR
            target1 = f"Wiki{iso2.capitalize()}"
            target2 = f"Wiki{iso2.upper()}"
            langs = getattr(grammar, "languages", None)
            if isinstance(langs, dict):
                if target1 in langs or target2 in langs:
                    stats["BIN"] = 10.0
                else:
                    # suffix fallback
                    for key in langs.keys():
                        if str(key).endswith(iso2.capitalize()) or str(key).endswith(iso2.upper()):
                            stats["BIN"] = 10.0
                            break
        except Exception:
            pass

    # 2) TEST via JUnit (single-language fallback parse)
    junit_path = _resolve_junit_path(repo=repo, cfg=ctx.cfg)
    rates = _parse_junit_report_pass_rates(junit_path, iso2s={iso2})
    stats["TEST"] = round(float(rates.get(iso2, 0.0)) * 10.0, 1)

    stats["BIN"] = scoring.clamp10(stats["BIN"])
    stats["TEST"] = scoring.clamp10(stats["TEST"])
    return stats


def scan_all_artifacts(gf_root: Path) -> Dict[str, Dict[str, float]]:
    """
    Contract for build_index.py:
      scan_all_artifacts(gf_root) -> {iso2: {"BIN": float, "TEST": float}}

    One-shot behavior:
      - Loads AbstractWiki.pgf once
      - Parses junit.xml once
      - Produces iso2-keyed results (lowercase)
    """
    out: Dict[str, Dict[str, float]] = {}
    if not isinstance(gf_root, Path):
        return out

    ctx = norm.NormContext.load()
    repo = ctx.repo

    # Universe: start from iso map (authoritative list) + folders present in gf/generated/src
    iso2s: Set[str] = set(ctx.iso2_names.keys())

    # Add any iso2-looking folders from gf/generated/src (helps when iso map lags)
    gen_src = gf_root / "generated" / "src"
    if gen_src.is_dir():
        for p in gen_src.iterdir():
            if p.is_dir():
                iso2 = ctx.to_iso2(p.name)
                if iso2:
                    iso2s.add(iso2)

    if not iso2s:
        return out

    # 1) BIN via PGF once
    pgf_path = gf_root / "AbstractWiki.pgf"
    grammar = load_grammar_once(pgf_path)

    bin_by_iso2: Dict[str, float] = {k: 0.0 for k in iso2s}
    if grammar:
        try:
            langs = getattr(grammar, "languages", None)
            if isinstance(langs, dict):
                lang_keys = list(langs.keys())
                for iso2 in iso2s:
                    target1 = f"Wiki{iso2.capitalize()}"
                    target2 = f"Wiki{iso2.upper()}"
                    if target1 in langs or target2 in langs:
                        bin_by_iso2[iso2] = 10.0
                        continue
                    # suffix fallback (slower, but still one-shot overall)
                    for key in lang_keys:
                        sk = str(key)
                        if sk.endswith(iso2.capitalize()) or sk.endswith(iso2.upper()):
                            bin_by_iso2[iso2] = 10.0
                            break
        except Exception:
            pass

    # 2) TEST via JUnit once
    junit_path = _resolve_junit_path(repo=repo, cfg=ctx.cfg)
    pass_rates = _parse_junit_report_pass_rates(junit_path, iso2s=iso2s)

    for iso2 in sorted(iso2s):
        out[iso2] = {
            "BIN": scoring.clamp10(bin_by_iso2.get(iso2, 0.0)),
            "TEST": scoring.clamp10(round(float(pass_rates.get(iso2, 0.0)) * 10.0, 1)),
        }

    return out


if __name__ == "__main__":
    import logging
    import time
    import json

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    ctx = norm.NormContext.load()
    qa_cfg = ctx.cfg.get("qa") if isinstance(ctx.cfg.get("qa"), dict) else {}
    gf_root = ctx.repo / str(qa_cfg.get("gf_root", "gf"))

    results = scan_all_artifacts(gf_root)
    meta = {
        "scanner": SCANNER_VERSION,
        "generated_at": int(time.time()),
        "generated_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "languages": len(results),
        "gf_root": str(gf_root).replace("\\", "/"),
    }
    print(json.dumps({"meta": meta, "languages": results}, indent=2, ensure_ascii=False, sort_keys=True))
    print(f"✅ Scanned QA artifacts for {len(results)} languages.")

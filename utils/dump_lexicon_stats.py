# utils/dump_lexicon_stats.py
"""
utils/dump_lexicon_stats.py
---------------------------

Quick statistics over the JSON lexicon files in data/lexicon/.

This is a lightweight, data-driven script: it reads the raw JSON files
directly, without requiring the full `lexicon` Python package to be
implemented. It assumes the files follow the schema used in this
project:

    {
      "_meta": { ... },
      "lemmas": {
        "lemma_string": {
          "pos": "NOUN" | "ADJ" | "VERB" | ...,
          "human": true/false (optional),
          "nationality": true/false (optional),
          ...
        },
        ...
      }
    }

By default it scans all *.json files under data/lexicon/, merges files
for the same language (e.g. en_lexicon.json + en_people.json), and
prints per-language stats.

Usage
=====

From project root:

    python utils/dump_lexicon_stats.py
    python utils/dump_lexicon_stats.py --langs en fr
    python utils/dump_lexicon_stats.py --format json --out /tmp/lexicon_stats.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

# ---------------------------------------------------------------------------
# Project root & logging
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

DEFAULT_LEXICON_DIR = PROJECT_ROOT / "data" / "lexicon"

# [REFACTOR] Use the standardized ToolLogger for GUI-compatible output
try:
    from utils.tool_logger import ToolLogger  # type: ignore
    logger = ToolLogger(__file__)
except Exception:  # pragma: no cover
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
    logger = logging.getLogger("dump_stats")


def _logger_start(title: str) -> None:
    """Call ToolLogger.start if available, but be robust to signature differences."""
    if hasattr(logger, "start"):
        try:
            logger.start(title)  # type: ignore[attr-defined]
        except TypeError:
            # Some ToolLogger variants may not accept args
            try:
                logger.start()  # type: ignore[attr-defined]
            except Exception:
                pass


def _logger_finish(message: str, *, success: Optional[bool] = None, details: Optional[dict] = None) -> None:
    """Call ToolLogger.finish if available, but be robust to signature differences."""
    if not hasattr(logger, "finish"):
        return
    try:
        # Most flexible attempt (keywords)
        kwargs: dict = {}
        if success is not None:
            kwargs["success"] = success
        if details is not None:
            kwargs["details"] = details
        logger.finish(message=message, **kwargs)  # type: ignore[attr-defined]
    except TypeError:
        # Fallback: positional message only
        try:
            logger.finish(message)  # type: ignore[attr-defined]
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Helpers for finding / grouping lexicon files
# ---------------------------------------------------------------------------

def _infer_lang_from_filename(filename: str) -> str:
    """
    Infer a language code from a lexicon JSON filename.

    Heuristic:
        - Take the stem (filename without extension).
        - Use the part before the first underscore, if present.
          Example: "en_lexicon" -> "en", "en_people" -> "en"
        - Otherwise use the whole stem.
    """
    stem = Path(filename).stem
    return stem.split("_", 1)[0] if "_" in stem else stem


def find_lexicon_files(lexicon_dir: str | Path, langs: Iterable[str] | None = None) -> Dict[str, List[str]]:
    """
    Scan lexicon_dir for JSON lexicon files and group them by language code.

    Args:
        lexicon_dir:
            Directory containing *.json lexicon files.
        langs:
            Optional iterable of language codes to restrict to. If None,
            all languages are included.

    Returns:
        Mapping: lang_code → list of JSON file paths (absolute).
    """
    lexicon_dir = Path(lexicon_dir)

    target_langs = {s.strip() for s in langs if s.strip()} if langs is not None else None
    by_lang: Dict[str, List[str]] = defaultdict(list)

    if not lexicon_dir.is_dir():
        logger.error(f"Lexicon directory not found: {lexicon_dir}")
        raise FileNotFoundError(f"Lexicon directory not found: {lexicon_dir}")

    # Deterministic ordering
    for path in sorted(lexicon_dir.iterdir(), key=lambda p: p.name):
        if not path.is_file() or path.suffix.lower() != ".json":
            continue

        lang = _infer_lang_from_filename(path.name)
        if target_langs is not None and lang not in target_langs:
            continue

        by_lang[lang].append(str(path.resolve()))

    # Also sort each language group deterministically
    for lang in list(by_lang.keys()):
        by_lang[lang].sort(key=lambda p: os.path.basename(p))

    return by_lang


# ---------------------------------------------------------------------------
# Stats computation
# ---------------------------------------------------------------------------

@dataclass
class MergeInfo:
    files_read: int = 0
    files_failed: int = 0
    overrides: int = 0
    invalid_lemmas_container: int = 0   # "lemmas" exists but is not a dict
    invalid_entries: int = 0            # lemma entry is not a dict


@dataclass
class LangStats:
    lang: str
    files: List[str]
    total_lemmas: int
    pos_counts: Dict[str, int]
    human_nouns: int
    nationality_adjs: int
    overrides: int
    invalid_entries: int

    @property
    def human_nouns_pct(self) -> float:
        return (100.0 * self.human_nouns / self.total_lemmas) if self.total_lemmas else 0.0

    @property
    def nationality_adjs_pct(self) -> float:
        return (100.0 * self.nationality_adjs / self.total_lemmas) if self.total_lemmas else 0.0


def load_lemmas_from_files(files: Iterable[str]) -> Tuple[Dict[str, dict], MergeInfo]:
    """
    Load and merge lemma dictionaries from a list of JSON files.

    For identical lemma keys across files for the same language,
    later files override earlier ones.

    Returns:
        (merged_lemmas, merge_info)
    """
    merged: Dict[str, dict] = {}
    info = MergeInfo()

    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            info.files_read += 1

            lemmas = data.get("lemmas", {})
            if not isinstance(lemmas, dict):
                info.invalid_lemmas_container += 1
                continue

            for k, v in lemmas.items():
                if k in merged:
                    info.overrides += 1
                # Only store dict entries; keep count of invalid ones.
                if isinstance(v, dict):
                    merged[k] = v
                else:
                    info.invalid_entries += 1

        except Exception as e:
            info.files_failed += 1
            logger.warning(f"Failed to read {path}: {e}")

    return merged, info


def compute_stats_for_lang(lang: str, lemmas: Mapping[str, dict], merge_info: MergeInfo) -> LangStats:
    """
    Compute basic statistics for a single language.
    """
    pos_counts: Counter[str] = Counter()
    human_nouns = 0
    nationality_adjs = 0
    invalid_entries = merge_info.invalid_entries

    for _, entry in lemmas.items():
        if not isinstance(entry, dict):
            invalid_entries += 1
            continue

        pos = str(entry.get("pos", "")).upper().strip()
        if pos:
            pos_counts[pos] += 1

        if pos == "NOUN" and bool(entry.get("human", False)):
            human_nouns += 1

        if pos == "ADJ" and bool(entry.get("nationality", False)):
            nationality_adjs += 1

    return LangStats(
        lang=lang,
        files=[],  # filled by caller
        total_lemmas=len(lemmas),
        pos_counts=dict(pos_counts),
        human_nouns=human_nouns,
        nationality_adjs=nationality_adjs,
        overrides=merge_info.overrides,
        invalid_entries=invalid_entries,
    )


def print_stats(stats: LangStats) -> None:
    """
    Pretty-print stats for a single language using the standardized logger.
    """
    logger.info(f"=== Lexicon stats for '{stats.lang}' ===")

    file_list = ", ".join(os.path.basename(f) for f in stats.files)
    logger.info(f"  Files: {file_list}")
    logger.info(f"  Total lemmas: {stats.total_lemmas}")
    logger.info(f"  Merge overrides (later file wins): {stats.overrides}")
    if stats.invalid_entries:
        logger.warning(f"  Invalid lemma entries skipped: {stats.invalid_entries}")

    if stats.total_lemmas == 0:
        logger.warning("  No lemmas found.")
        logger.info("")  # Spacer
        return

    logger.info("  By POS:")
    # Deterministic: sort primarily by count desc, then POS name asc
    for pos, count in sorted(stats.pos_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        pct = 100.0 * count / stats.total_lemmas
        logger.info(f"    {pos:<8} {count:5d} ({pct:5.1f}%)")

    logger.info("  Selected categories:")
    logger.info(f"    Human nouns:             {stats.human_nouns} ({stats.human_nouns_pct:5.1f}%)")
    logger.info(f"    Nationality adjectives:  {stats.nationality_adjs} ({stats.nationality_adjs_pct:5.1f}%)")
    logger.info("")  # Spacer


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dump basic statistics about lexicon JSON files.")
    parser.add_argument(
        "--lexicon-dir",
        "-d",
        default=str(DEFAULT_LEXICON_DIR),
        help=f"Directory containing lexicon JSON files (default: {DEFAULT_LEXICON_DIR})",
    )
    parser.add_argument(
        "--langs",
        "-l",
        nargs="*",
        help="Optional list of language codes to restrict to (e.g. en fr ru). "
             "If omitted, all languages found in the directory are included.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. 'text' logs to console; 'json' emits a machine-readable summary.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Optional output file path. If omitted, JSON is printed to stdout (and text uses logger).",
    )
    return parser


def main(argv: List[str] | None = None) -> None:
    _logger_start("Lexicon Stats Dump")

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    lexicon_dir = Path(args.lexicon_dir).expanduser().resolve()

    try:
        lang_files = find_lexicon_files(lexicon_dir, langs=args.langs)
    except FileNotFoundError:
        _logger_finish("Lexicon directory not found.", success=False)
        sys.exit(1)

    if not lang_files:
        msg = (
            f"No lexicon JSON files found for languages {args.langs} in {lexicon_dir}."
            if args.langs
            else f"No lexicon JSON files found in {lexicon_dir}."
        )
        logger.warning(msg)
        _logger_finish("No files found.", success=False, details={"lexicon_dir": str(lexicon_dir)})
        sys.exit(0)

    logger.info(f"Lexicon directory: {lexicon_dir}")
    logger.info(f"Languages found: {', '.join(sorted(lang_files.keys()))}")

    all_lang_stats: List[LangStats] = []
    global_lemmas = 0
    langs_processed = 0
    global_overrides = 0
    global_invalid_entries = 0

    for lang, files in sorted(lang_files.items(), key=lambda kv: kv[0]):
        lemmas, merge_info = load_lemmas_from_files(files)
        stats = compute_stats_for_lang(lang, lemmas, merge_info)
        stats.files = files

        all_lang_stats.append(stats)
        global_lemmas += stats.total_lemmas
        global_overrides += stats.overrides
        global_invalid_entries += stats.invalid_entries
        langs_processed += 1

        if args.format == "text":
            print_stats(stats)

    summary_data = {
        "lexicon_dir": str(lexicon_dir),
        "languages_scanned": langs_processed,
        "total_lemmas_found": global_lemmas,
        "total_merge_overrides": global_overrides,
        "total_invalid_entries": global_invalid_entries,
        "per_language": [asdict(s) for s in all_lang_stats],
    }

    if args.format == "json":
        payload = json.dumps(summary_data, ensure_ascii=False, indent=2)
        if args.out:
            out_path = Path(args.out).expanduser().resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(payload, encoding="utf-8")
            logger.info(f"Wrote JSON stats to: {out_path}")
        else:
            print(payload)

    _logger_finish(
        message=f"Stats dump complete. Found {global_lemmas} entries across {langs_processed} languages.",
        details={
            "languages_scanned": langs_processed,
            "total_lemmas_found": global_lemmas,
            "total_merge_overrides": global_overrides,
            "total_invalid_entries": global_invalid_entries,
        },
    )


if __name__ == "__main__":
    main()

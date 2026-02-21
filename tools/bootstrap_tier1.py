# tools/bootstrap_tier1.py
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

# Add project root for utils import
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from utils.tool_run_logging import tool_logging

# Defaults (kept compatible with builder/orchestrator.py path expectations)
DEFAULT_MATRIX_PATH = Path("data/indices/everything_matrix.json")
DEFAULT_RGL_SRC_PATH = Path("gf-rgl/src")

# IMPORTANT:
# - Bridge Syntax*.gf files default to generated/src so we do NOT modify gf-rgl/ (vendored/submodule).
# - App Wiki*.gf files default to gf/ because HIGH_ROAD compilation expects sources in gf/.
DEFAULT_BRIDGE_OUT_DIR = Path("generated/src")
DEFAULT_APP_OUT_DIR = Path("gf")

# Optional mapping used by orchestrator naming (e.g., "en" -> "Eng", "cy" -> "Cym")
ISO_MAP_PATH = Path("data/config/iso_to_wiki.json")

logger = logging.getLogger(__name__)


def _load_iso_map() -> Dict[str, Any]:
    """
    Loads data/config/iso_to_wiki.json if present.
    Expected formats:
      - {"en": "WikiEng", ...}
      - {"en": {"wiki": "WikiEng", ...}, ...}
    """
    if not ISO_MAP_PATH.exists():
        return {}
    try:
        data = json.loads(ISO_MAP_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _wiki_suffix_for(code: str, iso_map: Dict[str, Any]) -> str:
    """
    Returns the Wiki module suffix used in filenames, aligned with orchestrator.
    Example: "en" -> "Eng" (so file is WikiEng.gf)
    Fallback: Title-case of input code (e.g., "en" -> "En").
    """
    if not code:
        return "Unknown"

    raw = iso_map.get(code) or iso_map.get(code.lower())
    val_str: str = ""

    if raw:
        if isinstance(raw, dict):
            val_str = str(raw.get("wiki") or raw.get("Wiki") or "")
        else:
            val_str = str(raw)

    if val_str:
        suffix = val_str.replace("Wiki", "").strip()
        if suffix:
            return suffix

    return code.title().strip()


def _parse_langs_arg(langs: Optional[str]) -> Set[str]:
    """
    Accepts comma-separated (and/or space-separated) list and returns lowercased set.
    """
    if not langs:
        return set()
    parts = []
    for token in langs.replace(",", " ").split():
        t = token.strip()
        if t:
            parts.append(t.lower())
    return set(parts)


def _safe_int(x: Any, default: int = -1) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _detect_rgl_suffix(folder_path: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Detect an RGL "suffix" (e.g., Eng, Ger, Swe) from common RGL module names.

    We try multiple prefixes because some folders do not ship Grammar*.gf but do ship
    Syntax*.gf and/or Paradigms*.gf.

    Returns: (suffix, basis_prefix) where basis_prefix is one of:
      "Grammar" | "Syntax" | "Paradigms" | None
    """
    if not folder_path.exists():
        return (None, None)

    # Prefer Grammar if present (bridge generation references Grammar{suffix})
    prefixes = ("Grammar", "Syntax", "Paradigms")

    for prefix in prefixes:
        for f in folder_path.glob(f"{prefix}*.gf"):
            stem = f.stem
            if stem.startswith(prefix) and len(stem) > len(prefix):
                suffix = stem[len(prefix) :]
                # Basic sanity: suffix usually CamelCase-ish, but allow anything non-empty
                if suffix:
                    return (suffix, prefix)

    # Fallback: regex over all .gf in folder
    for f in folder_path.glob("*.gf"):
        m = re.match(r"^(Grammar|Syntax|Paradigms)(.+)$", f.stem)
        if m and m.group(2):
            return (m.group(2), m.group(1))

    return (None, None)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap Tier 1 (RGL-backed) languages.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    parser.add_argument(
        "--langs",
        help="Optional list of language codes to process (comma/space-separated). Example: --langs en,fr,de",
    )
    parser.add_argument(
        "--matrix",
        default=str(DEFAULT_MATRIX_PATH),
        help=f"Path to everything_matrix.json (default: {DEFAULT_MATRIX_PATH})",
    )
    parser.add_argument(
        "--rgl-src",
        default=str(DEFAULT_RGL_SRC_PATH),
        help=f"Path to gf-rgl/src (default: {DEFAULT_RGL_SRC_PATH})",
    )
    parser.add_argument(
        "--bridge-out",
        default=str(DEFAULT_BRIDGE_OUT_DIR),
        help=(
            "Output directory for generated Syntax*.gf bridge files. "
            f"Default: {DEFAULT_BRIDGE_OUT_DIR} (project-owned; avoids editing gf-rgl)."
        ),
    )
    parser.add_argument(
        "--app-out",
        default=str(DEFAULT_APP_OUT_DIR),
        help=(
            "Output directory for generated Wiki*.gf application grammars. "
            f"Default: {DEFAULT_APP_OUT_DIR} (needed for HIGH_ROAD builds)."
        ),
    )
    args = parser.parse_args()

    matrix_path = Path(args.matrix)
    rgl_src_path = Path(args.rgl_src)
    bridge_out_dir = Path(args.bridge_out)
    app_out_dir = Path(args.app_out)

    with tool_logging("bootstrap_tier1") as ctx:
        ctx.log_stage("Initialization")

        if not matrix_path.exists():
            ctx.logger.error(f"Matrix not found at {matrix_path}. Run tools/everything_matrix/build_index.py first.")
            sys.exit(1)

        if not rgl_src_path.exists():
            ctx.logger.error(f"RGL source path not found at {rgl_src_path}.")
            sys.exit(1)

        iso_map = _load_iso_map()

        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
        languages = matrix.get("languages", {}) if isinstance(matrix, dict) else {}
        if not isinstance(languages, dict):
            ctx.logger.error("Invalid matrix format: 'languages' must be an object/dict.")
            sys.exit(1)

        ctx.logger.info(f"Loaded {len(languages)} languages from matrix.")

        target_langs = _parse_langs_arg(args.langs)
        if target_langs:
            ctx.logger.info(f"Filtering for: {sorted(target_langs)}")

        ctx.log_stage("Bootstrapping")

        processed = 0
        skipped = 0
        updated = 0

        if not args.dry_run:
            bridge_out_dir.mkdir(parents=True, exist_ok=True)
            app_out_dir.mkdir(parents=True, exist_ok=True)

        for iso_code, data in languages.items():
            if not isinstance(iso_code, str):
                continue
            iso_key = iso_code.lower()

            if target_langs and iso_key not in target_langs:
                continue

            meta = (data or {}).get("meta", {}) if isinstance(data, dict) else {}
            if _safe_int(meta.get("tier"), default=-1) != 1:
                if target_langs:
                    ctx.logger.warning(f"Skipping {iso_key}: Not Tier 1 (Tier={meta.get('tier')})")
                continue

            folder_name = meta.get("folder")
            if not folder_name:
                ctx.logger.warning(f"Skipping {iso_key}: No folder defined in matrix meta.")
                skipped += 1
                continue

            # Matrix sometimes contains placeholders like "api" when the mapping is stale.
            if str(folder_name).strip().lower() == "api":
                ctx.logger.warning(f"Skipping {iso_key}: Matrix folder=api (stale mapping). Rebuild matrix with --regen-rgl.")
                skipped += 1
                continue

            rgl_folder_path = rgl_src_path / str(folder_name)
            suffix, basis = _detect_rgl_suffix(rgl_folder_path)
            if not suffix:
                ctx.logger.warning(f"Skipping {iso_key}: Could not detect RGL suffix in {rgl_folder_path}")
                skipped += 1
                continue

            # Decide what exists in RGL
            grammar_path = rgl_folder_path / f"Grammar{suffix}.gf"
            syntax_path = rgl_folder_path / f"Syntax{suffix}.gf"
            paradigms_path = rgl_folder_path / f"Paradigms{suffix}.gf"

            # 1) Bridge file: Syntax{suffix}.gf (only needed if RGL does NOT already provide Syntax)
            bridge_name = f"Syntax{suffix}.gf"
            bridge_target = bridge_out_dir / bridge_name

            rgl_syntax_exists = syntax_path.exists()
            target_bridge_exists = bridge_target.exists()

            if not rgl_syntax_exists:
                # If Syntax is missing, we can only generate it if Grammar exists.
                if not grammar_path.exists():
                    ctx.logger.warning(
                        f"Skipping {iso_key}: No Syntax{suffix}.gf and no Grammar{suffix}.gf in {rgl_folder_path} "
                        f"(detected suffix from {basis})."
                    )
                    skipped += 1
                    continue

                if args.force or not target_bridge_exists:
                    bridge_content = (
                        f"instance Syntax{suffix} of Syntax = Grammar{suffix} ** {{ flags coding=utf8 ; }};\n"
                    )
                    if args.dry_run:
                        ctx.logger.info(f"[DRY RUN] Would create bridge: {bridge_target}")
                    else:
                        try:
                            bridge_target.write_text(bridge_content, encoding="utf-8")
                            ctx.logger.info(f"Created/Updated Bridge: {bridge_target}")
                            updated += 1
                        except Exception as e:
                            ctx.logger.error(f"Failed to write bridge {bridge_target}: {e}")
                            skipped += 1
                            continue
            else:
                ctx.logger.debug(f"Syntax already provided by RGL: {syntax_path}")

            # 2) Application grammar: Wiki{WikiSuffix}.gf
            wiki_suffix = _wiki_suffix_for(iso_key, iso_map)
            app_name = f"Wiki{wiki_suffix}.gf"
            app_target = app_out_dir / app_name

            # If Paradigms is missing, still generate but omit it (and warn).
            open_modules = [f"Syntax{suffix}"]
            if paradigms_path.exists():
                open_modules.append(f"Paradigms{suffix}")
            else:
                ctx.logger.warning(f"{iso_key}: Paradigms{suffix}.gf not found; generating app without Paradigms{suffix}.")

            app_content = (
                f"concrete Wiki{wiki_suffix} of AbstractWiki = WikiI with (Syntax = Syntax{suffix}) ** "
                f"open {', '.join(open_modules)} in {{ flags coding=utf8 ; }};\n"
            )

            if args.force or not app_target.exists():
                if args.dry_run:
                    ctx.logger.info(f"[DRY RUN] Would create app grammar: {app_target}")
                else:
                    try:
                        app_target.write_text(app_content, encoding="utf-8")
                        ctx.logger.info(f"Created/Updated App Grammar: {app_target}")
                        updated += 1
                    except Exception as e:
                        ctx.logger.error(f"Failed to write app grammar {app_target}: {e}")
                        skipped += 1
                        continue

            processed += 1

        ctx.finish(
            {
                "processed_tier1": processed,
                "updated_files": updated,
                "skipped_errors": skipped,
                "bridge_out": str(bridge_out_dir),
                "app_out": str(app_out_dir),
                "mode": "DRY RUN" if args.dry_run else "LIVE",
            }
        )


if __name__ == "__main__":
    main()
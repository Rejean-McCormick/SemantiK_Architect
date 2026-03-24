# builder/compiler.py
from __future__ import annotations

import glob
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List

from . import config
from .orchestrator.gf_path import gf_path_args

# --- Configuration ---
LOG_DIR = Path("build_logs")
FAILURE_REPORT = Path("data") / "reports" / "build_failures.json"

# Canonical modules for this repo
ABSTRACT_GF = "SemantikArchitect.gf"
LEGACY_ABSTRACT_GF = "Wiki.gf"
SHARED_CONCRETE_GF = "WikiI.gf"


def get_sandboxed_env() -> Dict[str, str]:
    """
    Create a clean compiler environment.

    We intentionally remove GF_LIB_PATH so the build uses the repo-local RGL
    resolved by the canonical orchestrator path builder.
    """
    env = os.environ.copy()
    env.pop("GF_LIB_PATH", None)
    return env


def _decode_err(proc: subprocess.CalledProcessError) -> str:
    return (proc.stderr or b"").decode("utf-8", errors="replace").strip()


def _run_gf(argv: List[str], *, cwd: str, env: Dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def _is_language_concrete(path: str) -> bool:
    """
    Keep only real language targets.

    Exclude:
      - legacy/ambiguous Wiki.gf
      - shared base concrete WikiI.gf
    """
    name = os.path.basename(path)
    return name.startswith("Wiki") and name.endswith(".gf") and name not in {
        LEGACY_ABSTRACT_GF,
        SHARED_CONCRETE_GF,
    }


def _discover_concretes() -> List[str]:
    all_files = glob.glob(os.path.join(config.GF_DIR, "Wiki*.gf"))
    return sorted(os.path.basename(f) for f in all_files if _is_language_concrete(f))


def run() -> bool:
    print("🚀 Starting SemantikArchitect PGF Compilation (Sandboxed)...")

    gf_dir = Path(config.GF_DIR)
    if not gf_dir.exists():
        print(f"❌ Error: Directory '{config.GF_DIR}' not found.")
        return False

    abstract_path = gf_dir / ABSTRACT_GF
    if not abstract_path.exists():
        print(f"❌ Error: Abstract grammar '{abstract_path}' not found.")
        return False

    # Canonical GF -path builder:
    #   - gf-rgl/src + api
    #   - all first-level RGL language dirs
    #   - gf/contrib/*
    #   - gf/
    #   - generated/src candidates
    #   - repo root
    path_arg = gf_path_args()
    if not path_arg:
        print("❌ Error: empty GF path.")
        return False

    sandbox_env = get_sandboxed_env()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    FAILURE_REPORT.parent.mkdir(parents=True, exist_ok=True)

    concrete_files = _discover_concretes()
    successful_files: List[str] = []
    failed_languages: Dict[str, Dict[str, str]] = {}

    print(f"--- Phase 1: Individual Verification ({len(concrete_files)} languages) ---")

    # 1. Compile abstract first
    try:
        _run_gf(
            ["gf", "-make", "-path", path_arg, ABSTRACT_GF],
            cwd=config.GF_DIR,
            env=sandbox_env,
        )
        print(f"✔ {ABSTRACT_GF} compiled successfully.")
    except subprocess.CalledProcessError as e:
        err_msg = _decode_err(e)
        print(f"❌ CRITICAL: {ABSTRACT_GF} failed.")
        print(err_msg)
        return False

    # 2. Optionally sanity-check the shared base concrete
    shared_path = gf_dir / SHARED_CONCRETE_GF
    if shared_path.exists():
        try:
            _run_gf(
                ["gf", "-make", "-path", path_arg, SHARED_CONCRETE_GF],
                cwd=config.GF_DIR,
                env=sandbox_env,
            )
            print(f"✔ {SHARED_CONCRETE_GF} compiled successfully.")
        except subprocess.CalledProcessError as e:
            err_msg = _decode_err(e)
            print(f"❌ CRITICAL: {SHARED_CONCRETE_GF} failed.")
            print(err_msg)
            failed_languages["I"] = {
                "file": SHARED_CONCRETE_GF,
                "reason": err_msg,
            }
            with (LOG_DIR / "error_WikiI.txt").open("w", encoding="utf-8") as log:
                log.write(err_msg)

            with FAILURE_REPORT.open("w", encoding="utf-8") as f:
                json.dump(failed_languages, f, indent=2, ensure_ascii=False)

            return False

    # 3. Compile concrete languages one by one
    for filename in concrete_files:
        lang_code = filename.removeprefix("Wiki").removesuffix(".gf")

        try:
            _run_gf(
                ["gf", "-make", "-path", path_arg, filename],
                cwd=config.GF_DIR,
                env=sandbox_env,
            )
            print(f"✔ {lang_code:<10} [OK]")
            successful_files.append(filename)

        except subprocess.CalledProcessError as e:
            err_msg = _decode_err(e)
            summary = "\n   ".join(err_msg.splitlines()[-2:]) if err_msg else "unknown GF error"
            print(f"❌ {lang_code:<10} [FAILED] -> {summary}")

            failed_languages[lang_code] = {
                "file": filename,
                "reason": err_msg,
            }

            with (LOG_DIR / f"error_{lang_code}.txt").open("w", encoding="utf-8") as log:
                log.write(err_msg)

    # 4. Failure report for healer / diagnostics
    with FAILURE_REPORT.open("w", encoding="utf-8") as f:
        json.dump(failed_languages, f, indent=2, ensure_ascii=False)
    print(f"📝 Failure report saved to {FAILURE_REPORT}")

    print("-" * 60)
    print(f"Summary: {len(successful_files)} Passed, {len(failed_languages)} Failed.")

    if not successful_files:
        print("\n❌ No language concretes compiled successfully. Exiting.")
        return False

    # 5. Final link
    print("\n--- Phase 2: Linking Final PGF ---")
    final_cmd = ["gf", "-make", "-path", path_arg, ABSTRACT_GF, *successful_files]

    try:
        _run_gf(final_cmd, cwd=config.GF_DIR, env=sandbox_env)
        print(f"\n✅ SUCCESS: {gf_dir / 'SemantikArchitect.pgf'} created.")
        return True
    except subprocess.CalledProcessError as e:
        print("\n❌ FAILURE during final linking.")
        print(_decode_err(e))
        return False
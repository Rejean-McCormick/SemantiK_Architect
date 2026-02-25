#!/usr/bin/env python3
"""
=============================================================================
🚀 ABSTRACT WIKI ARCHITECT - UNIFIED COMMANDER (v2.5)
=============================================================================
Single entry point for developer operations.

Usage:
    python manage.py start       # Check -> Align -> Build -> Launch
    python manage.py build       # Compile grammars (supports --clean, --parallel, --langs, --strategy, --align)
    python manage.py align       # Align GF/RGL + generate Tier-1 bridge/app grammars (Syntax*.gf + Wiki*.gf)
    python manage.py clean       # Nuke generated artifacts (Zombie killer)
    python manage.py doctor      # System health check
    python manage.py generate    # AI/Factory generation for missing languages
"""

from __future__ import annotations

import os
import sys
import subprocess
import argparse
import shutil
import platform
from pathlib import Path
from typing import Optional, Union, Literal

# --- CONFIGURATION ---
ROOT_DIR = Path(__file__).parent.resolve()

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

# Robust venv detection (supports Windows + WSL/Linux)
VENV_DIR = ROOT_DIR / "venv"
VENV_BIN = VENV_DIR / ("Scripts" if IS_WINDOWS else "bin")
VENV_PYTHON = VENV_BIN / ("python.exe" if IS_WINDOWS else "python")


def _python_exe() -> str:
    """
    Prefer venv python if it exists, otherwise fall back to the currently running interpreter.
    This makes `python manage.py ...` work even if venv is not activated.
    """
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return sys.executable


PYTHON = _python_exe()

INDEXER = ROOT_DIR / "tools" / "everything_matrix" / "build_index.py"

# Alignment entrypoints
ALIGN_SCRIPT = ROOT_DIR / "scripts" / "align_system.py"
ALIGN_MODULE = ROOT_DIR / "builder" / "alignment.py"  # fallback if script isn't present

# Generated dir reconciliation
CANON_GENERATED_ROOT = ROOT_DIR / "generated"
LEGACY_GENERATED_ROOT = ROOT_DIR / "gf" / "generated"

CANON_GENERATED_DIR = CANON_GENERATED_ROOT / "src"          # canonical
LEGACY_GENERATED_DIR = LEGACY_GENERATED_ROOT / "src"        # legacy

GENERATED_DIR = CANON_GENERATED_DIR

CONTRIB_DIR = ROOT_DIR / "gf" / "contrib"
BUILD_LOGS = ROOT_DIR / "gf" / "build_logs"

# Alignment defaults (ref-first; overridable)
RGL_REF_ENV = "ABSTRACTWIKI_RGL_REF"
RGL_COMMIT_ENV = "ABSTRACTWIKI_RGL_COMMIT"
DEFAULT_RGL_REF = os.environ.get(RGL_REF_ENV) or os.environ.get(RGL_COMMIT_ENV) or "GF-3.10"


# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def log(msg: str, color: str = Colors.ENDC) -> None:
    print(f"{color}{msg}{Colors.ENDC}")


def is_wsl() -> bool:
    """Detect if running under Windows Subsystem for Linux."""
    if platform.system() == "Linux":
        try:
            with open("/proc/version", "r", encoding="utf-8") as f:
                return "microsoft" in f.read().lower()
        except Exception:
            return False
    return False


def _path_with_venv() -> str:
    # os.pathsep is ':' on Linux/WSL, ';' on Windows
    return f"{str(VENV_BIN)}{os.pathsep}{os.environ.get('PATH', '')}"


def run_cmd(
    cmd: Union[str, list[str]],
    cwd: Path = ROOT_DIR,
    check: bool = True,
    capture: bool = False,
):
    """
    Runs a command safely.
    - Accepts string (shell=True) or argv list (shell=False).
    - Ensures venv bin/Scripts is at the front of PATH.
    """
    env = os.environ.copy()
    env["PATH"] = _path_with_venv()

    use_shell = isinstance(cmd, str)

    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=use_shell,
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        env=env,
    )
    return result


def _safe_symlink(link_path: Path, target_path: Path) -> bool:
    """
    Try to create link_path -> target_path symlink.
    Returns True if created (or already correct), False otherwise.
    """
    try:
        if link_path.is_symlink():
            try:
                if link_path.resolve() != target_path.resolve():
                    link_path.unlink()
                else:
                    return True
            except Exception:
                link_path.unlink()

        if link_path.exists():
            return False

        link_path.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(str(target_path), str(link_path), target_is_directory=True)
        return True
    except Exception:
        return False


def _sync_generated_src(src_dir: Path, dst_dir: Path) -> int:
    """
    One-way sync for generated artifacts.
    Copies a small set of relevant file types, only if missing or newer.
    Returns number of files copied.
    """
    if not src_dir.exists():
        return 0

    copied = 0
    dst_dir.mkdir(parents=True, exist_ok=True)

    allow_suffix = {".gf", ".gfo", ".pgf", ".json", ".log"}

    for p in src_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix not in allow_suffix:
            continue

        rel = p.relative_to(src_dir)
        out = dst_dir / rel
        out.parent.mkdir(parents=True, exist_ok=True)

        try:
            if (not out.exists()) or (p.stat().st_mtime > out.stat().st_mtime + 1e-6):
                shutil.copy2(p, out)
                copied += 1
        except FileNotFoundError:
            continue

    return copied


def reconcile_generated_dirs(verbose: bool = False) -> None:
    """
    Ensure:
      - generated/src exists (canonical)
      - gf/generated/src exists (legacy)
      - best effort to unify via symlink
      - fallback: bidirectional sync to reduce shadowing/staleness
    """
    LEGACY_GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    CANON_GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    linked = _safe_symlink(CANON_GENERATED_ROOT, LEGACY_GENERATED_ROOT)

    copied_l2c = 0
    copied_c2l = 0

    if not linked:
        copied_l2c = _sync_generated_src(LEGACY_GENERATED_DIR, CANON_GENERATED_DIR)
        copied_c2l = _sync_generated_src(CANON_GENERATED_DIR, LEGACY_GENERATED_DIR)

        if verbose and (copied_l2c or copied_c2l):
            log(f"    🔁 Synced {copied_l2c} files: gf/generated/src -> generated/src", Colors.WARNING)
            log(f"    🔁 Synced {copied_c2l} files: generated/src -> gf/generated/src", Colors.WARNING)

    if verbose:
        try:
            canon = CANON_GENERATED_DIR.resolve()
            legacy = LEGACY_GENERATED_DIR.resolve()
            if canon == legacy:
                log(
                    f"    ✅ Generated dirs unified: {CANON_GENERATED_DIR.relative_to(ROOT_DIR)} == "
                    f"{LEGACY_GENERATED_DIR.relative_to(ROOT_DIR)}",
                    Colors.GREEN,
                )
            else:
                log(f"    ⚠️  Generated dirs distinct:", Colors.WARNING)
                log(f"       - {CANON_GENERATED_DIR} -> {canon}", Colors.WARNING)
                log(f"       - {LEGACY_GENERATED_DIR} -> {legacy}", Colors.WARNING)

                broken = list(LEGACY_GENERATED_DIR.glob("**/*.RGL_BROKEN"))
                if broken:
                    log(
                        f"       ⚠️  Found {len(broken)} '*.RGL_BROKEN' under gf/generated/src (may shadow builds).",
                        Colors.WARNING,
                    )
        except Exception:
            pass


def _docker_hint(stderr: str) -> Optional[str]:
    s = (stderr or "").lower()
    if "permission denied" in s and ("docker.sock" in s or "/var/run/docker.sock" in s):
        return "Hint: permission denied on Docker socket → `sudo usermod -aG docker $USER` then restart shell/WSL."
    if "cannot connect to the docker daemon" in s or "is the docker daemon running" in s:
        if is_wsl():
            return "Hint: Docker daemon unreachable from WSL → enable Docker Desktop > Settings > Resources > WSL Integration for this distro."
        return "Hint: Docker daemon unreachable → ensure the docker service/daemon is running."
    if "context" in s and ("not found" in s or "no such file" in s or "cannot" in s):
        return "Hint: Docker context may be broken → try `docker context ls` and `docker context use default`."
    return None


def _try_docker_cmd(docker_cmd: str) -> Optional[subprocess.CompletedProcess]:
    try:
        return run_cmd([docker_cmd, "info"], capture=True, check=True)
    except Exception:
        return None


def _print_tail(label: str, text: str, n: int = 40) -> None:
    t = (text or "").strip()
    if not t:
        return
    log(f"       {label} (last {n} lines):", Colors.WARNING)
    for line in t.splitlines()[-n:]:
        log(f"         {line}", Colors.WARNING)


# --- Alignment capability probing (prevents arg mismatch like --tier / langs parsing) ---

def _get_align_entry() -> list[str]:
    if ALIGN_SCRIPT.exists():
        return [PYTHON, str(ALIGN_SCRIPT)]
    if ALIGN_MODULE.exists():
        return [PYTHON, str(ALIGN_MODULE)]
    return []


def _align_help(entry: list[str]) -> str:
    try:
        p = run_cmd(entry + ["--help"], cwd=ROOT_DIR, capture=True, check=False)
        return (p.stdout or "") + "\n" + (p.stderr or "")
    except Exception:
        return ""


def _help_supports(help_text: str, flag: str) -> bool:
    return flag in (help_text or "")


def _langs_mode(help_text: str) -> Literal["multi", "single"]:
    """
    Best-effort: detect whether align tool expects:
      --langs en fr        (multi via nargs)
    or:
      --langs en,fr        (single string)
    """
    for line in (help_text or "").splitlines():
        if "--langs" not in line:
            continue
        if "[" in line and "..." in line:
            return "multi"
        return "single"
    return "multi"


# --- COMMANDS ---

def check_env() -> None:
    """Pre-flight checks for Docker, Redis, and GF."""
    log("\n[1/5] 🏥 Health Check", Colors.HEADER)

    docker_cmd = "docker"

    # 1) Docker
    try:
        run_cmd([docker_cmd, "info"], capture=True, check=True)
        log("    ✅ Docker is running.", Colors.GREEN)
    except subprocess.CalledProcessError as e:
        log("    ❌ Docker check failed (`docker info` returned non-zero).", Colors.FAIL)

        docker_path = shutil.which("docker", path=_path_with_venv())
        log(f"       docker path: {docker_path}", Colors.WARNING)

        stderr = (e.stderr or "")
        stdout = (e.stdout or "")

        _print_tail("stderr", stderr, n=20)
        _print_tail("stdout", stdout, n=20)

        hint = _docker_hint(stderr)
        if hint:
            log(f"       {hint}", Colors.WARNING)

        if is_wsl():
            alt = _try_docker_cmd("docker.exe")
            if alt is not None:
                docker_cmd = "docker.exe"
                log("    ✅ Docker is reachable via docker.exe (WSL → Windows Docker Desktop).", Colors.GREEN)

        if docker_cmd != "docker.exe":
            sys.exit(1)

    # 2) Redis (use the same docker_cmd we validated above)
    try:
        res = run_cmd([docker_cmd, "ps", "-q", "-f", "name=aw_redis"], capture=True, check=False)
        if (res.stdout or "").strip():
            log("    ✅ Redis container is active.", Colors.GREEN)
        else:
            log("    ⚠️  Redis container not found/running. Starting...", Colors.WARNING)
            run_cmd([docker_cmd, "run", "-d", "-p", "6379:6379", "--name", "aw_redis", "redis:alpine"], check=True)
            log("    ✅ Redis started.", Colors.GREEN)
    except Exception as e:
        log(f"    ❌ Redis check failed: {e}", Colors.FAIL)

    # 3) GF Binary (prefer orchestrator-resolved GF_BIN if available)
    gf_exe = "gf"
    try:
        from builder.orchestrator import config as orch_config  # type: ignore
        gf_exe = orch_config.GF_BIN  # type: ignore[attr-defined]
    except Exception:
        gf_exe = "gf"

    try:
        run_cmd([gf_exe, "--version"], capture=True, check=True)
        log("    ✅ GF compiler found.", Colors.GREEN)
    except Exception:
        log("    ❌ 'gf' binary not found/working.", Colors.FAIL)
        sys.exit(1)


def clean_artifacts() -> None:
    """Cleanup of generated/build artifacts (handles both generated/src and gf/generated/src)."""
    reconcile_generated_dirs(verbose=False)

    log("\n🧹 Cleaning Artifacts...", Colors.WARNING)

    targets: list[Path] = []

    for base in (CANON_GENERATED_DIR, LEGACY_GENERATED_DIR):
        targets.extend([base / "bul", base / "pol"])

    targets.extend([
        BUILD_LOGS,
        ROOT_DIR / "gf" / "AbstractWiki.gfo",
        ROOT_DIR / "gf" / "AbstractWiki.pgf",
    ])

    for target in targets:
        if target.exists():
            try:
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
                log(f"    🗑️  Deleted: {target.relative_to(ROOT_DIR)}")
            except Exception as e:
                log(f"    ⚠️  Failed to delete {target}: {e}", Colors.WARNING)

    log("    ✅ Clean complete.", Colors.GREEN)


def align_system(
    langs: Optional[list[str]] = None,
    tier: int = 1,
    force: bool = False,
    no_time_travel: bool = False,
    ref: Optional[str] = None,
    commit: Optional[str] = None,
) -> None:
    """
    Aligns GF/RGL and generates Tier-1 bridge/app grammars.

    Key: this wrapper probes align_system.py --help so we DON'T pass flags it doesn't support.
    """
    reconcile_generated_dirs(verbose=True)
    log("\n🧭 Aligning GF/RGL System", Colors.HEADER)

    entry = _get_align_entry()
    if not entry:
        log("    ❌ Alignment tool not found.", Colors.FAIL)
        log("       Expected one of:", Colors.FAIL)
        log(f"         - {ALIGN_SCRIPT.relative_to(ROOT_DIR)}", Colors.FAIL)
        log(f"         - {ALIGN_MODULE.relative_to(ROOT_DIR)}", Colors.FAIL)
        sys.exit(1)

    help_text = _align_help(entry)

    chosen_ref = ref or commit or DEFAULT_RGL_REF

    cmd: list[str] = entry[:]

    if chosen_ref:
        if _help_supports(help_text, "--ref"):
            cmd += ["--ref", chosen_ref]
        elif _help_supports(help_text, "--commit"):
            cmd += ["--commit", chosen_ref]

    if langs and _help_supports(help_text, "--langs"):
        mode = _langs_mode(help_text)
        if mode == "multi":
            cmd += ["--langs", *langs]
        else:
            cmd += ["--langs", ",".join(langs)]

    if _help_supports(help_text, "--tier"):
        cmd += ["--tier", str(int(tier))]

    if force and _help_supports(help_text, "--force"):
        cmd += ["--force"]

    if no_time_travel and _help_supports(help_text, "--no-time-travel"):
        cmd += ["--no-time-travel"]

    proc = run_cmd(cmd, cwd=ROOT_DIR, capture=True, check=False)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)

    if proc.returncode != 0:
        log("    ❌ Alignment failed.", Colors.FAIL)
        _print_tail("stderr", proc.stderr or "", n=60)
        sys.exit(proc.returncode)

    log("    ✅ Alignment complete.", Colors.GREEN)


def build_system(
    clean: bool = False,
    parallel: Optional[int] = None,
    langs: Optional[list[str]] = None,
    strategy: str = "AUTO",
    align: bool = False,
    rgl_ref: Optional[str] = None,
) -> None:
    """The Build Pipeline."""
    reconcile_generated_dirs(verbose=True)

    if clean:
        clean_artifacts()

    if align:
        align_system(langs=langs, tier=1, force=False, no_time_travel=False, ref=rgl_ref)

    log("\n[2/5] 🧠 Indexing Knowledge Layer", Colors.HEADER)
    try:
        run_cmd([PYTHON, str(INDEXER)], cwd=ROOT_DIR, check=True)
    except subprocess.CalledProcessError as e:
        log("❌ Indexing Failed.", Colors.FAIL)
        _print_tail("stderr", e.stderr or "", n=60)
        sys.exit(e.returncode)

    log("\n[3/5] 🏗️  Compiling Grammar Layer", Colors.HEADER)

    try:
        from builder.orchestrator import build_pgf  # type: ignore
    except Exception:
        build_pgf = None  # type: ignore[assignment]

    if build_pgf is None:
        log("❌ Orchestrator import failed: builder.orchestrator.build_pgf not available.", Colors.FAIL)
        sys.exit(1)

    try:
        pgf_path = build_pgf(
            strategy=strategy,
            langs=langs,
            clean=False,          # manage.py already cleaned if requested
            verbose=False,
            max_workers=parallel,
            no_preflight=False,
            regen_safe=False,
        )
        log(f"    ✅ PGF built: {pgf_path}", Colors.GREEN)
    except SystemExit as e:
        code = int(getattr(e, "code", 1) or 1)
        sys.exit(code)
    except Exception as e:
        log(f"❌ Compilation Failed: {e}", Colors.FAIL)
        sys.exit(1)


def kill_stale_processes() -> None:
    """Kills old uvicorn/arq processes to free ports."""
    log("\n[4/5] 🔫 Process Cleanup", Colors.HEADER)

    if IS_WINDOWS and not is_wsl():
        log("    ⚠️  Process cleanup skipped on native Windows.", Colors.WARNING)
        return

    subprocess.run("pkill -f uvicorn || true", shell=True)
    subprocess.run("pkill -f arq || true", shell=True)
    log("    ✅ Port 8000 freed.", Colors.GREEN)


def start_services() -> None:
    """Launches API and Worker."""
    log("\n[5/5] 🚀 Launching Services", Colors.HEADER)

    api_cmd = f"cd {ROOT_DIR} && {PYTHON} -m uvicorn app.adapters.api.main:create_app --factory --host 0.0.0.0 --port 8000 --reload"
    worker_cmd = f"cd {ROOT_DIR} && {PYTHON} -m arq app.workers.worker.WorkerSettings --watch app"

    if IS_WINDOWS and not is_wsl():
        log("    🪟 Native Windows Detected (no auto-spawn).", Colors.BLUE)
        _print_manual_commands(api_cmd, worker_cmd)
        return

    if is_wsl():
        try:
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "wsl", "bash", "-c",
                 f"{api_cmd}; echo '❌ API CRASHED'; exec bash"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            log("    👉 API Window Spawned.", Colors.CYAN)

            subprocess.Popen(
                ["cmd.exe", "/c", "start", "wsl", "bash", "-c",
                 f"{worker_cmd}; echo '❌ WORKER CRASHED'; exec bash"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            log("    👉 Worker Window Spawned.", Colors.CYAN)

            log("\n✅ SYSTEM ONLINE!", Colors.GREEN)
            log("    🗺️  Docs: http://localhost:8000/docs", Colors.BOLD)

        except FileNotFoundError:
            log("    ⚠️  'cmd.exe' not found despite WSL check.", Colors.WARNING)
            _print_manual_commands(api_cmd, worker_cmd)
    else:
        log("    🐧 Linux Detected (no GUI spawning)", Colors.BLUE)
        _print_manual_commands(api_cmd, worker_cmd)


def _print_manual_commands(api_cmd: str, worker_cmd: str) -> None:
    log("\n    Please run these in separate terminals:", Colors.WARNING)
    log(f"    [Terminal 1] {api_cmd}", Colors.CYAN)
    log(f"    [Terminal 2] {worker_cmd}", Colors.CYAN)


def generate_missing(lang_code: Optional[str] = None) -> None:
    """Generate missing grammars via AI/Factory."""
    reconcile_generated_dirs(verbose=True)
    log("\n🎨 Generating Missing Grammars", Colors.HEADER)

    cmd = [PYTHON, "-m", "ai_services.architect"]
    if lang_code:
        cmd += ["--lang", lang_code]
    else:
        cmd += ["--missing"]

    try:
        run_cmd(cmd, cwd=ROOT_DIR, check=True)

        copied_l2c = _sync_generated_src(LEGACY_GENERATED_DIR, CANON_GENERATED_DIR)
        copied_c2l = _sync_generated_src(CANON_GENERATED_DIR, LEGACY_GENERATED_DIR)
        if copied_l2c or copied_c2l:
            log(f"    🔁 Synced {copied_l2c} legacy->canon and {copied_c2l} canon->legacy files", Colors.WARNING)

        log("    ✅ Generation complete.", Colors.GREEN)
    except subprocess.CalledProcessError as e:
        log("    ❌ Generation failed.", Colors.FAIL)
        _print_tail("stderr", e.stderr or "", n=80)
        sys.exit(e.returncode)


def doctor() -> None:
    """System Diagnostic Tool."""
    reconcile_generated_dirs(verbose=True)

    log("\n🩺 Running Doctor...", Colors.HEADER)
    log(f"    📂 Root: {ROOT_DIR}")

    if not (ROOT_DIR / "gf-rgl").exists():
        log("    ❌ gf-rgl/ folder missing! Run setup.", Colors.FAIL)
    else:
        log("    ✅ gf-rgl/ found.", Colors.GREEN)
        try:
            p = run_cmd(["git", "-C", str(ROOT_DIR / "gf-rgl"), "rev-parse", "--short", "HEAD"], capture=True, check=False)
            head = (p.stdout or "").strip()
            if head:
                log(f"    🔎 gf-rgl HEAD: {head}", Colors.CYAN)
        except Exception:
            pass

    config_file = ROOT_DIR / "app" / "shared" / "config.py"
    if not config_file.exists():
        log("    ❌ app/shared/config.py missing.", Colors.FAIL)
    else:
        log("    ✅ config.py found.", Colors.GREEN)

    stray_wiki = []
    for base in (CANON_GENERATED_DIR, LEGACY_GENERATED_DIR):
        if base.exists():
            stray_wiki.extend(base.glob("**/Wiki*.gf"))
    if stray_wiki:
        log(f"    ⚠️  Found {len(stray_wiki)} Wiki*.gf under generated roots (should be under gf/).", Colors.WARNING)

    if ALIGN_SCRIPT.exists() or ALIGN_MODULE.exists():
        log("    ✅ Alignment tool present.", Colors.GREEN)
    else:
        log("    ⚠️  Alignment tool missing (scripts/align_system.py or builder/alignment.py).", Colors.WARNING)

    log("    ✅ Doctor complete.", Colors.GREEN)


# --- MAIN ---

def main() -> None:
    parser = argparse.ArgumentParser(description="Abstract Wiki Architect Commander")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("start", help="Full Launch: Check, Align, Build, Run")

    build_parser = subparsers.add_parser("build", help="Compile grammars")
    build_parser.add_argument("--clean", action="store_true", help="Clean artifacts first")
    build_parser.add_argument("--parallel", type=int, default=None, help="Number of CPU cores / max workers")
    build_parser.add_argument("--langs", nargs="*", default=None, help="Language codes to build (e.g., en fr deu)")
    build_parser.add_argument(
        "--strategy",
        choices=["AUTO", "HIGH_ROAD", "SAFE_MODE"],
        default="AUTO",
        help="AUTO uses everything_matrix.json verdicts; otherwise force a strategy for selected languages.",
    )
    build_parser.add_argument(
        "--align",
        action="store_true",
        help="Run system alignment before building (pins gf-rgl + generates Tier-1 bridge/app grammars).",
    )
    build_parser.add_argument(
        "--rgl-ref",
        type=str,
        default=None,
        help=f"RGL pin ref/tag/commit (defaults to ${RGL_REF_ENV} or '{DEFAULT_RGL_REF}').",
    )

    subparsers.add_parser("clean", help="Remove generated artifacts")

    align_parser = subparsers.add_parser("align", help="Align GF/RGL and generate Tier-1 bridge/app grammars")
    align_parser.add_argument("--langs", nargs="*", default=None, help="Limit alignment/bootstrap to these languages")
    align_parser.add_argument("--tier", type=int, default=1, help="Tier to bootstrap (default: 1)")
    align_parser.add_argument("--force", action="store_true", help="Force overwrite of generated bridge/app grammars")
    align_parser.add_argument("--no-time-travel", action="store_true", help="Skip gf-rgl pin/reset step")
    align_parser.add_argument(
        "--ref",
        type=str,
        default=None,
        help=f"RGL ref/tag/commit (preferred; defaults to ${RGL_REF_ENV} or '{DEFAULT_RGL_REF}').",
    )
    align_parser.add_argument(
        "--commit",
        type=str,
        default=None,
        help=f"Backward-compat alias for --ref (or uses ${RGL_COMMIT_ENV}).",
    )

    gen_parser = subparsers.add_parser("generate", help="Generate missing grammars via AI/Factory")
    gen_parser.add_argument("--lang", type=str, default=None, help="Specific ISO code")
    gen_parser.add_argument("--missing", action="store_true", help="Generate all missing (default if --lang omitted)")

    subparsers.add_parser("doctor", help="Run diagnostics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "start":
        check_env()
        kill_stale_processes()
        build_system(clean=False, parallel=None, langs=None, strategy="AUTO", align=True, rgl_ref=None)
        start_services()

    elif args.command == "build":
        build_system(
            clean=bool(args.clean),
            parallel=args.parallel,
            langs=args.langs,
            strategy=args.strategy,
            align=bool(args.align),
            rgl_ref=args.rgl_ref,
        )

    elif args.command == "align":
        align_system(
            langs=args.langs,
            tier=int(args.tier),
            force=bool(args.force),
            no_time_travel=bool(args.no_time_travel),
            ref=args.ref,
            commit=args.commit,
        )

    elif args.command == "clean":
        clean_artifacts()

    elif args.command == "generate":
        generate_missing(args.lang if args.lang else None)

    elif args.command == "doctor":
        doctor()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n🛑 Aborted by user.", Colors.WARNING)
from __future__ import annotations

import os
import subprocess
import time
from typing import Dict, Sequence, Tuple

from .config import REPO_ROOT


def run_process_extended(
    cmd: Sequence[str],
    timeout_sec: int,
    env_updates: Dict[str, str],
) -> Tuple[int, str, str, int]:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env.update(env_updates)

    started = time.time()
    try:
        proc = subprocess.run(
            list(cmd),
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
            check=False,
        )
        duration_ms = int((time.time() - started) * 1000)
        return proc.returncode, proc.stdout or "", proc.stderr or "", duration_ms

    except subprocess.TimeoutExpired as e:
        duration_ms = int((time.time() - started) * 1000)
        stdout = (e.stdout or "") if isinstance(e.stdout, str) else ""
        stderr = (e.stderr or "") if isinstance(e.stderr, str) else ""
        stderr += f"\nProcess timed out (limit: {timeout_sec}s)."
        return 124, stdout, stderr, duration_ms

    except Exception as e:
        duration_ms = int((time.time() - started) * 1000)
        return 127, "", f"CRITICAL RUNNER ERROR: {str(e)}\n", duration_ms

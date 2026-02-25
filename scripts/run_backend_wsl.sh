#!/usr/bin/env bash
# Backend launcher for WSL:
# - Always runs from repo root
# - Logs to ./logs/backend_YYYYMMDD_HHMMSS.log
# - Activates venv (prefers ./venv, then ./.venv)
# - Runs: python3 manage.py start
# - Never closes the window: drops into bash at the end
#
# Optional env vars:
#   AW_TRACE=1   -> bash xtrace (very verbose)

set +e
set -o pipefail

if [[ "${AW_TRACE:-0}" == "1" ]]; then
  set -x
fi

# Resolve repo root based on this script location: repo/scripts/run_backend_wsl.sh
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_DIR" || exit 1

TS="$(date +%Y%m%d_%H%M%S)"

mkdir -p logs
LOGFILE="logs/backend_${TS}.log"

echo "Logging to: ${REPO_DIR}/${LOGFILE}"
exec > >(tee -a "$LOGFILE") 2>&1

echo "PWD=$(pwd)"
echo "WSL=$(uname -a)"

# Keep the wrapper alive even if something sends SIGTERM to the session
# (so the window doesn’t close and you can read the error).
trap ':' TERM

# Activate venv
VENV=""
if [[ -f "venv/bin/activate" ]]; then
  VENV="venv"
elif [[ -f ".venv/bin/activate" ]]; then
  VENV=".venv"
fi

if [[ -n "$VENV" ]]; then
  # shellcheck disable=SC1090
  source "${VENV}/bin/activate"
  echo "VENV_OK=${VIRTUAL_ENV}"
else
  echo "VENV_MISSING: expected ./venv/ or ./.venv/ under: $(pwd)"
  echo "Create one of:"
  echo "  python3 -m venv venv"
  echo "  python3 -m venv .venv"
fi

echo -n "PY="
command -v python3 2>/dev/null || true
python3 --version 2>/dev/null || true

echo ""
echo "Preflight (docker.exe from WSL):"
docker.exe info >/dev/null 2>&1 && echo "DOCKER_OK" || echo "DOCKER_FAIL"

echo ""
echo "Running: python3 manage.py start"
PYTHONUNBUFFERED=1 python3 -u manage.py start
STATUS=$?
echo "manage.py exit code: ${STATUS}"

echo ""
echo "Listener check (8000):"
ss -ltnp 2>/dev/null | grep ':8000 ' || echo "NO_LISTENER_8000"

echo ""
echo "Notes:"
echo "- If manage.py exits during compilation, the API/worker will not start, so 8000 stays closed."
echo "- If you saw 'WSL exited with code 15', something sent SIGTERM to the session; this wrapper ignores TERM so the window stays open."

echo ""
echo "Dropping into an interactive shell."
exec bash -li
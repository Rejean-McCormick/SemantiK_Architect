#!/usr/bin/env bash
set +e
set -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

TS="$(date +%Y%m%d_%H%M%S)"
mkdir -p logs

pick_venv() {
  if [ -f venv/bin/activate ]; then echo "venv"; return; fi
  if [ -f .venv/bin/activate ]; then echo ".venv"; return; fi
  echo ""
}

LOGFILE="logs/api_${TS}.log"
echo "Logging to: ${ROOT}/${LOGFILE}"
exec > >(tee -a "${LOGFILE}") 2>&1

echo "PWD=$(pwd)"
echo "WSL=$(uname -a)"

VENV="$(pick_venv)"
if [ -n "$VENV" ]; then
  # shellcheck disable=SC1090
  source "${VENV}/bin/activate"
  echo "VENV_OK=${VIRTUAL_ENV}"
else
  echo "VENV_MISSING: expected venv/ or .venv/ in $(pwd)"
fi

echo "PY=$(command -v python3 2>/dev/null || true)"
python3 --version 2>/dev/null || true

echo ""
echo "PGF check:"
ls -l gf/AbstractWiki.pgf 2>/dev/null || echo "MISSING_PGF"

PORT="${1:-8000}"

echo ""
echo "Starting API:"
echo "  python3 -m uvicorn app.adapters.api.main:create_app --factory --host 0.0.0.0 --port ${PORT} --reload"
python3 -m uvicorn app.adapters.api.main:create_app --factory --host 0.0.0.0 --port "${PORT}" --reload
STATUS=$?
echo "uvicorn exit code: ${STATUS}"

echo ""
echo "Dropping into an interactive shell."
exec bash -li

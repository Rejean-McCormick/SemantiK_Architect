#!/usr/bin/env bash
set +e
set -o pipefail

TS=$(date +%Y%m%d_%H%M%S)
mkdir -p logs
LOGFILE="logs/backend_${TS}.log"

echo "Logging to: $(pwd)/$LOGFILE"
exec > >(tee -a "$LOGFILE") 2>&1

echo "PWD=$(pwd)"
echo "WSL=$(uname -a)"

# Prevent wrapper from dying if something sends SIGTERM to the session
trap ':' TERM

VENV=""
if [ -f venv/bin/activate ]; then
  VENV="venv"
elif [ -f .venv/bin/activate ]; then
  VENV=".venv"
fi

if [ -n "$VENV" ]; then
  # shellcheck disable=SC1090
  source "$VENV/bin/activate"
  echo "VENV_OK=$VIRTUAL_ENV"
else
  echo "VENV_MISSING: expected venv/ or .venv/ in $(pwd)"
  echo "Create one of:"
  echo "  python3 -m venv venv"
  echo "  python3 -m venv .venv"
fi

echo -n "PY="
command -v python3 2>/dev/null || true
python3 --version 2>/dev/null || true

echo ""
echo "Post-reboot quick check (Windows Docker via docker.exe):"
docker.exe info >/dev/null 2>&1 && echo "DOCKER_OK" || echo "DOCKER_FAIL"

echo ""
echo "Running: python3 manage.py start"

# Run in isolated session if available (reduces chance that a TERM kills the wrapper)
if command -v setsid >/dev/null 2>&1; then
  PYTHONUNBUFFERED=1 setsid -w python3 -u manage.py start
else
  PYTHONUNBUFFERED=1 python3 -u manage.py start
fi

STATUS=$?
echo "manage.py exit code: $STATUS"

echo ""
echo "Listener check (8000):"
ss -ltnp 2>/dev/null | grep ':8000 ' || echo "NO_LISTENER_8000"

echo ""
echo "Dropping into an interactive shell."
exec bash -li
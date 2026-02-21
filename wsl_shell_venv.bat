@echo off
setlocal EnableExtensions
TITLE Abstract Wiki Architect (WSL + venv)

REM Windows path of the repo (edit only this)
set "WIN_REPO=C:\MyCode\AbstractWiki\abstract-wiki-architect"

REM Convert to a WSL path
for /f "usebackq delims=" %%I in (`wsl.exe wslpath -a "%WIN_REPO%"`) do set "WSL_REPO=%%I"

if "%WSL_REPO%"=="" (
  echo ERROR: WSL path conversion failed. Is WSL installed and working?
  pause
  exit /b 1
)

wsl.exe --cd "%WSL_REPO%" --exec bash -lic ^
"V=; \
if [ -f .venv/bin/activate ]; then V=.venv; fi; \
if [ -z $V ] && [ -f venv/bin/activate ]; then V=venv; fi; \
if [ -n $V ]; then \
  source $V/bin/activate; \
  echo VENV_OK:$VIRTUAL_ENV; \
  echo PY:$(which python3); \
  python3 --version; \
else \
  echo VENV_MISSING: expected .venv/ or venv/ in $(pwd); \
  echo Create: python3 -m venv .venv; \
fi; \
exec bash -li"
endlocal
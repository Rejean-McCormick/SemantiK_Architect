@echo off
setlocal EnableExtensions
TITLE Semantik Architect (WSL + venv)

REM Prefer "repo = folder where this BAT lives" if manage.py is present; otherwise fallback.
set "WIN_REPO=%~dp0"
if not exist "%WIN_REPO%manage.py" (
  set "WIN_REPO=C:\MyCode\AbstractWiki\abstract-wiki-architect"
)

REM Normalize to a full path
for %%I in ("%WIN_REPO%.") do set "WIN_REPO=%%~fI"

REM Convert to a WSL path
for /f "usebackq delims=" %%I in (`wsl.exe wslpath -a "%WIN_REPO%" 2^>NUL`) do set "WSL_REPO=%%I"

if not defined WSL_REPO (
  echo ERROR: WSL path conversion failed.
  echo Try: wsl.exe -l -v
  pause
  exit /b 1
)

echo ==================================================
echo SKA WSL SHELL (venv)
echo Windows repo: %WIN_REPO%
echo WSL repo:     %WSL_REPO%
echo ==================================================
echo.

REM Start WSL, activate venv if present, then drop into an interactive login shell.
REM Keep the bash command as ONE LINE (avoid Windows line-continuation issues).
wsl.exe --cd "%WSL_REPO%" --exec bash -lc "set +e; VENV=; if [ -f venv/bin/activate ]; then VENV=venv; elif [ -f .venv/bin/activate ]; then VENV=.venv; fi; echo PWD=$(pwd); if [ x$VENV != x ]; then source $VENV/bin/activate; echo VENV_OK=$VIRTUAL_ENV; else echo VENV_MISSING: expected venv/ or .venv/ in $(pwd); echo Create: python3 -m venv venv; fi; echo PY=$(command -v python3 2>/dev/null || true); python3 -V 2>/dev/null || true; exec bash -li"

set "CODE=%ERRORLEVEL%"
if not "%CODE%"=="0" (
  echo.
  echo WSL exited with code %CODE%
  pause
)

endlocal
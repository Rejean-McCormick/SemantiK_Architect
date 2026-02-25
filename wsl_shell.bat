@echo off
setlocal EnableExtensions
TITLE Abstract Wiki Architect (WSL - plain)

REM Windows path of the repo (edit only this)
set "WIN_REPO=C:\MyCode\AbstractWiki\abstract-wiki-architect"

REM Convert to a WSL path
for /f "usebackq delims=" %%I in (`wsl.exe wslpath -a "%WIN_REPO%"`) do set "WSL_REPO=%%I"

if "%WSL_REPO%"=="" (
  echo ERROR: WSL path conversion failed. Is WSL installed and working?
  pause
  exit /b 1
)

wsl.exe --cd "%WSL_REPO%" --exec bash -li
endlocal
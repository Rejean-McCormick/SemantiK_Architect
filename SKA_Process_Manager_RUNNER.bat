@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PS1=%SCRIPT_DIR%SKA_Process_Manager.ps1"

if not exist "%PS1%" (
  echo Could not find: %PS1%
  pause
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
  echo.
  echo PowerShell exited with code %EXITCODE%.
  pause
)

exit /b %EXITCODE%

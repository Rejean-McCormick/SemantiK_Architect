@echo off
cd /d "%~dp0"

where pwsh >nul 2>&1
if %errorlevel%==0 (
  pwsh -NoExit -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-Architect.ps1"
) else (
  powershell -NoExit -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-Architect.ps1"
)
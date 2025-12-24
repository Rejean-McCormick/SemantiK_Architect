@echo off
TITLE Abstract Wiki Architect

:: 1. Navigate to the project folder
cd /d "C:\MyCode\AbstractWiki\abstract-wiki-architect"

:: 2. Launch PowerShell 7 (pwsh) and execute the WSL command
::    -NoExit: Keeps the PowerShell window open if WSL crashes or exits.
::    -Command: Passes the WSL logic string.
::    Note: The double single-quotes ('') are required to escape quotes inside the command string.

pwsh -NoExit -Command "wsl -e bash -c 'source venv/bin/activate; echo ''Virtual Environment Activated!''; exec bash'"
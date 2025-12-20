@echo off
TITLE Abstract Wiki Architect
:: 1. Navigate to the project folder in Windows
cd /d "C:\MyCode\AbstractWiki\abstract-wiki-architect"

:: 2. Launch WSL, activate venv, and stay open
:: Note: 'exec bash' keeps the shell alive. The '(venv)' prompt might not show, 
:: but 'which python' will confirm you are using the virtual environment.
wsl -e bash -c "source venv/bin/activate; echo 'Virtual Environment Activated!'; exec bash"
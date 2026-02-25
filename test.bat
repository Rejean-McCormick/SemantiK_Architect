@echo off
TITLE WSL Sanity
wsl.exe --exec bash -lc "echo HELLO; uname -a; exec bash -li"
pause
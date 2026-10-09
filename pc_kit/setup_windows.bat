@echo off
rem One-click offline setup (Python 3.11, VC++ runtime, packages, checks). Safe to re-run.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_windows.ps1" %*
pause

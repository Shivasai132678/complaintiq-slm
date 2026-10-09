@echo off
rem Windows: fill an empty dashboard with clearly labelled public demo complaints.
cd /d "%~dp0"
set PYTHONUTF8=1
".venv\Scripts\python.exe" -m scripts.seed_demo
pause

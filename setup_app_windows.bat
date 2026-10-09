@echo off
rem Windows: offline setup of the ComplaintIQ app (Python 3.12 venv + packages). Run after the training kit is done.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0pc_kit\scripts_win\setup_app.ps1"
pause

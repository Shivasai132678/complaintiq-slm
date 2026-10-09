@echo off
rem Shared settings for the run_*.bat files.
set "KIT=%~dp0.."
set "PY=%KIT%\.venv\Scripts\python.exe"
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
set TOKENIZERS_PARALLELISM=false
set BITSANDBYTES_NOWELCOME=1
set PYTHONUTF8=1
set PYTHONUNBUFFERED=1
if not exist "%PY%" (
  echo The .venv is missing. Run setup_windows.bat first.
  pause
  exit /b 1
)
cd /d "%KIT%"

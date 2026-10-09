@echo off
rem Loads Qwen3-4B in 4-bit, 5 training steps, saves + reloads the adapter, evaluates 32 rows (~5-10 min).
call "%~dp0scripts_win\_env.bat" || exit /b 1
"%PY%" src\train_qwen3.py --mode dryrun %*
pause

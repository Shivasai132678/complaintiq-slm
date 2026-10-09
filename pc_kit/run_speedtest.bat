@echo off
rem ~200 real training steps; writes results\speedtest-Qwen3-4B-Instruct-2507\speedtest.json with the projected epoch time.
call "%~dp0scripts_win\_env.bat" || exit /b 1
"%PY%" src\train_qwen3.py --mode speedtest %*
pause

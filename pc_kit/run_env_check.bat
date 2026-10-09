@echo off
call "%~dp0scripts_win\_env.bat" || exit /b 1
"%PY%" src\env_check.py
pause

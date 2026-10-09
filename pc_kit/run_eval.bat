@echo off
rem Re-evaluate an adapter on test + check sets (writes eval\results.md).
rem Default adapter: results\qwen3-4b-main\final_adapter. Or: run_eval.bat --adapter results\qwen3-4b-main\checkpoints\checkpoint-2000
call "%~dp0scripts_win\_env.bat" || exit /b 1
set "ARGS=%*"
if "%ARGS%"=="" set "ARGS=--adapter results\qwen3-4b-main\final_adapter"
"%PY%" src\evaluate_qwen3.py %ARGS%
pause

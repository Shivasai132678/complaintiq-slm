@echo off
rem Merge adapter, convert to GGUF, quantize to Q4_K_M, copy it to ..\models for the app, then check it through llama-server on 300 test rows.
call "%~dp0scripts_win\_env.bat" || exit /b 1
set "ADAPTER=%~1"
if "%ADAPTER%"=="" set "ADAPTER=results\qwen3-4b-main\final_adapter"
"%PY%" src\export_gguf.py --adapter "%ADAPTER%" --verify-rows 300
pause

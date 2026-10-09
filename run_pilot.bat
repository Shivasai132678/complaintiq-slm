@echo off
rem Windows: start the model server (CUDA llama-server from pc_kit\tools) and the app on http://127.0.0.1:8501
rem Uses models\complaintiq-qwen3-4b-Q4_K_M.gguf if present, otherwise the Qwen2.5 GGUF.
rem Override with: set COMPLAINTIQ_MODEL_PATH=C:\path\to\model.gguf
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup_app_windows.bat first.
  pause
  exit /b 1
)
set PYTHONUTF8=1
start "" http://127.0.0.1:8501
".venv\Scripts\python.exe" scripts\launch_pilot.py
pause

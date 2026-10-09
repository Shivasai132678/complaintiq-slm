@echo off
rem Opens JupyterLab in the browser with notebooks\train_qwen3_windows.ipynb.
call "%~dp0scripts_win\_env.bat" || exit /b 1
"%KIT%\.venv\Scripts\jupyter-lab.exe" --notebook-dir="%KIT%" "notebooks\train_qwen3_windows.ipynb"

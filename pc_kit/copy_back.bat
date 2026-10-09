@echo off
rem Copies everything worth keeping (adapters, GGUF, evaluations, logs) to a USB drive or other folder.
rem Usage: copy_back.bat E:\complaintiq_results
if "%~1"=="" (
  echo Usage: copy_back.bat DESTINATION_FOLDER    e.g.  copy_back.bat E:\complaintiq_results
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts_win\copy_back.ps1" -Destination "%~1"
pause

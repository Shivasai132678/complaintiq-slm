@echo off
rem Continue RUN_ALL after a crash, reboot or fixed error, from the first unfinished step.
rem (Training continues from its newest checkpoint.) To start over, delete logs\run_all_state.json.
title ComplaintIQ RESUME_ALL
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0pc_kit\scripts_win\run_all.ps1" -Resume
pause

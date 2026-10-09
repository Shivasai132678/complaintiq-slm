@echo off
rem ONE CLICK on the Windows PC: setup -> dry run -> speed test -> train -> export -> app.
rem Progress: logs\run_all_status.txt   Full log: logs\run_all.log
rem Already finished steps are skipped, so running it again continues where it stopped.
rem Keep this window open. Training takes several hours.
title ComplaintIQ RUN_ALL
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0pc_kit\scripts_win\run_all.ps1"
pause

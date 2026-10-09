@echo off
rem Full training run. Resumes automatically from the last checkpoint if re-run.
rem Default: 1 epoch, stops cleanly after 7 hours. Extra flags are passed through, e.g.
rem   run_train.bat --time-budget-hours 6
rem   run_train.bat --max-steps 3000
call "%~dp0scripts_win\_env.bat" || exit /b 1
"%PY%" src\train_qwen3.py --mode train --run-name qwen3-4b-main --time-budget-hours 7 %*
pause

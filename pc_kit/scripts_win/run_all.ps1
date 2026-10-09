# One-command pipeline for the Windows PC: setup -> dry run -> speed test -> train -> export -> app.
# Started by RUN_ALL.bat / RESUME_ALL.bat in the project root. Finished steps are recorded in
# logs\run_all_state.json and skipped on the next run, so after a crash or reboot it continues
# where it stopped. Everything is logged to logs\run_all.log; logs\run_all_status.txt shows the
# current step. Delete logs\run_all_state.json to start over from step 1.
param([switch]$Resume)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$Kit = Join-Path $Root "pc_kit"
$Logs = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $Logs | Out-Null
$LogFile = Join-Path $Logs "run_all.log"
$StatusFile = Join-Path $Logs "run_all_status.txt"
$StateFile = Join-Path $Logs "run_all_state.json"
$VenvPy = Join-Path $Kit ".venv\Scripts\python.exe"
$Run = "qwen3-4b-main"
$RunDir = Join-Path $Kit "results\$Run"
$TrainHours = 7.0
$Steps = @("setup", "dryrun", "speedtest", "train", "export", "app_setup", "app_start")
$Titles = @{
    setup = "1/7 Setup: checksums, driver, Python 3.11, packages, GPU check"
    dryrun = "2/7 Dry run (5 steps, save/reload adapter)"
    speedtest = "3/7 Speed test (200 steps) and choosing the training length"
    train = "4/7 Training Qwen3-4B (checkpoints every 250 steps)"
    export = "5/7 Export GGUF, copy to models\, 300-row llama-server check"
    app_setup = "6/7 App setup (Python 3.12 + packages + tests)"
    app_start = "7/7 Starting the app at http://127.0.0.1:8501"
}

$env:HF_HUB_OFFLINE = "1"; $env:TRANSFORMERS_OFFLINE = "1"; $env:TOKENIZERS_PARALLELISM = "false"
$env:BITSANDBYTES_NOWELCOME = "1"; $env:PYTHONUTF8 = "1"; $env:PYTHONUNBUFFERED = "1"

function Log([string]$Text) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Text
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Load-State {
    if (Test-Path $StateFile) { return Get-Content $StateFile -Raw | ConvertFrom-Json }
    return [pscustomobject]@{ done = @(); max_steps = $null; started = (Get-Date -Format s) }
}
function Save-State($State) { $State | ConvertTo-Json | Set-Content -Path $StateFile -Encoding UTF8 }

function Set-Status([string]$Step, [string]$Detail = "") {
    $state = Load-State
    $lines = @("ComplaintIQ RUN_ALL status  (updated {0})" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), "")
    foreach ($s in $Steps) {
        $mark = "[ ]"
        if ($state.done -contains $s) { $mark = "[x]" } elseif ($s -eq $Step) { $mark = "[>]" }
        $lines += "$mark $($Titles[$s])"
    }
    $lines += ""
    if ($Detail) { $lines += $Detail; $lines += "" }
    $lines += "Full log: logs\run_all.log"
    $lines += "If it stopped: fix the reason shown at the end of the log, then double-click RESUME_ALL.bat."
    Set-Content -Path $StatusFile -Value $lines -Encoding UTF8
}

function Invoke-Logged([string]$Exe, [string[]]$Arguments) {
    # Stream a command's output to the console and the log; return its exit code.
    Log ("> " + $Exe + " " + ($Arguments -join " "))
    & $Exe @Arguments 2>&1 | ForEach-Object { $t = "$_"; Write-Host $t; Add-Content -Path $LogFile -Value $t -Encoding UTF8 }
    return $LASTEXITCODE
}

function Fail([string]$Step, [string]$Why) {
    Log "STOPPED at step '$Step': $Why"
    Set-Status $Step "STOPPED: $Why"
    Write-Host ""
    Write-Host "STOPPED at step '$Step'. Reason: $Why" -ForegroundColor Red
    Write-Host "Details: logs\run_all.log   Status: logs\run_all_status.txt" -ForegroundColor Red
    exit 1
}

function Mark-Done([string]$Step) {
    $state = Load-State
    $state.done = @($state.done) + $Step
    Save-State $state
    Log "Finished step '$Step'"
}

# ---------------------------------------------------------------------------------------------
$state = Load-State
if (-not (Test-Path $StateFile)) { Save-State $state }
Log ("RUN_ALL started" + $(if ($Resume) { " (resume)" } else { "" }) + ". Already done: " + (@($state.done) -join ", "))

# Do not let Windows sleep during training (restored when this window closes).
Add-Type -Namespace Win32 -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);' -ErrorAction SilentlyContinue
[void][Win32.Power]::SetThreadExecutionState([uint32]2147483649)  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED

foreach ($step in $Steps) {
    $state = Load-State
    if ($state.done -contains $step) { continue }
    Log "=== $($Titles[$step]) ==="
    Set-Status $step

    switch ($step) {
        "setup" {
            $code = Invoke-Logged "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $Kit "setup_windows.ps1"))
            if ($code -eq 3) {
                # Driver installed: continue automatically after the restart.
                $resume = Join-Path $Root "RESUME_ALL.bat"
                Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce" -Name "ComplaintIQResume" -Value "cmd /c `"$resume`""
                Fail $step "NVIDIA driver installed. Restart Windows; RESUME_ALL.bat starts by itself after you log in."
            }
            if ($code -ne 0) {
                Fail $step "Setup or GPU check failed (see results\setup_log.txt). If bitsandbytes is the problem, see README 'If bitsandbytes fails' (WSL2 needs you to act)."
            }
        }
        "dryrun" {
            $code = Invoke-Logged $VenvPy @("-u", (Join-Path $Kit "src\train_qwen3.py"), "--mode", "dryrun")
            if ($code -ne 0) { Fail $step "Dry run failed. Most often bitsandbytes/CUDA; see README 'If something goes wrong'." }
        }
        "speedtest" {
            $code = Invoke-Logged $VenvPy @("-u", (Join-Path $Kit "src\train_qwen3.py"), "--mode", "speedtest")
            if ($code -ne 0) { Fail $step "Speed test failed (if out of GPU memory: run_train.bat --batch-size 2 --grad-accum 8 by hand)." }
            $speed = Get-Content (Join-Path $Kit "results\speedtest-Qwen3-4B-Instruct-2507\speedtest.json") -Raw | ConvertFrom-Json
            $fit = [int][math]::Floor($TrainHours * 3600 * 0.92 / [double]$speed.seconds_per_step)
            $maxSteps = [math]::Min([int]$speed.steps_per_epoch, $fit)
            $state = Load-State
            $state.max_steps = $maxSteps
            Save-State $state
            Log ("Speed: {0} s/step, peak VRAM {1} GB, full epoch {2} h. Training will run {3} of {4} epoch steps." -f $speed.seconds_per_step, $speed.peak_vram_gb, $speed.projected_hours_per_epoch, $maxSteps, $speed.steps_per_epoch)
        }
        "train" {
            $maxSteps = (Load-State).max_steps
            $trainArgs = @("-u", (Join-Path $Kit "src\train_qwen3.py"), "--mode", "train", "--run-name", $Run, "--time-budget-hours", "$TrainHours")
            if ($maxSteps) { $trainArgs += @("--max-steps", "$maxSteps") }
            $console = Join-Path $Logs "train_console.log"
            Log ("> " + $VenvPy + " " + ($trainArgs -join " ") + "   (console output: logs\train_console.log)")
            $proc = Start-Process -FilePath $VenvPy -ArgumentList ($trainArgs | ForEach-Object { "`"$_`"" }) -WorkingDirectory $Kit -NoNewWindow -PassThru -RedirectStandardOutput $console -RedirectStandardError (Join-Path $Logs "train_console.err.log")
            $trainLog = Join-Path $RunDir "train_log.jsonl"
            while (-not $proc.HasExited) {
                Start-Sleep -Seconds 60
                $detail = "Training is running."
                if (Test-Path $trainLog) {
                    $events = Get-Content $trainLog -Tail 200 | ForEach-Object { try { $_ | ConvertFrom-Json } catch { } }
                    $last = $events | Where-Object { $_.event -eq "log" -and $_.loss } | Select-Object -Last 1
                    $acc = $events | Where-Object { $_.event -eq "val_accuracy" } | Select-Object -Last 1
                    if ($last) { $detail = "Training: step $($last.step) of $maxSteps, loss $([math]::Round([double]$last.loss, 4)), elapsed $([math]::Round($last.elapsed_s / 3600, 2)) h." }
                    if ($acc) { $detail += " Last validation accuracy: $($acc.accuracy) (step $($acc.step))." }
                }
                Set-Status $step $detail
            }
            $proc.WaitForExit()
            Get-Content $console -Tail 40 | ForEach-Object { Add-Content -Path $LogFile -Value $_ -Encoding UTF8 }
            if ($proc.ExitCode -ne 0) { Fail $step "Training stopped with an error (logs\train_console.err.log). RESUME_ALL.bat continues from the last checkpoint." }
            $results = Join-Path $RunDir "eval\results.md"
            if (Test-Path $results) { Log "Results:"; Get-Content $results | ForEach-Object { Log $_ } }
        }
        "export" {
            $code = Invoke-Logged $VenvPy @("-u", (Join-Path $Kit "src\export_gguf.py"), "--adapter", (Join-Path $RunDir "final_adapter"), "--verify-rows", "300")
            if ($code -ne 0) { Fail $step "GGUF export failed. The trained adapter is safe in pc_kit\results\$Run\final_adapter." }
        }
        "app_setup" {
            $code = Invoke-Logged "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $Kit "scripts_win\setup_app.ps1"))
            if ($code -ne 0) { Fail $step "App setup failed." }
        }
        "app_start" {
            # Not recorded as done: running RUN_ALL/RESUME_ALL again simply restarts the app.
            Set-Status "app_start" "Steps 1-6 finished. The app runs in this window: http://127.0.0.1:8501 (close the window to stop it; start it again later with run_pilot.bat). Training results: pc_kit\results\$Run\eval\results.md"
            Log "Starting the app. Close this window to stop it."
            Start-Process "http://127.0.0.1:8501"
            Set-Location $Root
            & (Join-Path $Root ".venv\Scripts\python.exe") (Join-Path $Root "scripts\launch_pilot.py")
            exit 0
        }
    }
    Mark-Done $step
}
Set-Status "" "All steps finished."

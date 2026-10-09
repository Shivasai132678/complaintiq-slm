# One-time offline setup of the ComplaintIQ Qwen3 training kit on a fresh Windows 11 PC.
# Run via setup_windows.bat (double-click). Safe to re-run: finished steps are skipped.
# Log: results\setup_log.txt
param([switch]$SkipChecksums)

$ErrorActionPreference = "Stop"
$Kit = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Kit
New-Item -ItemType Directory -Force -Path (Join-Path $Kit "results") | Out-Null
Start-Transcript -Path (Join-Path $Kit "results\setup_log.txt") -Append | Out-Null

function Step([string]$Message) { Write-Host ""; Write-Host "=== $Message ===" -ForegroundColor Cyan }
function Stop-Setup([string]$Message, [int]$Code = 1) {
    Write-Host ""
    Write-Host "SETUP STOPPED: $Message" -ForegroundColor Red
    Stop-Transcript | Out-Null
    exit $Code   # 3 = restart Windows, then run setup (or RESUME_ALL.bat) again
}

if ($Kit.Length -gt 50) {
    Write-Warning "The kit path is long ($Kit). If pip reports path errors, move the project to C:\SLMProject and run setup again."
}

# 0. Online downloads (lite bundle) ----------------------------------------------
Step "0/6 Downloading anything the copied folder does not contain (model, installers, llama.cpp)"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Kit "scripts_win\fetch_online.ps1")
if ($LASTEXITCODE -ne 0) { Stop-Setup "Required files are missing and could not be downloaded (see the list above)." }

# 1. Checksums ---------------------------------------------------------------
if (-not $SkipChecksums) {
    Step "1/6 Verifying SHA-256 checksums of copied files (1-3 min)"
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Kit "verify_checksums.ps1")
    if ($LASTEXITCODE -ne 0) { Stop-Setup "Some files are missing or corrupted. Copy them again from the USB drive." }
} else {
    Step "1/6 Checksums skipped"
}

# 2. NVIDIA driver -----------------------------------------------------------
Step "2/6 NVIDIA GPU and driver"
$smi = "C:\Windows\System32\nvidia-smi.exe"
function Get-DriverInstaller {
    $found = Get-ChildItem (Join-Path $Kit "installers") -Filter "nvidia-*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $found) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Kit "scripts_win\fetch_online.ps1") -DriverNeeded
        $found = Get-ChildItem (Join-Path $Kit "installers") -Filter "nvidia-*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    }
    if (-not $found) { Stop-Setup "No NVIDIA driver installer: download it from nvidia.com/drivers (GeForce RTX 4070) or copy pc_kit\installers from the full bundle." }
    return $found
}
if (-not (Test-Path $smi)) {
    $driverInstaller = Get-DriverInstaller
    Write-Host "No NVIDIA driver found. Starting the bundled driver installer (admin prompt; choose Express)."
    Start-Process -FilePath $driverInstaller.FullName -Verb RunAs -Wait
    Stop-Setup "Driver installer finished. Restart Windows, then double-click setup_windows.bat (or RESUME_ALL.bat) again." 3
}
$gpu = (& $smi --query-gpu=name,driver_version,memory.total --format=csv,noheader) | Select-Object -First 1
Write-Host "GPU: $gpu"
$driverVersion = [double](($gpu -split ",")[1].Trim())
if ($driverVersion -lt 560) {
    Write-Host "Driver $driverVersion is older than 560 (needed for CUDA 12.6 PyTorch). Starting the bundled driver installer."
    $driverInstaller = Get-DriverInstaller
    Start-Process -FilePath $driverInstaller.FullName -Verb RunAs -Wait
    Stop-Setup "Driver updated. Restart Windows, then run setup_windows.bat (or RESUME_ALL.bat) again." 3
}

# 3. Visual C++ runtime --------------------------------------------------------
Step "3/6 Microsoft Visual C++ runtime"
$vc = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" -ErrorAction SilentlyContinue
if ($vc -and $vc.Installed -eq 1) {
    Write-Host "Already installed ($($vc.Version))"
} else {
    Write-Host "Installing vc_redist.x64.exe (admin prompt)..."
    Start-Process -FilePath (Join-Path $Kit "installers\vc_redist.x64.exe") -ArgumentList "/install", "/quiet", "/norestart" -Verb RunAs -Wait
}

# 4. Python 3.11 ---------------------------------------------------------------
Step "4/6 Python 3.11"
$py = Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Installing Python 3.11.9 for the current user (no admin needed)..."
    $args311 = @("/quiet", "InstallAllUsers=0", "PrependPath=0", "Include_launcher=1", "Include_test=0", "Shortcuts=0")
    Start-Process -FilePath (Join-Path $Kit "installers\python-3.11.9-amd64.exe") -ArgumentList $args311 -Wait
}
if (-not (Test-Path $py)) { Stop-Setup "Python 3.11 was not found at $py after installation." }
& $py --version

# 5. Virtual environment + offline packages -------------------------------------
Step "5/6 Creating .venv and installing packages (offline from wheels\, or online)"
$venvPy = Join-Path $Kit ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { & $py -m venv (Join-Path $Kit ".venv") }
$lock = Join-Path $Kit "requirements-windows.lock.txt"
if (Get-ChildItem (Join-Path $Kit "wheels") -Filter "torch-*.whl" -ErrorAction SilentlyContinue) {
    & $venvPy -m pip install --no-index --find-links (Join-Path $Kit "wheels") -r $lock
} else {
    Write-Host "No bundled wheels: downloading the same pinned packages from PyPI and download.pytorch.org (~3 GB)..."
    & $venvPy -m pip install --extra-index-url https://download.pytorch.org/whl/cu126 -r $lock
}
if ($LASTEXITCODE -ne 0) { Stop-Setup "pip install failed; see results\setup_log.txt." }

# 6. Environment check ---------------------------------------------------------
Step "6/6 Environment check (CUDA, bf16, bitsandbytes 4-bit, model, data, tools)"
$env:PYTHONUTF8 = "1"
& $venvPy (Join-Path $Kit "src\env_check.py")
if ($LASTEXITCODE -ne 0) { Stop-Setup "Environment check failed. See README: 'If bitsandbytes fails'." }

Write-Host ""
Write-Host "SETUP COMPLETE. Next: double-click run_dryrun.bat" -ForegroundColor Green
Stop-Transcript | Out-Null
exit 0

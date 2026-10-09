# Offline setup of the ComplaintIQ app (FastAPI + React build + llama.cpp) on Windows.
# Run via setup_app_windows.bat in the project root. Safe to re-run.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$Kit = Join-Path $Root "pc_kit"
Set-Location $Root

Write-Host "=== 1/4 Python 3.12 ===" -ForegroundColor Cyan
$py = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
if (-not (Test-Path $py)) {
    $args312 = @("/quiet", "InstallAllUsers=0", "PrependPath=0", "Include_launcher=1", "Include_test=0", "Shortcuts=0")
    Start-Process -FilePath (Join-Path $Kit "installers\python-3.12.10-amd64.exe") -ArgumentList $args312 -Wait
}
if (-not (Test-Path $py)) { Write-Host "Python 3.12 not found at $py" -ForegroundColor Red; exit 1 }
& $py --version

Write-Host "=== 2/4 App virtual environment (.venv, offline packages) ===" -ForegroundColor Cyan
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if ((Test-Path (Join-Path $Root ".venv")) -and -not (Test-Path $venvPy)) {
    Write-Host "Removing a non-Windows .venv copied from the Mac..."
    Remove-Item -Recurse -Force (Join-Path $Root ".venv")
}
if (-not (Test-Path $venvPy)) { & $py -m venv (Join-Path $Root ".venv") }
$appLock = Join-Path $Kit "requirements-app-windows.lock.txt"
if (Get-ChildItem (Join-Path $Kit "wheels_app") -Filter "*.whl" -ErrorAction SilentlyContinue) {
    & $venvPy -m pip install --no-index --find-links (Join-Path $Kit "wheels_app") -r $appLock
} else {
    Write-Host "No bundled app wheels: installing the same pinned packages from PyPI..."
    & $venvPy -m pip install -r $appLock
}
if ($LASTEXITCODE -ne 0) { Write-Host "pip install failed" -ForegroundColor Red; exit 1 }

Write-Host "=== 3/4 Frontend build and model server ===" -ForegroundColor Cyan
if (-not (Test-Path (Join-Path $Root "frontend\dist\index.html"))) { Write-Host "frontend\dist is missing (it is built on the Mac and copied)." -ForegroundColor Red; exit 1 }
if (-not (Test-Path (Join-Path $Kit "tools\llama-bin\llama-server.exe"))) { Write-Host "pc_kit\tools\llama-bin\llama-server.exe is missing." -ForegroundColor Red; exit 1 }
Write-Host "OK"

Write-Host "=== 4/4 Tests ===" -ForegroundColor Cyan
$env:PYTHONUTF8 = "1"
& $venvPy -m pytest -q
if ($LASTEXITCODE -ne 0) { Write-Host "Some tests failed (see above). The app may still run." -ForegroundColor Yellow }
Write-Host ""
Write-Host "APP SETUP COMPLETE. Start it with run_pilot.bat" -ForegroundColor Green

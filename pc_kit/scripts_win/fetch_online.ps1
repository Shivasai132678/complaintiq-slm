# Download whatever the copied folder is missing (lite bundle): installers, the Qwen3-4B model,
# llama.cpp binaries. Every file is checked against the SHA-256 in pc_kit\downloads.json.
# Files already present with the right hash are skipped. Exit code 0 = everything needed is present.
param([switch]$DriverNeeded)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$Kit = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$manifest = Get-Content (Join-Path $Kit "downloads.json") -Raw | ConvertFrom-Json
$curl = if ($env:SystemRoot) { Join-Path $env:SystemRoot "System32\curl.exe" } else { "curl" }  # curl.exe ships with Windows 10/11
$failed = @()

function Get-Sha([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLower() }

foreach ($item in $manifest.items) {
    if ($item.when -eq "driver_needed" -and -not $DriverNeeded) { continue }
    if ($item.skip_if_exists -and (Test-Path (Join-Path $Kit $item.skip_if_exists))) { continue }
    $dest = Join-Path $Kit ($item.dest -replace "/", "\")
    $check = -not ($item.PSObject.Properties.Name -contains "verify" -and $item.verify -eq $false)
    if ((Test-Path -LiteralPath $dest) -and ((-not $check) -or (Get-Sha $dest) -eq $item.sha256)) { continue }

    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
    $mb = [math]::Round($item.bytes / 1MB)
    Write-Host "Downloading $($item.dest) ($mb MB) ..."
    $ok = $false
    for ($attempt = 1; $attempt -le 3 -and -not $ok; $attempt++) {
        & $curl -L --fail --retry 5 --retry-delay 5 -C - -o "$dest" "$($item.url)"
        if ($LASTEXITCODE -eq 0 -and ((-not $check) -or (Get-Sha $dest) -eq $item.sha256)) { $ok = $true }
        elseif ($LASTEXITCODE -eq 0) { Write-Host "  checksum mismatch, retrying from scratch"; Remove-Item -LiteralPath $dest -Force }
        else { Write-Host "  download error (curl exit $LASTEXITCODE), retry $attempt of 3" }
    }
    if (-not $ok) {
        if ($item.optional) { Write-Host "  optional file skipped: $($item.dest)" -ForegroundColor Yellow; continue }
        $failed += $item
        continue
    }
    if ($item.extract_to) {
        $target = Join-Path $Kit ($item.extract_to -replace "/", "\")
        New-Item -ItemType Directory -Force -Path $target | Out-Null
        Expand-Archive -LiteralPath $dest -DestinationPath $target -Force
        Remove-Item -LiteralPath $dest -Force
    }
}

if ($failed.Count -gt 0) {
    Write-Host ""
    Write-Host "Could not download (no internet, a blocked site, or a changed file):" -ForegroundColor Red
    foreach ($f in $failed) { Write-Host "  $($f.dest)   from $($f.url)" -ForegroundColor Red }
    if ($failed | Where-Object { $_.dest -like "model/*" }) {
        Write-Host "Hugging Face could not be reached. Copy pc_kit\model\Qwen3-4B-Instruct-2507 from the FULL bundle by USB," -ForegroundColor Red
        Write-Host "then run RESUME_ALL.bat (or setup_windows.bat) again." -ForegroundColor Red
    } else {
        Write-Host "Copy the listed files from the FULL bundle (same paths under pc_kit) by USB, then run again." -ForegroundColor Red
    }
    exit 1
}
Write-Host "All required downloads present and verified."
exit 0

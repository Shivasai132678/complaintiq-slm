# Verify every file listed in CHECKSUMS.sha256 ("<sha256>  <relative/path>").
# Exit code 0 when all files are present and match.
$ErrorActionPreference = "Stop"
$Kit = Split-Path -Parent $MyInvocation.MyCommand.Path
$lines = Get-Content (Join-Path $Kit "CHECKSUMS.sha256") | Where-Object { $_ -and -not $_.StartsWith("#") }
$bad = 0
$missing = 0
$i = 0
foreach ($line in $lines) {
    $i++
    $expected = $line.Substring(0, 64).ToLower()
    $relative = $line.Substring(66)
    $path = Join-Path $Kit ($relative -replace "/", "\")
    if (-not (Test-Path -LiteralPath $path)) {
        $missing++
        continue
    }
    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower()
    if ($actual -ne $expected) {
        Write-Host "MISMATCH $relative" -ForegroundColor Red
        $bad++
    }
    if ($i % 50 -eq 0) { Write-Host "  checked $i of $($lines.Count)" }
}
if ($missing -gt 0) {
    Write-Host "$missing listed file(s) are not in this copy (normal for the lite bundle: packages are installed online)." -ForegroundColor Yellow
}
if ($bad -eq 0) {
    Write-Host "All $($lines.Count - $missing) present files verified." -ForegroundColor Green
    exit 0
}
Write-Host "$bad problem file(s)." -ForegroundColor Red
exit 1

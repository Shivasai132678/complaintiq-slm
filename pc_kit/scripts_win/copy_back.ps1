# Copy results\ to a destination, skipping bulky intermediates.
# Kept: final adapters, GGUF files, eval\, logs, summaries, and the newest checkpoint of each run.
param([Parameter(Mandatory = $true)][string]$Destination)
$ErrorActionPreference = "Stop"
$Kit = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$source = Join-Path $Kit "results"
$target = Join-Path $Destination "results"
robocopy $source $target /E /XD checkpoints merged_hf /XF *-f16.gguf /R:2 /W:2 /NP | Out-Host
foreach ($run in Get-ChildItem $source -Directory) {
    $ckpt = Join-Path $run.FullName "checkpoints"
    if (Test-Path $ckpt) {
        $last = Get-ChildItem $ckpt -Directory -Filter "checkpoint-*" |
            Sort-Object { [int]($_.Name -replace "checkpoint-", "") } | Select-Object -Last 1
        if ($last) {
            robocopy $last.FullName (Join-Path $target "$($run.Name)\checkpoints\$($last.Name)") /E /R:2 /W:2 /NP | Out-Host
        }
    }
}
$ggufs = Get-ChildItem $target -Recurse -Filter *.gguf
Write-Host ""
Write-Host "Copied to $target"
foreach ($g in $ggufs) { Write-Host ("  {0}  {1:N2} GB" -f $g.FullName, ($g.Length / 1GB)) }
if (-not $ggufs) { Write-Host "  (no GGUF found - did run_export.bat finish?)" -ForegroundColor Yellow }

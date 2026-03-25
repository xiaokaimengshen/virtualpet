param(
    [string]$SourceRoot = "",
    [string]$BackupRoot = "",
    [string]$Label = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $SourceRoot) {
    $SourceRoot = Split-Path -Parent $PSScriptRoot
}

if (-not $BackupRoot) {
    $BackupRoot = Join-Path (Split-Path -Parent $SourceRoot) "BeiFen"
}

if (-not (Test-Path -LiteralPath $SourceRoot)) {
    throw "SourceRoot does not exist: $SourceRoot"
}

if (-not (Test-Path -LiteralPath (Join-Path $SourceRoot "run_DyberPet.py"))) {
    throw "SourceRoot does not look like DyberPet source root: $SourceRoot"
}

if (-not (Test-Path -LiteralPath $BackupRoot)) {
    New-Item -ItemType Directory -Path $BackupRoot | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$safeLabel = $Label.Trim()
if ($safeLabel) {
    $safeLabel = "_" + (($safeLabel -replace '[^\w\-\u4e00-\u9fa5]+', "_").Trim("_"))
}

$archiveName = "DyberPet-main_${timestamp}${safeLabel}.zip"
$archivePath = Join-Path $BackupRoot $archiveName

Write-Host "Creating archive..."
Write-Host "Source:  $SourceRoot"
Write-Host "Target:  $archivePath"

Compress-Archive -Path (Join-Path $SourceRoot "*") -DestinationPath $archivePath -Force

Write-Host ""
Write-Host "Archive created successfully."
Write-Host $archivePath

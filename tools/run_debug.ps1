param(
    [switch]$SkipBackup,
    [switch]$NoRun,
    [string]$Label = "pre_debug"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$pythonExe = Join-Path $projectRoot ".venv\\Scripts\\python.exe"
if (-not (Test-Path -LiteralPath $pythonExe)) {
    $pythonExe = "python"
}

if (-not $SkipBackup) {
    & (Join-Path $PSScriptRoot "archive_runnable_version.ps1") -Label $Label
}

$prevErrAction = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $pythonExe -c "import tendo, PySide6, qfluentwidgets, pynput" >$null 2>$null
$depExit = $LASTEXITCODE
$ErrorActionPreference = $prevErrAction

if ($depExit -ne 0) {
    Write-Host "Missing runtime dependencies."
    Write-Host "Please install them first (example):"
    Write-Host "  pip install tendo pyside6==6.5.2 PySide6-Fluent-Widgets==1.5.4 pynput apscheduler"
    exit $LASTEXITCODE
}

if ($NoRun) {
    Write-Host "Environment check complete."
    exit 0
}

Write-Host "Launching DyberPet (debug mode)..."
& $pythonExe ".\\run_DyberPet.py"

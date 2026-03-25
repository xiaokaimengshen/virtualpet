@echo off
setlocal

set SCRIPT_DIR=%~dp0
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%tools\run_debug.ps1" -SkipBackup %*

endlocal

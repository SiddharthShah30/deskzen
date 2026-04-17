@echo off
REM Denji Synthetic Command Interface - Windows Batch Installer
REM This file allows double-clicking to start the installation
REM
REM Right-click this file and select "Run as Administrator" for automatic elevation
REM Or just double-click - it will request admin privileges

setlocal enabledelayedexpansion

REM Request admin privileges if not running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator privileges...
    timeout /t 2 /nobreak
    powershell -Command "Start-Process cmd.exe -ArgumentList '/c %~s0' -Verb RunAs"
    exit /b
)

REM Run the PowerShell installer
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║     DENJI SYNTHETIC COMMAND INTERFACE - INSTALLATION WIZARD    ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo Starting PowerShell installer...
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0install.ps1"

pause

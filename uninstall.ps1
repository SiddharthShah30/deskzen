# Denji Synthetic Command Interface - Uninstall Script for Windows
# ==================================================================
# This script safely removes Denji and cleans up all installations
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File uninstall.ps1

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        DENJI SYNTHETIC COMMAND INTERFACE - UNINSTALLER         ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "⚠️  This script requires Administrator privileges." -ForegroundColor Yellow
    Write-Host "Restarting with elevated permissions..." -ForegroundColor Yellow
    Start-Process powershell -Args "-ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# Confirmation
Write-Host "This will uninstall Denji and remove:" -ForegroundColor Yellow
Write-Host "  • All Denji packages" -ForegroundColor White
Write-Host "  • Virtual environment (.venv folder)" -ForegroundColor White
Write-Host "  • Configuration files (optional)" -ForegroundColor White
Write-Host ""
Write-Host "Your todo list and calendar data will be preserved in ~/.terminal_standby_todos.json and ~/.cal.json" -ForegroundColor Gray
Write-Host ""
$confirm = Read-Host "Do you want to continue? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Uninstall cancelled" -ForegroundColor Yellow
    exit
}

Write-Host ""
Write-Host "[1/3] Removing virtual environment..." -ForegroundColor Cyan
$venvPath = ".\.venv"
if (Test-Path $venvPath) {
    try {
        Remove-Item -Path $venvPath -Recurse -Force -ErrorAction Stop
        Write-Host "✓ Virtual environment removed" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Could not remove virtual environment: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "Virtual environment not found (already removed)" -ForegroundColor Gray
}

Write-Host "[2/3] Uninstalling Denji packages..." -ForegroundColor Cyan
$uninstallPackages = @(
    "pyttsx3",
    "SpeechRecognition",
    "sounddevice",
    "opencv-python",
    "numpy",
    "requests",
    "psutil",
    "feedparser",
    "icalendar",
    "pywin32",
    "windows-curses"
)

# Try to uninstall from system Python
try {
    foreach ($pkg in $uninstallPackages) {
        pip uninstall -y "$pkg" 2>$null
    }
    Write-Host "✓ System packages uninstalled" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Could not uninstall from system Python (this is okay)" -ForegroundColor Gray
}

Write-Host "[3/3] Cleaning up..." -ForegroundColor Cyan

# Remove cache and build artifacts
$pathsToClean = @(
    "build",
    "dist",
    "*.egg-info",
    "__pycache__",
    ".pytest_cache",
    ".egg-info"
)

foreach ($path in $pathsToClean) {
    Get-ChildItem -Path . -Filter $path -Recurse -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Host "✓ Cache and build artifacts removed" -ForegroundColor Green

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║        ✓ DENJI UNINSTALL COMPLETE                              ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "WHAT WAS REMOVED:" -ForegroundColor Cyan
Write-Host "  ✓ All Denji packages and dependencies" -ForegroundColor White
Write-Host "  ✓ Virtual environment" -ForegroundColor White
Write-Host "  ✓ Cache and build artifacts" -ForegroundColor White
Write-Host ""

Write-Host "WHAT WAS PRESERVED:" -ForegroundColor Cyan
Write-Host "  ✓ Your todo list (~\.terminal_standby_todos.json)" -ForegroundColor White
Write-Host "  ✓ Your calendar data (~\.cal.json)" -ForegroundColor White
Write-Host "  ✓ This source code (current folder)" -ForegroundColor White
Write-Host ""

Write-Host "TO REINSTALL DENJI:" -ForegroundColor Yellow
Write-Host "  powershell -ExecutionPolicy Bypass -File install.ps1" -ForegroundColor White
Write-Host ""

Read-Host "Press Enter to close"

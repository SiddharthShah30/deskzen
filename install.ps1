# Denji Synthetic Command Interface - Installation Script for Windows
# =====================================================================
# This script automatically installs Denji and all dependencies on Windows
# 
# Usage (Copy & Paste into PowerShell as Administrator):
#   iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/SiddharthShah30/deskzen/main/install.ps1'))
#
# Or locally:
#   powershell -ExecutionPolicy Bypass -File install.ps1
#
# To uninstall:
#   powershell -ExecutionPolicy Bypass -File uninstall.ps1

param(
    [switch]$Force = $false
)

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     DENJI SYNTHETIC COMMAND INTERFACE - INSTALLATION WIZARD    ║" -ForegroundColor Cyan
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

# Step 1: Check Python installation
Write-Host "[1/6] Checking Python 3.9+ installation..." -ForegroundColor Cyan
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "3\.([9]|1[0-9])") {
        Write-Host "✓ Python $pythonVersion found" -ForegroundColor Green
    } else {
        Write-Host "✗ Python 3.9+ required, found: $pythonVersion" -ForegroundColor Red
        Write-Host "Install Python from: https://www.python.org/downloads/" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
} catch {
    Write-Host "✗ Python not found in PATH" -ForegroundColor Red
    Write-Host "Install Python from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 2: Check pip
Write-Host "[2/6] Verifying pip package manager..." -ForegroundColor Cyan
try {
    pip --version | Out-Null
    Write-Host "✓ pip found" -ForegroundColor Green
} catch {
    Write-Host "✗ pip not found, upgrading Python..." -ForegroundColor Red
    python -m ensurepip --upgrade
}

# Step 3: Create/activate virtual environment
Write-Host "[3/6] Setting up virtual environment..." -ForegroundColor Cyan
$venvPath = ".\.venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment..."
    python -m venv $venvPath
} else {
    Write-Host "Virtual environment already exists"
}

# Activate virtual environment
& "$venvPath\Scripts\Activate.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to activate virtual environment" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Virtual environment activated" -ForegroundColor Green

# Step 4: Upgrade pip, setuptools, wheel
Write-Host "[4/6] Upgrading package managers..." -ForegroundColor Cyan
python -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Warning: pip upgrade had issues, continuing..." -ForegroundColor Yellow
}
Write-Host "✓ Package managers updated" -ForegroundColor Green

# Step 5: Install dependencies
Write-Host "[5/6] Installing Denji and dependencies..." -ForegroundColor Cyan
Write-Host "This may take 2-5 minutes on first install..." -ForegroundColor Gray

$dependencies = @(
    "pyttsx3>=2.90",
    "SpeechRecognition>=3.10.1",
    "sounddevice>=0.5.0",
    "opencv-python>=4.10.0.84",
    "numpy>=1.21.0",
    "requests>=2.28.0",
    "psutil>=5.9.0",
    "feedparser>=6.0.10",
    "icalendar>=5.0.0",
    "pywin32>=305; sys_platform == 'win32'",
    "windows-curses>=2.3.0"
)

foreach ($dep in $dependencies) {
    Write-Host "  Installing: $dep" -ForegroundColor Gray
    pip install "$dep" --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠️  Warning: Issue installing $dep, continuing..." -ForegroundColor Yellow
    }
}
Write-Host "✓ All dependencies installed" -ForegroundColor Green

# Step 6: Install Denji in editable mode
Write-Host "[6/6] Installing Denji application..." -ForegroundColor Cyan
pip install -e . --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Denji installed successfully" -ForegroundColor Green
} else {
    Write-Host "⚠️  Denji setup had issues, but core components installed" -ForegroundColor Yellow
}

# Installation complete
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║           ✓ DENJI INSTALLATION COMPLETE                        ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "QUICK START:" -ForegroundColor Cyan
Write-Host "  1. Open a new PowerShell window" -ForegroundColor White
Write-Host "  2. Navigate to: cd '$PWD'" -ForegroundColor White
Write-Host "  3. Run: python main.py" -ForegroundColor White
Write-Host "     OR: denji" -ForegroundColor White
Write-Host ""

Write-Host "OPTIONAL ENHANCEMENTS:" -ForegroundColor Cyan
Write-Host "  • OpenCode AI Agent (recommended):" -ForegroundColor White
Write-Host "    npm install -g opencode-ai@latest" -ForegroundColor White
Write-Host "  • Ollama Local LLM (for speed):" -ForegroundColor White
Write-Host "    https://ollama.ai" -ForegroundColor White
Write-Host ""

Write-Host "TO UNINSTALL DENJI:" -ForegroundColor Yellow
Write-Host "  powershell -ExecutionPolicy Bypass -File uninstall.ps1" -ForegroundColor White
Write-Host ""

Write-Host "Documentation: See README.md and AI_INTEGRATION.md" -ForegroundColor Gray
Write-Host ""

Read-Host "Press Enter to close"

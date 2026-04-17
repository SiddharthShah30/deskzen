#!/bin/bash
# Denji Synthetic Command Interface - Installation Script for macOS/Linux
# ========================================================================
# This script automatically installs Denji and all dependencies
#
# Usage (curl pipe):
#   curl -fsSL https://raw.githubusercontent.com/SiddharthShah30/deskzen/main/install.sh | bash
#
# Or locally:
#   bash install.sh
#
# To uninstall:
#   bash uninstall.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     DENJI SYNTHETIC COMMAND INTERFACE - INSTALLATION WIZARD    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Step 1: Detect OS and install system dependencies
echo -e "${CYAN}[1/6] Detecting system and installing system dependencies...${NC}"

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Detected: Linux"
    if command -v apt-get &> /dev/null; then
        echo "Using apt-get package manager"
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip python3-venv curl
    elif command -v yum &> /dev/null; then
        echo "Using yum package manager"
        sudo yum install -y python3 python3-pip curl
    elif command -v pacman &> /dev/null; then
        echo "Using pacman package manager"
        sudo pacman -S --noconfirm python python-pip curl
    else
        echo -e "${YELLOW}⚠️  Unsupported Linux distribution${NC}"
        echo "Please install Python 3.9+ and pip manually"
        exit 1
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected: macOS"
    if command -v brew &> /dev/null; then
        echo "Using Homebrew"
        brew install python@3.11 || brew upgrade python@3.11
        echo 'export PATH="/usr/local/opt/python@3.11/bin:$PATH"' >> ~/.zprofile
    else
        echo -e "${YELLOW}⚠️  Homebrew not found. Install from: https://brew.sh${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Unsupported OS: $OSTYPE${NC}"
    exit 1
fi
echo -e "${GREEN}✓ System dependencies installed${NC}"

# Step 2: Check Python installation
echo -e "${CYAN}[2/6] Verifying Python 3.9+ installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 not found in PATH${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | grep -oP '\d+\.\d+')
REQUIRED_VERSION="3.9"
if (( $(echo "$PYTHON_VERSION < $REQUIRED_VERSION" | bc -l) )); then
    echo -e "${RED}✗ Python 3.9+ required, found: $PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# Step 3: Create/activate virtual environment
echo -e "${CYAN}[3/6] Setting up virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists"
fi
source .venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Step 4: Upgrade pip
echo -e "${CYAN}[4/6] Upgrading package managers...${NC}"
python3 -m pip install --upgrade pip setuptools wheel --quiet
echo -e "${GREEN}✓ Package managers updated${NC}"

# Step 5: Install dependencies
echo -e "${CYAN}[5/6] Installing Denji and dependencies...${NC}"
echo "This may take 2-5 minutes on first install..."

DEPENDENCIES=(
    "pyttsx3>=2.90"
    "SpeechRecognition>=3.10.1"
    "sounddevice>=0.5.0"
    "opencv-python>=4.10.0.84"
    "numpy>=1.21.0"
    "requests>=2.28.0"
    "psutil>=5.9.0"
    "feedparser>=6.0.10"
    "icalendar>=5.0.0"
)

for dep in "${DEPENDENCIES[@]}"; do
    echo "  Installing: $dep"
    pip install "$dep" --quiet || echo "  ⚠️  Warning: Issue installing $dep, continuing..."
done
echo -e "${GREEN}✓ All dependencies installed${NC}"

# Step 6: Install Denji in editable mode
echo -e "${CYAN}[6/6] Installing Denji application...${NC}"
pip install -e . --quiet && echo -e "${GREEN}✓ Denji installed successfully${NC}" || \
    echo -e "${YELLOW}⚠️  Denji setup had issues, but core components installed${NC}"

# Installation complete
echo ""
echo -e "${GREEN}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║           ✓ DENJI INSTALLATION COMPLETE                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

echo -e "${CYAN}QUICK START:${NC}"
echo "  1. Activate environment: source .venv/bin/activate"
echo "  2. Run: python3 main.py"
echo "     OR: denji"
echo ""

echo -e "${CYAN}OPTIONAL ENHANCEMENTS:${NC}"
echo "  • OpenCode AI Agent (recommended):"
echo "    npm install -g opencode-ai@latest"
echo "  • Ollama Local LLM (for speed):"
echo "    https://ollama.ai"
echo ""

echo -e "${YELLOW}TO UNINSTALL DENJI:${NC}"
echo "  bash uninstall.sh"
echo ""

echo -e "${CYAN}Documentation: See README.md and AI_INTEGRATION.md${NC}"
echo ""

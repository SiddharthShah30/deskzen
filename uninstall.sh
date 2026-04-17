#!/bin/bash
# Denji Synthetic Command Interface - Uninstall Script for macOS/Linux
# ===================================================================
# This script safely removes Denji and cleans up all installations
#
# Usage:
#   bash uninstall.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        DENJI SYNTHETIC COMMAND INTERFACE - UNINSTALLER         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Confirmation
echo -e "${YELLOW}This will uninstall Denji and remove:${NC}"
echo "  • All Denji packages"
echo "  • Virtual environment (.venv folder)"
echo "  • Cache and build artifacts"
echo ""
echo -e "${CYAN}Your todo list and calendar data will be preserved in ~/.terminal_standby_todos.json and ~/.cal.json${NC}"
echo ""
read -p "Do you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${YELLOW}Uninstall cancelled${NC}"
    exit
fi

echo ""

# Step 1: Deactivate virtual environment
echo -e "${CYAN}[1/3] Deactivating virtual environment...${NC}"
if [ ! -z "$VIRTUAL_ENV" ]; then
    deactivate || true
fi
echo -e "${GREEN}✓ Virtual environment deactivated${NC}"

# Step 2: Remove virtual environment
echo -e "${CYAN}[2/3] Removing virtual environment...${NC}"
if [ -d ".venv" ]; then
    rm -rf .venv
    echo -e "${GREEN}✓ Virtual environment removed${NC}"
else
    echo "Virtual environment not found (already removed)"
fi

# Step 3: Clean up cache and build artifacts
echo -e "${CYAN}[3/3] Cleaning up...${NC}"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
echo -e "${GREEN}✓ Cache and build artifacts removed${NC}"

# Uninstall complete
echo ""
echo -e "${GREEN}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        ✓ DENJI UNINSTALL COMPLETE                              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

echo -e "${CYAN}WHAT WAS REMOVED:${NC}"
echo "  ✓ All Denji packages and dependencies"
echo "  ✓ Virtual environment"
echo "  ✓ Cache and build artifacts"
echo ""

echo -e "${CYAN}WHAT WAS PRESERVED:${NC}"
echo "  ✓ Your todo list (~/.terminal_standby_todos.json)"
echo "  ✓ Your calendar data (~/.cal.json)"
echo "  ✓ This source code (current folder)"
echo ""

echo -e "${YELLOW}TO REINSTALL DENJI:${NC}"
echo "  bash install.sh"
echo ""

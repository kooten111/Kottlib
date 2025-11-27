#!/bin/bash
#
# YACLib Enhanced - Start Web UI Only
# Starts the Svelte web frontend
#
# Usage: ./start_webui.sh
#
# NOTE: Backend API must be running separately!
#       Run ./start_backend.sh first or use ./start.sh for both
#

set -e  # Exit on error

echo "=================================================="
echo "       YACLib Enhanced - Web UI"
echo "=================================================="
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Node.js is installed
echo "Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed!${NC}"
    echo "Please install Node.js:"
    echo "  - Arch/Manjaro: sudo pacman -S nodejs npm"
    echo "  - Ubuntu/Debian: sudo apt install nodejs npm"
    echo "  - macOS: brew install node"
    exit 1
fi

NODE_VERSION=$(node --version)
echo -e "${GREEN}✓ Node.js ${NODE_VERSION} found${NC}"

# Check if webui directory exists
if [ ! -d "webui" ]; then
    echo -e "${RED}Error: webui directory not found!${NC}"
    exit 1
fi

cd webui

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo ""
    echo -e "${YELLOW}Installing Web UI dependencies...${NC}"
    npm install
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${GREEN}✓ Dependencies found${NC}"
fi

echo ""
echo -e "${YELLOW}NOTE: Make sure the backend API is running!${NC}"
echo "      Start it with: ./start_backend.sh"
echo ""
echo "Web UI will be available at:"
echo "  - http://localhost:5173"
echo ""
echo "Backend API should be running at:"
echo "  - http://localhost:8081"
echo ""
echo "Press Ctrl+C to stop the Web UI"
echo ""

# Start Web UI
npm run dev

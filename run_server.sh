#!/bin/bash
#
# Kottlib Server Startup Script
# Automatically sets up environment, installs dependencies, and starts server
#

set -e  # Exit on error

echo "=================================================="
echo "       Kottlib Server"
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

# Check if Python is installed
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed!${NC}"
    echo "Please install Python 3.8 or later:"
    echo "  - Arch/Manjaro: sudo pacman -S python"
    echo "  - Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "  - macOS: brew install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓ Python ${PYTHON_VERSION} found${NC}"

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo ""
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"

    # Check if python3-venv is available
    if ! python3 -m venv --help &> /dev/null; then
        echo -e "${RED}Error: python3-venv module is not available!${NC}"
        echo "Please install it:"
        echo "  - Arch/Manjaro: sudo pacman -S python"
        echo "  - Ubuntu/Debian: sudo apt install python3-venv"
        exit 1
    fi

    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment found${NC}"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip (use the venv's pip directly)
echo "Checking pip version..."
venv/bin/python -m pip install --upgrade pip --quiet 2>/dev/null || echo "Note: Pip upgrade skipped"

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: requirements.txt not found!${NC}"
    exit 1
fi

# Check and install dependencies
echo "Checking dependencies..."
MISSING_DEPS=0

# Check for key dependencies
for package in fastapi uvicorn pillow; do
    if ! python3 -c "import $package" 2>/dev/null; then
        MISSING_DEPS=1
        break
    fi
done

if [ $MISSING_DEPS -eq 1 ]; then
    echo -e "${YELLOW}Installing/updating dependencies...${NC}"
    venv/bin/pip install -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${GREEN}✓ All dependencies satisfied${NC}"
fi

# Check if config file exists
if [ ! -f "config.yml" ]; then
    if [ -f "config.example.yml" ]; then
        echo ""
        echo -e "${YELLOW}Warning: config.yml not found!${NC}"
        echo "Copying config.example.yml to config.yml..."
        cp config.example.yml config.yml
        echo -e "${GREEN}✓ Config file created${NC}"
        echo ""
        echo -e "${YELLOW}Please edit config.yml with your library paths before starting.${NC}"
        echo "Press Enter to continue or Ctrl+C to exit and edit config first..."
        read
    else
        echo -e "${YELLOW}Warning: No config file found. Server will use defaults.${NC}"
    fi
fi

echo ""
echo "Initializing database..."
python3 src/init_db.py
echo -e "${GREEN}✓ Database initialized${NC}"

echo ""
echo "Starting Kottlib Server..."
echo ""

# Check if Node.js is installed for Web UI
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js ${NODE_VERSION} found${NC}"

    # Check if web UI dependencies are installed
    if [ -d "webui/node_modules" ]; then
        echo -e "${GREEN}✓ Web UI dependencies found${NC}"
    else
        echo -e "${YELLOW}Installing Web UI dependencies...${NC}"
        cd webui
        npm install
        cd ..
        echo -e "${GREEN}✓ Web UI dependencies installed${NC}"
    fi

    # Start Web UI in background
    echo "Starting Web UI frontend..."
    mkdir -p logs
    cd webui
    npm start > ../logs/webui.log 2>&1 &
    WEBUI_PID=$!
    cd ..
    echo -e "${GREEN}✓ Web UI started (PID: $WEBUI_PID)${NC}"

    echo ""
    echo "Servers will be available at:"
    echo "  - Web UI: http://localhost:5173"
    echo "  - API Backend: http://localhost:8081"
    echo "  - API docs: http://localhost:8081/docs"
    echo ""
else
    echo -e "${YELLOW}Warning: Node.js not found. Web UI will not start.${NC}"
    echo "Install Node.js to use the Web UI:"
    echo "  - Arch/Manjaro: sudo pacman -S nodejs npm"
    echo "  - Ubuntu/Debian: sudo apt install nodejs npm"
    echo "  - macOS: brew install node"
    echo ""
    echo "Server will be available at:"
    echo "  - API Backend: http://localhost:8081"
    echo "  - API docs: http://localhost:8081/docs"
    echo ""
fi

echo "Press Ctrl+C to stop the servers"
echo ""

# Cleanup function to kill Web UI when backend stops
cleanup() {
    echo ""
    echo "Stopping servers..."
    if [ ! -z "$WEBUI_PID" ]; then
        kill $WEBUI_PID 2>/dev/null
        echo "Web UI stopped"
    fi
    exit 0
}

trap cleanup INT TERM

# Start backend server (with logging to logs directory)
mkdir -p logs
python3 -m uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port 8081 \
    --log-level info \
    2>&1 | tee logs/server.log

#!/bin/bash
#
# YACLib Enhanced - Start Backend Only
# Starts the FastAPI backend server
#
# Usage: ./start_backend.sh
#

set -e  # Exit on error

echo "=================================================="
echo "       YACLib Enhanced - Backend API"
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

# Upgrade pip
echo "Checking pip version..."
python -m pip install --upgrade pip --quiet

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
    if ! python -c "import $package" 2>/dev/null; then
        MISSING_DEPS=1
        break
    fi
done

if [ $MISSING_DEPS -eq 1 ]; then
    echo -e "${YELLOW}Installing/updating dependencies...${NC}"
    pip install -r requirements.txt
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
python src/init_db.py
echo -e "${GREEN}✓ Database initialized${NC}"

echo ""
echo "Starting Backend API Server..."
echo ""
echo "Server will be available at:"
echo "  - API Backend: http://localhost:8081"
echo "  - API docs: http://localhost:8081/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start backend server (with logging to logs directory)
mkdir -p logs
python -m uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port 8081 \
    --log-level info \
    --workers 4 \
    2>&1 | tee logs/server.log

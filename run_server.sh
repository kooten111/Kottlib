#!/bin/bash
#
# YACLib Enhanced Server Startup Script
#

echo "=================================================="
echo "       YACLib Enhanced Server"
echo "=================================================="
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check dependencies
echo "Checking dependencies..."
if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "Starting YACLib Enhanced Server..."
echo ""
echo "Server will be available at:"
echo "  - http://localhost:8081"
echo "  - API docs: http://localhost:8081/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start server
python -m uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port 8081 \
    --reload \
    --log-level info

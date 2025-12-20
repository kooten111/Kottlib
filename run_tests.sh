#!/bin/bash
# Test runner script for Kottlib

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Print header
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Kottlib - Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}Warning: Virtual environment not activated${NC}"
    echo -e "Attempting to activate venv..."
    if [[ -f "venv/bin/activate" ]]; then
        source venv/bin/activate
        echo -e "${GREEN}✓ Virtual environment activated${NC}"
    else
        echo -e "${RED}✗ Virtual environment not found${NC}"
        echo "Please create it with: python -m venv venv"
        exit 1
    fi
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}pytest not found. Installing...${NC}"
    pip install pytest pytest-asyncio
fi

# Parse command line arguments
TEST_TYPE="${1:-all}"
PYTEST_ARGS="${@:2}"

# Run tests based on type
case "$TEST_TYPE" in
    all)
        echo -e "${GREEN}Running all tests...${NC}"
        pytest -v $PYTEST_ARGS
        ;;
    v1|mobile)
        echo -e "${GREEN}Running v1 API (mobile) tests...${NC}"
        pytest tests/api/test_v1_api.py -v $PYTEST_ARGS
        ;;
    v2|webui)
        echo -e "${GREEN}Running v2 API (webui) tests...${NC}"
        pytest tests/api/test_v2_api.py -v $PYTEST_ARGS
        ;;
    integration|int)
        echo -e "${GREEN}Running integration tests...${NC}"
        pytest tests/api/test_integration.py -v $PYTEST_ARGS
        ;;
    quick)
        echo -e "${GREEN}Running quick test suite (excluding slow tests)...${NC}"
        pytest -v -m "not slow" $PYTEST_ARGS
        ;;
    coverage|cov)
        echo -e "${GREEN}Running tests with coverage report...${NC}"
        if ! command -v pytest-cov &> /dev/null; then
            pip install pytest-cov
        fi
        pytest --cov=src --cov-report=html --cov-report=term -v $PYTEST_ARGS
        echo ""
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    parallel)
        echo -e "${GREEN}Running tests in parallel...${NC}"
        if ! command -v pytest-xdist &> /dev/null; then
            pip install pytest-xdist
        fi
        pytest -n auto -v $PYTEST_ARGS
        ;;
    watch)
        echo -e "${GREEN}Running tests in watch mode...${NC}"
        if ! command -v pytest-watch &> /dev/null; then
            pip install pytest-watch
        fi
        ptw -- -v $PYTEST_ARGS
        ;;
    help|--help|-h)
        echo "Usage: ./run_tests.sh [test_type] [pytest_args]"
        echo ""
        echo "Test Types:"
        echo "  all           - Run all tests (default)"
        echo "  v1, mobile    - Run v1 API (mobile) tests only"
        echo "  v2, webui     - Run v2 API (webui) tests only"
        echo "  integration   - Run integration tests only"
        echo "  quick         - Run quick tests (exclude slow tests)"
        echo "  coverage      - Run with coverage report"
        echo "  parallel      - Run tests in parallel"
        echo "  watch         - Run tests in watch mode"
        echo "  help          - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh                    # Run all tests"
        echo "  ./run_tests.sh v1                 # Run v1 API tests"
        echo "  ./run_tests.sh coverage           # Run with coverage"
        echo "  ./run_tests.sh all -k search      # Run all tests matching 'search'"
        echo "  ./run_tests.sh v2 -vv -s          # Run v2 tests with verbose output"
        exit 0
        ;;
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo "Run './run_tests.sh help' for usage information"
        exit 1
        ;;
esac

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ✓ All tests passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  ✗ Some tests failed${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi

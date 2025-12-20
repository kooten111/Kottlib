#!/bin/bash

#
# Kottlib - Quick Library Scanner
#
# Usage:
#   ./scan.sh /path/to/library            # Quick scan with defaults
#   ./scan.sh /path/to/library --workers 8  # Fast scan with 8 workers
#   ./scan.sh /path/to/library --verbose     # Verbose single-threaded scan
#   ./scan.sh --help                         # Show all options
#

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Forward all arguments to the scanner script
exec python3 "$SCRIPT_DIR/scripts/scan_library.py" "$@"

#!/usr/bin/env python3
"""
Kottlib - Simple launcher wrapper

Just calls ./start.sh
"""

import subprocess
import sys
from pathlib import Path

# Get the script directory
script_dir = Path(__file__).parent.parent

# Call start.sh
start_script = script_dir / "start.sh"
sys.exit(subprocess.call([str(start_script)]))

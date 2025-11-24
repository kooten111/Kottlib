#!/usr/bin/env python3
"""
Test the new progress display
"""

import sys
import time

def progress_callback_simple(current, total, message, series_name=None, filename=None, running_comics=None):
    """Print progress bar with active workers (default mode)"""

    percent = (current / total * 100) if total > 0 else 0

    # Create progress bar
    bar_width = 40
    filled = int(bar_width * current / total) if total > 0 else 0
    bar = '█' * filled + '░' * (bar_width - filled)

    # Calculate lines needed
    worker_lines = len(running_comics) if running_comics else 0
    total_lines = 2 + worker_lines  # Progress bar + blank line + worker lines

    # Move cursor up to overwrite previous output
    if current > 1:  # Don't move up on first iteration
        sys.stdout.write(f'\033[{total_lines}A')  # Move up N lines

    # Clear and print progress bar
    sys.stdout.write(f'\r\033[K  [{bar}] {percent:5.1f}% ({current}/{total})\n')

    # Print active workers
    if running_comics:
        sys.stdout.write('\r\033[K  Active workers:\n')
        for series, fname in running_comics[:8]:  # Limit to 8 workers
            # Truncate for display
            max_series_len = 25
            max_file_len = 45
            if len(series) > max_series_len:
                series = series[:max_series_len-3] + "..."
            if len(fname) > max_file_len:
                fname = fname[:max_file_len-3] + "..."
            sys.stdout.write(f'\r\033[K    └─ {series} / {fname}\n')
    else:
        sys.stdout.write('\r\033[K\n')  # Blank line

    sys.stdout.flush()


# Simulate scanning
print("\nYACLib Enhanced - Scanner Progress Test")
print("=" * 60)
print()

total = 100

for i in range(1, total + 1):
    # Simulate 8 active workers
    running = [
        ("Jojo's Bizarre Adventure", f"Volume_{j:02d}.cbz")
        for j in range(i, min(i + 8, total + 1))
    ]

    progress_callback_simple(i, total, "Processing...", running_comics=running)
    time.sleep(0.05)  # Simulate work

print("\n\nScan complete!")

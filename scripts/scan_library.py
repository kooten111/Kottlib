#!/usr/bin/env python3
"""
Library Scanner

Scans a directory for comic files and adds them to the database.
Supports both single-threaded (verbose) and multi-threaded (fast) modes.
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database import (
    Database,
    get_default_db_path,
    create_library,
    get_library_by_path,
)
from scanner.threaded_scanner import scan_library_threaded


def progress_callback_verbose(current, total, message):
    """Print detailed progress updates (verbose mode)"""
    percent = (current / total * 100) if total > 0 else 0
    print(f"  [{current}/{total}] ({percent:.1f}%) - {message}")


def progress_callback_simple(current, total, message):
    """Print simple progress bar (default mode)"""
    percent = (current / total * 100) if total > 0 else 0
    print(f"\r  Progress: {current}/{total} ({percent:.1f}%)", end='', flush=True)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Scan a comic library and add files to database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fast multi-threaded scan (default: 4 workers)
  python scan_library.py /mnt/Comics

  # Single-threaded verbose mode (good for debugging)
  python scan_library.py /mnt/Comics --workers 1 --verbose

  # Fast scan with 8 workers (good for large libraries)
  python scan_library.py /mnt/Comics --workers 8

  # Custom library name
  python scan_library.py /mnt/Comics --name "My Comics"
        """
    )

    parser.add_argument(
        'library_path',
        type=Path,
        help='Path to comic library directory'
    )

    parser.add_argument(
        '--name',
        type=str,
        default=None,
        help='Library name (default: directory name)'
    )

    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of worker threads (default: 4, use 1 for single-threaded)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed per-file progress (recommended with --workers 1)'
    )

    args = parser.parse_args()

    library_path = args.library_path.resolve()
    library_name = args.name or library_path.name
    max_workers = args.workers
    verbose = args.verbose

    # Validation
    if not library_path.exists():
        print(f"Error: Directory not found: {library_path}")
        return 1

    if not library_path.is_dir():
        print(f"Error: Not a directory: {library_path}")
        return 1

    if max_workers < 1:
        print(f"Error: Workers must be >= 1")
        return 1

    # Header
    mode = "Single-threaded (Verbose)" if max_workers == 1 else f"Multi-threaded ({max_workers} workers)"
    print(f"\nYACLib Enhanced - Library Scanner")
    print(f"=" * 60)
    print(f"Library:  {library_name}")
    print(f"Path:     {library_path}")
    print(f"Mode:     {mode}")
    print(f"=" * 60 + "\n")

    # Initialize database
    db_path = get_default_db_path()
    print(f"Database: {db_path}\n")

    db = Database(db_path)
    db.init_db()

    # Create or get library
    library_id = None
    with db.get_session() as session:
        library = get_library_by_path(session, str(library_path))
        if not library:
            print(f"Creating library...")
            library = create_library(session, library_name, str(library_path))
            library_id = library.id
            print(f"Library created (ID: {library_id})\n")
        else:
            library_id = library.id
            print(f"Library already exists (ID: {library_id})\n")

    # Choose progress callback
    progress_cb = progress_callback_verbose if verbose else progress_callback_simple

    # Scan library
    print(f"Starting scan...\n")

    result = scan_library_threaded(
        db=db,
        library_id=library_id,
        library_path=library_path,
        max_workers=max_workers,
        progress_callback=progress_cb
    )

    print()  # New line after progress

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Scan Complete!")
    print(f"{'=' * 60}")
    print(f"Comics found:        {result.comics_found}")
    print(f"Comics added:        {result.comics_added}")
    print(f"Comics skipped:      {result.comics_skipped} (already in DB)")
    print(f"Folders found:       {result.folders_found}")
    print(f"Thumbnails created:  {result.thumbnails_generated}")
    print(f"Errors:              {result.errors}")
    print(f"Time elapsed:        {result.duration:.2f}s")

    if result.duration > 0 and result.comics_found > 0:
        rate = result.comics_found / result.duration
        print(f"Processing rate:     {rate:.1f} comics/sec")

    print(f"{'=' * 60}\n")

    # Performance tips
    if result.comics_found > 100 and max_workers < 8:
        optimal_workers = min(8, (result.comics_found // 50))
        if max_workers < optimal_workers:
            print(f"Tip: For {result.comics_found} comics, try {optimal_workers} workers for better performance:")
            print(f"     python scan_library.py '{library_path}' --workers {optimal_workers}\n")

    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

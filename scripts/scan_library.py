#!/usr/bin/env python3
"""
Library Scanner

Scans a directory for comic files and adds them to the database.
Supports both single-threaded (verbose) and multi-threaded (fast) modes.
"""

import sys
import argparse
import logging
from pathlib import Path

# Add src and scanners to path
SRC_PATH = Path(__file__).parent.parent / 'src'
SCANNERS_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(SRC_PATH))
sys.path.insert(0, str(SCANNERS_PATH))

from config import load_config
from database import (
    Database,
    create_library,
    get_library_by_path,
)
from database.models import Comic, Library
from scanner.threaded_scanner import scan_library_threaded
from scanner.tool_check import check_tools_and_warn
from src.scanners.scanner_manager import ScannerManager
from src.scanners.base_scanner import ScanResult


def progress_callback_verbose(current, total, message, series_name=None, filename=None, running_comics=None):
    """Print detailed progress updates (verbose mode)"""
    percent = (current / total * 100) if total > 0 else 0

    # In verbose mode, only print when a comic completes (not for active workers update)
    if running_comics is None:
        if series_name and filename:
            print(f"  [{current}/{total}] ({percent:.1f}%) - {series_name} / {filename}")
        else:
            print(f"  [{current}/{total}] ({percent:.1f}%) - {message}")


def progress_callback_simple(current, total, message, series_name=None, filename=None, running_comics=None):
    """Print progress bar with active workers (default mode)"""
    import sys

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


def scan_metadata(
    db: Database,
    library_id: int,
    scanner_name: str,
    scan_new_only: bool = True,
    overwrite: bool = False,
    confidence_threshold: float = 0.4,
    verbose: bool = False
):
    """Scan library for metadata using the specified scanner"""

    # Initialize scanner
    manager = ScannerManager()
    manager.register_scanner('nhentai', NhentaiScanner)

    if scanner_name not in manager.get_available_scanners():
        print(f"Error: Scanner '{scanner_name}' not available")
        print(f"Available scanners: {', '.join(manager.get_available_scanners())}")
        return {
            'total': 0,
            'scanned': 0,
            'failed': 0,
            'skipped': 0
        }

    # Get scanner instance
    scanner_class = manager._available_scanners[scanner_name]
    scanner = scanner_class()

    with db.get_session() as session:
        # Get all comics in library
        query = session.query(Comic).filter(Comic.library_id == library_id)

        # Filter out already scanned if requested
        if scan_new_only:
            query = query.filter(Comic.scanned_at.is_(None))

        comics = query.all()
        total = len(comics)

        if total == 0:
            print("No comics to scan for metadata")
            return {
                'total': 0,
                'scanned': 0,
                'failed': 0,
                'skipped': 0
            }

        print(f"\nScanning {total} comics for metadata using {scanner_name}...")
        print(f"Confidence threshold: {confidence_threshold}")
        print(f"Overwrite existing: {overwrite}")
        print()

        scanned = 0
        failed = 0
        skipped = 0

        for i, comic in enumerate(comics, 1):
            if verbose:
                print(f"[{i}/{total}] Scanning: {comic.filename}")
            else:
                # Progress bar for metadata scanning
                percent = (i / total * 100) if total > 0 else 0
                bar_width = 40
                filled = int(bar_width * i / total) if total > 0 else 0
                bar = '█' * filled + '░' * (bar_width - filled)

                # Truncate filename if too long
                filename = comic.filename
                if len(filename) > 50:
                    filename = filename[:47] + "..."

                print(f"\r  [{bar}] {percent:5.1f}% ({i}/{total}) - {filename}", end='', flush=True)

            try:
                # Scan using filename
                result, _ = scanner.scan(comic.filename)

                if not result:
                    skipped += 1
                    if verbose:
                        print(f"  → No match found")
                    continue

                if result.confidence < confidence_threshold:
                    skipped += 1
                    if verbose:
                        print(f"  → Confidence too low: {result.confidence:.2f}")
                    continue

                # Apply metadata directly
                import time
                fields_updated = []

                # Update basic metadata from result
                if result.metadata.get('title') and (overwrite or not comic.title):
                    comic.title = result.metadata['title']
                    fields_updated.append('title')

                # Store scanner metadata
                comic.scanner_source = scanner_name
                comic.scanner_source_id = result.source_id
                comic.scanner_source_url = result.source_url
                comic.scanned_at = int(time.time())
                comic.scan_confidence = result.confidence

                # Store source URL
                if result.source_url and (overwrite or not comic.web):
                    comic.web = result.source_url
                    fields_updated.append('web')

                # Commit changes
                session.commit()

                scanned += 1
                if verbose:
                    print(f"  → Success! Confidence: {result.confidence:.2f}, Updated {len(fields_updated)} fields")

            except Exception as e:
                failed += 1
                if verbose:
                    print(f"  → Error: {str(e)}")

        if not verbose:
            print()  # New line after progress

    return {
        'total': total,
        'scanned': scanned,
        'failed': failed,
        'skipped': skipped
    }


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

  # Scan files and then fetch metadata with scanner
  python scan_library.py /mnt/Comics --scan-metadata --scanner nhentai

  # Only scan new comics for metadata (skip already scanned)
  python scan_library.py /mnt/Comics --scan-metadata --scanner nhentai --scan-new-only

  # Scan with custom confidence threshold
  python scan_library.py /mnt/Comics --scan-metadata --scanner nhentai --confidence 0.6
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

    parser.add_argument(
        '--db',
        type=Path,
        default=None,
        help='Database path (default: system default location)'
    )

    parser.add_argument(
        '--scan-metadata',
        action='store_true',
        help='Scan for metadata after adding files to database'
    )

    parser.add_argument(
        '--scanner',
        type=str,
        default='nhentai',
        help='Scanner to use for metadata (default: nhentai)'
    )

    parser.add_argument(
        '--scan-new-only',
        action='store_true',
        help='Only scan comics that have not been scanned before (skip comics with existing metadata)'
    )

    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing metadata fields when scanning'
    )

    parser.add_argument(
        '--confidence',
        type=float,
        default=0.4,
        help='Minimum confidence threshold for metadata matches (0.0-1.0, default: 0.4)'
    )

    args = parser.parse_args()

    library_path = args.library_path.resolve()
    library_name = args.name or library_path.name
    max_workers = args.workers
    verbose = args.verbose
    
    # Load config to get database path
    config = load_config()
    db_path = Path(config.database.path) if config.database.path else None

    # Configure logging
    # If verbose, log to console. If not, log to file to avoid breaking progress bar.
    if verbose:
        logging.basicConfig(
            level=logging.INFO,
            format='%(levelname)s: %(message)s',
            force=True
        )
    else:
        # Log to file in logs directory
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / 'scan_library.log'
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filemode='w',
            force=True
        )


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
    if args.scan_metadata:
        print(f"Metadata: {args.scanner} (threshold: {args.confidence})")
    if args.scan_metadata:
        print(f"Metadata: {args.scanner} (threshold: {args.confidence})")
    if not verbose:
        print(f"Logging:  {(Path('logs') / 'scan_library.log').resolve()}")
    print(f"=" * 60 + "\n")

    # Check for external tools
    check_tools_and_warn(verbose=verbose)

    # Initialize database
    if db_path is None and args.db is None:
        # Fallback to default if not in config and not specified
        from database import get_default_db_path
        db_path = get_default_db_path()
    elif args.db is not None:
        # Command line overrides config
        db_path = args.db.resolve()
    else:
        # Use config path
        db_path = db_path.resolve()
        
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
    if result.comics_skipped_unchanged > 0:
        print(f"  - Unchanged:       {result.comics_skipped_unchanged} (fast path)")
    if result.comics_updated > 0:
        print(f"  - Updated:         {result.comics_updated} (moved/renamed)")
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

    # Metadata scanning (if requested)
    if args.scan_metadata:
        print(f"\n{'=' * 60}")
        print(f"Starting Metadata Scan")
        print(f"{'=' * 60}")

        metadata_result = scan_metadata(
            db=db,
            library_id=library_id,
            scanner_name=args.scanner,
            scan_new_only=args.scan_new_only,
            overwrite=args.overwrite,
            confidence_threshold=args.confidence,
            verbose=verbose
        )

        print(f"\n{'=' * 60}")
        print(f"Metadata Scan Complete!")
        print(f"{'=' * 60}")
        print(f"Comics processed:    {metadata_result['total']}")
        print(f"Successfully scanned: {metadata_result['scanned']}")
        print(f"Failed:              {metadata_result['failed']}")
        print(f"Skipped:             {metadata_result['skipped']}")
        print(f"{'=' * 60}\n")

    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

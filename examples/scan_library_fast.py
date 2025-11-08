#!/usr/bin/env python3
"""
Fast Multi-Threaded Library Scanner

Uses parallel processing for significantly faster scanning.
Recommended for large libraries (100+ comics).
"""

import sys
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


def progress_callback(current, total, message):
    """Print progress updates"""
    percent = (current / total * 100) if total > 0 else 0
    print(f"\r  Progress: {current}/{total} ({percent:.1f}%) - {message}", end='', flush=True)


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python scan_library_fast.py <library_path> [library_name] [workers]")
        print("\nExample:")
        print("  python scan_library_fast.py /mnt/Comics 'My Comics' 8")
        print("\nArguments:")
        print("  library_path - Path to comic library")
        print("  library_name - Name for library (default: folder name)")
        print("  workers      - Number of worker threads (default: 4)")
        return

    library_path = Path(sys.argv[1])
    library_name = sys.argv[2] if len(sys.argv) > 2 else library_path.name
    max_workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4

    if not library_path.exists():
        print(f"❌ Directory not found: {library_path}")
        return

    if not library_path.is_dir():
        print(f"❌ Not a directory: {library_path}")
        return

    print(f"\nYACLib Enhanced - Fast Multi-Threaded Scanner")
    print(f"="*60)
    print(f"Library: {library_name}")
    print(f"Path: {library_path}")
    print(f"Workers: {max_workers} threads")
    print(f"="*60 + "\n")

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
            print(f"✅ Library created (ID: {library_id})\n")
        else:
            library_id = library.id
            print(f"ℹ️  Library already exists (ID: {library_id})\n")

    # Scan library with threading
    print(f"Starting multi-threaded scan...\n")

    result = scan_library_threaded(
        db=db,
        library_id=library_id,
        library_path=library_path,
        max_workers=max_workers,
        progress_callback=progress_callback
    )

    print()  # New line after progress

    # Summary
    print(f"\n{'='*60}")
    print(f"Scan Complete!")
    print(f"{'='*60}")
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

    print(f"{'='*60}\n")

    # Performance tips
    if result.comics_found > 100:
        optimal_workers = min(8, (result.comics_found // 50))
        if max_workers < optimal_workers:
            print(f"💡 Tip: For {result.comics_found} comics, try {optimal_workers} workers for better performance")
            print(f"   python scan_library_fast.py '{library_path}' '{library_name}' {optimal_workers}\n")

    db.close()


if __name__ == "__main__":
    main()
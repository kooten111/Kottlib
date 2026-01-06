#!/usr/bin/env python3
"""
Regenerate missing cover thumbnails for a library

Uses the centralized cover_service for cover regeneration.
"""

import sys
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database import (
    Database,
    get_library_by_id,
    get_comics_in_library,
)
from services.cover_service import regenerate_cover_for_comic

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def regenerate_cover(comic, library_name, force=False):
    """Regenerate cover for a single comic using centralized service"""
    db = Database()
    with db.get_session() as session:
        return regenerate_cover_for_comic(
            session=session,
            comic=comic,
            library_name=library_name,
            force=force
        )


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python regenerate_covers.py <library_id> [--force] [--workers N]")
        print("\nOptions:")
        print("  --force      Regenerate all covers, even if they already exist")
        print("  --workers N  Number of parallel workers (default: 4)")
        print("\nExample:")
        print("  python regenerate_covers.py 2")
        print("  python regenerate_covers.py 2 --force --workers 8")
        sys.exit(1)

    library_id = int(sys.argv[1])
    force = '--force' in sys.argv

    # Get number of workers
    workers = 4
    if '--workers' in sys.argv:
        idx = sys.argv.index('--workers')
        if idx + 1 < len(sys.argv):
            workers = int(sys.argv[idx + 1])

    db = Database()

    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        if not library:
            print(f"Error: Library {library_id} not found")
            sys.exit(1)

        print(f"\n{'='*60}")
        print(f"Regenerating Covers for Library: {library.name}")
        print(f"{'='*60}")
        print(f"Library ID: {library_id}")
        print(f"Path: {library.path}")
        print(f"Workers: {workers}")
        print(f"Force: {force}")
        print(f"{'='*60}\n")

        # Get all comics
        comics = get_comics_in_library(session, library_id)
        total = len(comics)

        if total == 0:
            print("No comics found in library")
            sys.exit(0)

        print(f"Found {total} comics\n")

    # Process comics in parallel
    results = {
        'success': 0,
        'skipped': 0,
        'failed': 0,
        'error': 0
    }
    failed_comics = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(regenerate_cover, comic, library.name, force): comic
            for comic in comics
        }

        # Process completed tasks
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            status = result['status']
            results[status] += 1

            if status in ['failed', 'error']:
                failed_comics.append(result)

            # Progress
            percent = (i / total * 100)
            print(f"\rProgress: {i}/{total} ({percent:.1f}%) - Success: {results['success']}, Skipped: {results['skipped']}, Failed: {results['failed'] + results['error']}", end='', flush=True)

    print("\n")

    # Summary
    print(f"{'='*60}")
    print(f"Cover Generation Complete")
    print(f"{'='*60}")
    print(f"Total comics:     {total}")
    print(f"Success:          {results['success']}")
    print(f"Skipped:          {results['skipped']} (already exist)")
    print(f"Failed:           {results['failed']}")
    print(f"Errors:           {results['error']}")
    print(f"{'='*60}\n")

    # Show failed comics
    if failed_comics:
        print(f"\nFailed Comics ({len(failed_comics)}):")
        print(f"{'='*60}")
        for result in failed_comics[:20]:  # Show first 20
            print(f"  ID {result['comic_id']}: {result['filename']}")
            if 'error' in result:
                print(f"    Error: {result['error']}")
        if len(failed_comics) > 20:
            print(f"  ... and {len(failed_comics) - 20} more")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Diagnostic script to identify missing covers and comics
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database.database import Database, get_library_by_id, get_comic_by_id, get_comics_in_library, get_covers_dir
from database.models import Cover

def diagnose_library(library_id: int):
    """Diagnose missing data for a library"""

    db = Database()

    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        if not library:
            print(f"❌ Library {library_id} not found")
            return

        print(f"\n📚 Library: {library.name} (ID: {library_id})")
        print(f"   Path: {library.path}")
        print(f"   Scan Status: {library.scan_status}")
        print(f"   Last Scan: {library.last_scan_at}")

        # Get all comics
        comics = get_comics_in_library(session, library_id)
        print(f"\n📖 Total Comics: {len(comics)}")

        # Check for missing covers
        covers_dir = get_covers_dir(library.name)
        print(f"\n📁 Covers Directory: {covers_dir}")
        print(f"   Exists: {covers_dir.exists()}")

        missing_covers = []
        missing_files = []

        for comic in comics:
            # Check if comic file exists
            comic_path = Path(comic.path)
            if not comic_path.exists():
                missing_files.append(comic)

            # Check if cover exists
            cover = session.query(Cover).filter_by(comic_id=comic.id, type='auto').first()
            if not cover:
                missing_covers.append(comic)
            else:
                # Check if cover file exists
                cover_path = Path(cover.jpeg_path)
                if not cover_path.exists():
                    missing_covers.append(comic)

        print(f"\n⚠️  Comics with missing files: {len(missing_files)}")
        if missing_files:
            print("   First 5 missing files:")
            for comic in missing_files[:5]:
                print(f"   - ID {comic.id}: {comic.filename}")
                print(f"     Path: {comic.path}")

        print(f"\n⚠️  Comics with missing covers: {len(missing_covers)}")
        if missing_covers:
            print("   First 10 missing covers:")
            for comic in missing_covers[:10]:
                print(f"   - ID {comic.id}: {comic.filename}")
                print(f"     Hash: {comic.hash}")

        # Check specific comic ID if it exists
        if len(sys.argv) > 2:
            comic_id = int(sys.argv[2])
            comic = get_comic_by_id(session, comic_id)
            if comic:
                print(f"\n🔍 Comic {comic_id} exists:")
                print(f"   Filename: {comic.filename}")
                print(f"   Path: {comic.path}")
                print(f"   Library ID: {comic.library_id}")
                print(f"   File exists: {Path(comic.path).exists()}")
            else:
                print(f"\n❌ Comic {comic_id} NOT found in database")

        # Check cache status
        if library.cached_series_tree:
            print(f"\n✅ Series tree cache exists (updated: {library.tree_cache_updated_at})")
        else:
            print(f"\n⚠️  Series tree cache missing")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python diagnose_missing_data.py <library_id> [comic_id]")
        print("\nExample:")
        print("  python diagnose_missing_data.py 2")
        print("  python diagnose_missing_data.py 2 4157")
        sys.exit(1)

    library_id = int(sys.argv[1])
    diagnose_library(library_id)

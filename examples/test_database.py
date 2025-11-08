#!/usr/bin/env python3
"""
Test Database Layer

Demonstrates database operations: creating libraries, adding comics, etc.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database import (
    Database,
    get_default_db_path,
    create_library,
    get_library_by_path,
    get_all_libraries,
    create_comic,
    get_comic_by_hash,
    get_comics_in_library,
    get_library_stats,
)


def main():
    """Main function"""
    print("YACLib Enhanced - Database Test\n")

    # Get database path
    db_path = get_default_db_path()
    print(f"Database location: {db_path}")
    print(f"Database exists: {db_path.exists()}\n")

    # Initialize database
    db = Database(db_path)
    print("Initializing database...")
    db.init_db()
    print("✅ Database initialized\n")

    # Test library operations
    print("="*60)
    print("TESTING LIBRARY OPERATIONS")
    print("="*60 + "\n")

    # Store library ID for later use
    library_id = None

    with db.get_session() as session:
        # Create a test library (or get existing)
        existing = get_library_by_path(session, "/tmp/test_comics")
        if existing:
            print("Test library already exists, using it...")
            library_id = existing.id
            library_name = existing.name
            print(f"✅ Using library: {library_name} (ID: {library_id})\n")
        else:
            print("Creating test library...")
            library = create_library(
                session,
                name="Test Comics",
                path="/tmp/test_comics",
                settings={"sort_mode": "folders_first"}
            )
            library_id = library.id  # Save ID before session closes
            library_name = library.name
            print(f"✅ Created library: {library_name} (ID: {library_id})\n")

        # List all libraries
        print("Listing all libraries:")
        libraries = get_all_libraries(session)
        for lib in libraries:
            print(f"  • {lib.name} - {lib.path}")
        print()

        # Get library stats
        print("Library statistics:")
        stats = get_library_stats(session, library_id)
        print(f"  Comics: {stats['comic_count']}")
        print(f"  Folders: {stats['folder_count']}")
        print()

    # Test comic operations
    print("="*60)
    print("TESTING COMIC OPERATIONS")
    print("="*60 + "\n")

    with db.get_session() as session:
        # Add a test comic (or get existing)
        test_hash = "abc123"
        existing_comic = get_comic_by_hash(session, test_hash)

        if existing_comic:
            print("Test comic already exists, using it...")
            comic = existing_comic
            print(f"✅ Using comic: {comic.filename} (ID: {comic.id})\n")
        else:
            print("Adding test comic...")
            comic = create_comic(
                session,
                library_id=library_id,
                path="/tmp/test_comics/test.cbz",
                filename="test.cbz",
                file_hash=test_hash,
                file_size=1024000,
                file_modified_at=int(time.time()),
                format="cbz",
                num_pages=24,
                title="Test Comic #1",
                series="Test Series",
                issue_number=1,
            )
            print(f"✅ Created comic: {comic.filename} (ID: {comic.id})\n")

        # List comics in library
        print("Comics in library:")
        comics = get_comics_in_library(session, library_id)
        for c in comics:
            print(f"  • {c.filename} - {c.num_pages} pages")
        print()

        # Update library stats
        stats = get_library_stats(session, library_id)
        print("Updated library statistics:")
        print(f"  Comics: {stats['comic_count']}")
        print(f"  Folders: {stats['folder_count']}")
        print()

    print("="*60)
    print("✅ All tests completed successfully!")
    print("="*60)

    # Close database
    db.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Library Scanner

Scans a directory for comic files and adds them to the database.
Generates thumbnails for all comics found.
"""

import sys
import hashlib
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database import (
    Database,
    get_default_db_path,
    get_covers_dir,
    create_library,
    get_library_by_path,
    create_comic,
    get_comic_by_hash,
    create_folder,
    get_folder_by_path,
)
from scanner import open_comic, is_comic_file
from scanner.thumbnail_generator import (
    calculate_file_hash,
    generate_dual_thumbnails,
    thumbnail_exists,
)


def scan_directory(library_path: Path, library_id: int, session, db_folder_id=None):
    """
    Recursively scan directory for comics

    Args:
        library_path: Root library path
        library_id: Library database ID
        session: Database session
        db_folder_id: Parent folder ID (for recursion)
    """
    comics_found = 0
    folders_found = 0

    for item in library_path.iterdir():
        # Skip hidden files and directories
        if item.name.startswith('.'):
            continue

        if item.is_dir():
            # Create folder in database
            folder = get_folder_by_path(session, library_id, str(item))
            if not folder:
                folder = create_folder(
                    session,
                    library_id=library_id,
                    path=str(item),
                    name=item.name,
                    parent_id=db_folder_id
                )
                print(f"📁 {item.name}/")
                folders_found += 1

            # Recursively scan subfolder
            sub_comics, sub_folders = scan_directory(
                item,
                library_id,
                session,
                db_folder_id=folder.id
            )
            comics_found += sub_comics
            folders_found += sub_folders

        elif item.is_file() and is_comic_file(item):
            # Process comic file
            process_comic(item, library_id, session, db_folder_id)
            comics_found += 1

    return comics_found, folders_found


def process_comic(file_path: Path, library_id: int, session, folder_id=None):
    """Process a single comic file"""
    print(f"  📖 {file_path.name}")

    # Calculate hash
    file_hash = calculate_file_hash(file_path)

    # Check if already in database
    existing = get_comic_by_hash(session, file_hash)
    if existing:
        print(f"     ℹ️  Already in database (skipping)")
        return

    # Open comic to get metadata
    with open_comic(file_path) as comic:
        if comic is None:
            print(f"     ❌ Failed to open comic")
            return

        # Extract metadata
        metadata = {}
        if comic.comic_info:
            info = comic.comic_info
            if info.title:
                metadata['title'] = info.title
            if info.series:
                metadata['series'] = info.series
            if info.number:
                try:
                    metadata['issue_number'] = float(info.number)
                except ValueError:
                    pass
            if info.year:
                metadata['year'] = info.year
            if info.publisher:
                metadata['publisher'] = info.publisher
            if info.writer:
                metadata['writer'] = info.writer
            if info.manga:
                metadata['reading_direction'] = 'rtl' if info.manga else 'ltr'

        # Add to database
        db_comic = create_comic(
            session,
            library_id=library_id,
            folder_id=folder_id,
            path=str(file_path),
            filename=file_path.name,
            file_hash=file_hash,
            file_size=file_path.stat().st_size,
            file_modified_at=int(file_path.stat().st_mtime),
            format=file_path.suffix[1:].lower(),  # Remove leading dot
            num_pages=comic.page_count,
            **metadata
        )

        print(f"     ✅ Added to database (ID: {db_comic.id})")

        # Generate thumbnails
        covers_dir = get_covers_dir()
        if not thumbnail_exists(covers_dir, file_hash):
            print(f"     🖼️  Generating thumbnails...")

            # Get cover image
            cover_image = comic.extract_page_as_image(0)
            if cover_image:
                jpeg_ok, webp_ok = generate_dual_thumbnails(
                    cover_image,
                    covers_dir,
                    file_hash
                )

                if jpeg_ok and webp_ok:
                    print(f"     ✅ Thumbnails generated (JPEG + WebP)")
                elif jpeg_ok:
                    print(f"     ⚠️  JPEG generated, WebP failed")
                else:
                    print(f"     ❌ Thumbnail generation failed")
            else:
                print(f"     ❌ Failed to extract cover image")
        else:
            print(f"     ℹ️  Thumbnails already exist")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python scan_library.py <library_path> [library_name]")
        print("\nExample:")
        print("  python scan_library.py /mnt/Comics 'My Comics'")
        return

    library_path = Path(sys.argv[1])
    library_name = sys.argv[2] if len(sys.argv) > 2 else library_path.name

    if not library_path.exists():
        print(f"❌ Directory not found: {library_path}")
        return

    if not library_path.is_dir():
        print(f"❌ Not a directory: {library_path}")
        return

    print(f"\nYACLib Enhanced - Library Scanner")
    print(f"="*60)
    print(f"Library: {library_name}")
    print(f"Path: {library_path}")
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
            library_id = library.id  # Save ID before session closes
            print(f"✅ Library created (ID: {library_id})\n")
        else:
            library_id = library.id  # Save ID before session closes
            print(f"ℹ️  Library already exists (ID: {library_id})\n")

    # Scan directory
    print(f"Scanning directory...\n")
    start_time = time.time()

    with db.get_session() as session:
        comics_found, folders_found = scan_directory(
            library_path,
            library_id,
            session
        )

    elapsed = time.time() - start_time

    # Summary
    print(f"\n{'='*60}")
    print(f"Scan Complete!")
    print(f"{'='*60}")
    print(f"Comics found: {comics_found}")
    print(f"Folders found: {folders_found}")
    print(f"Time elapsed: {elapsed:.2f}s")
    print(f"{'='*60}\n")

    db.close()


if __name__ == "__main__":
    main()

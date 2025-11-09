#!/usr/bin/env python3
"""
Test script to verify folder API responses
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from database import Database, get_default_db_path, get_library_by_id, get_folders_in_library, get_comics_in_folder
from database.models import Comic

def test_folder_response(library_id: int, folder_id: int):
    """Simulate what the API would return for a folder request"""
    db = Database(get_default_db_path())

    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        if not library:
            print(f"ERROR: Library {library_id} not found")
            return

        print(f"\n{'='*80}")
        print(f"Testing: GET /v2/library/{library_id}/folder/{folder_id}")
        print(f"Library: {library.name} (ID: {library_id})")
        print(f"Folder ID: {folder_id}")
        print(f"{'='*80}\n")

        # Get folders
        all_folders = get_folders_in_library(session, library_id)
        print(f"Total folders in library: {len(all_folders)}")

        child_folders = []
        for folder in all_folders:
            if folder_id == 0:
                if folder.parent_id is not None:
                    continue
            else:
                if folder.parent_id != folder_id:
                    continue
            child_folders.append(folder)

        print(f"\nFolders to return ({len(child_folders)}):")
        for folder in child_folders:
            print(f"  - {folder.name} (ID: {folder.id}, parent: {folder.parent_id})")

        # Get comics
        if folder_id == 0:
            comics = session.query(Comic).filter_by(library_id=library_id, folder_id=None).all()
        else:
            comics = get_comics_in_folder(session, folder_id, library_id=library_id)

        print(f"\nComics to return ({len(comics)}):")
        for comic in comics:
            print(f"  - {comic.filename} (ID: {comic.id}, folder: {comic.folder_id})")

        print(f"\nTotal items: {len(child_folders) + len(comics)}")
        print(f"  Folders: {len(child_folders)}")
        print(f"  Comics: {len(comics)}")
        print()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test folder API responses')
    parser.add_argument('library_id', type=int, help='Library ID')
    parser.add_argument('folder_id', type=int, help='Folder ID')

    args = parser.parse_args()

    test_folder_response(args.library_id, args.folder_id)

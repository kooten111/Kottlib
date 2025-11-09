#!/usr/bin/env python3
"""
Debug script to check folder relationships
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import Database, get_default_db_path, get_all_libraries, get_folders_in_library

def main():
    db_path = get_default_db_path()
    print(f"Database: {db_path}")

    if not Path(db_path).exists():
        print("ERROR: Database not found!")
        print("Please run the scanner first to create the database.")
        return

    db = Database(db_path)

    with db.get_session() as session:
        # Get all libraries
        libraries = get_all_libraries(session)

        for library in libraries:
            print(f"\n{'='*80}")
            print(f"Library: {library.name} (ID: {library.id})")
            print(f"Path: {library.path}")
            print(f"{'='*80}")

            # Get all folders in this library
            folders = get_folders_in_library(session, library.id)

            if not folders:
                print("  No folders found")
                continue

            # Build folder tree
            folder_dict = {f.id: f for f in folders}

            print(f"\nTotal folders: {len(folders)}\n")

            # Check for issues
            issues_found = False

            for folder in folders:
                # Check for self-reference
                if folder.parent_id == folder.id:
                    print(f"❌ ISSUE: Folder {folder.id} '{folder.name}' references itself as parent!")
                    issues_found = True

                # Check for invalid parent
                if folder.parent_id is not None and folder.parent_id not in folder_dict:
                    print(f"❌ ISSUE: Folder {folder.id} '{folder.name}' has invalid parent_id={folder.parent_id}")
                    issues_found = True

                # Print folder info
                parent_name = "ROOT" if folder.parent_id is None else folder_dict.get(folder.parent_id, "???").name if folder.parent_id in folder_dict else "MISSING"

                print(f"  Folder {folder.id:3d}: {folder.name:30s} | Parent: {str(folder.parent_id):>4s} ({parent_name})")

                # Check for circular references
                visited = set()
                current = folder
                depth = 0
                max_depth = 100

                while current.parent_id is not None and depth < max_depth:
                    if current.id in visited:
                        print(f"    ❌ CIRCULAR REFERENCE DETECTED! Path: {' -> '.join(str(x) for x in visited)} -> {current.id}")
                        issues_found = True
                        break
                    visited.add(current.id)
                    if current.parent_id not in folder_dict:
                        break
                    current = folder_dict[current.parent_id]
                    depth += 1

                if depth >= max_depth:
                    print(f"    ❌ DEPTH LIMIT EXCEEDED! Possible infinite loop.")
                    issues_found = True

            if not issues_found:
                print(f"\n✅ No folder relationship issues found in '{library.name}'")
            else:
                print(f"\n❌ Issues found in '{library.name}'!")

    db.close()

if __name__ == "__main__":
    main()

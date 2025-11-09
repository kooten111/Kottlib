#!/usr/bin/env python3
"""
Migration script to update existing database to YACReader schema

This script:
1. Creates root folders (ID=1 preferred) for each library
2. Updates top-level folders to have parent_id pointing to root folder
3. Updates root-level comics to have folder_id pointing to root folder
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from database import Database, get_default_db_path, get_all_libraries
from database.models import Folder, Comic

def migrate_database():
    """Migrate database to YACReader-compatible schema"""

    db_path = get_default_db_path()
    print(f"Database: {db_path}")
    print()

    db = Database(db_path)

    with db.get_session() as session:
        libraries = get_all_libraries(session)

        for library in libraries:
            print(f"{'='*80}")
            print(f"Migrating Library: {library.name} (ID: {library.id})")
            print(f"{'='*80}")

            # Step 1: Get or create root folder
            root_folder = session.query(Folder).filter_by(
                library_id=library.id,
                name="__ROOT__"
            ).first()

            if not root_folder:
                # Create root folder
                root_folder = Folder(
                    library_id=library.id,
                    parent_id=None,
                    path=library.path,
                    name="__ROOT__",
                    created_at=0,
                    updated_at=0
                )
                session.add(root_folder)
                session.flush()
                print(f"✓ Created root folder with ID={root_folder.id}")
            else:
                print(f"✓ Root folder already exists with ID={root_folder.id}")

            # Step 2: Update top-level folders to have parent_id=root_folder.id
            top_level_folders = session.query(Folder).filter(
                Folder.library_id == library.id,
                Folder.parent_id == None,
                Folder.id != root_folder.id  # Don't update root itself
            ).all()

            if top_level_folders:
                print(f"\nUpdating {len(top_level_folders)} top-level folders:")
                for folder in top_level_folders:
                    folder.parent_id = root_folder.id
                    print(f"  - {folder.name} (ID={folder.id}) → parent_id={root_folder.id}")
            else:
                print(f"\n✓ All folders already have correct parent_id")

            # Step 3: Update root-level comics to have folder_id=root_folder.id
            root_comics = session.query(Comic).filter(
                Comic.library_id == library.id,
                Comic.folder_id == None
            ).all()

            if root_comics:
                print(f"\nUpdating {len(root_comics)} root-level comics:")
                for comic in root_comics:
                    comic.folder_id = root_folder.id
                    print(f"  - {comic.filename[:60]} → folder_id={root_folder.id}")
            else:
                print(f"\n✓ All comics already have folder assignments")

            session.commit()
            print(f"\n✅ Migration complete for {library.name}\n")

    db.close()
    print("="*80)
    print("Database migration complete!")
    print("="*80)

if __name__ == "__main__":
    migrate_database()

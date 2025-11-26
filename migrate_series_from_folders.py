#!/usr/bin/env python3
"""
Migrate Series Names from Folder Structure

This script updates comics that have NULL series values by extracting
the series name from their folder structure (top-level folder).
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import get_library_database
from src.database.models import Comic
from sqlalchemy import text

def migrate_library_series(library_name: str):
    """Migrate series names for a library from folder structure"""

    print(f"\n{'='*70}")
    print(f"Migrating series names for library: {library_name}")
    print(f"{'='*70}\n")

    lib_db = get_library_database(library_name)

    with lib_db.get_session() as session:
        # Count comics with NULL series
        null_count = session.execute(
            text("SELECT COUNT(*) FROM comics WHERE series IS NULL")
        ).scalar()

        print(f"Comics with NULL series: {null_count}")

        if null_count == 0:
            print("✅ All comics already have series values!")
            return

        # Get all comics with NULL series
        # For comics with folder_id, use folder name
        # For comics without folder, extract from path
        query = text("""
            SELECT
                c.id as comic_id,
                c.filename,
                c.path,
                COALESCE(f.name, '') as folder_name
            FROM comics c
            LEFT JOIN folders f ON c.folder_id = f.id
            WHERE c.series IS NULL
        """)

        results = session.execute(query).fetchall()

        print(f"\nUpdating {len(results)} comics...\n")

        updated = 0
        for comic_id, filename, path, folder_name in results:
            # Determine series name
            if folder_name:
                # Has folder_id - use folder name
                series_name = folder_name
            else:
                # No folder_id - extract from path
                # Example: /mnt/Blue/Ebooks_Comics/Manga/67% Inertia/file.cbz
                # -> Series = "67% Inertia"
                from pathlib import Path
                path_obj = Path(path)
                parent_dir = path_obj.parent.name

                # Skip if parent is the library root (Manga, Comics, Webtoon)
                if parent_dir in ["Manga", "Comics", "Webtoon"]:
                    # File is directly in library root, use filename
                    series_name = path_obj.stem  # filename without extension
                else:
                    # Use parent directory name
                    series_name = parent_dir

            # Update the series field
            session.execute(
                text("UPDATE comics SET series = :series WHERE id = :id"),
                {"series": series_name, "id": comic_id}
            )
            updated += 1

            if updated % 100 == 0:
                print(f"  Updated {updated}/{len(results)} comics...")

        session.commit()

        print(f"\n✅ Successfully updated {updated} comics!")
        print(f"   Set series = immediate parent folder name\n")

        # Show sample of updated series
        sample = session.execute(
            text("""
                SELECT series, COUNT(*) as count
                FROM comics
                WHERE series IS NOT NULL
                GROUP BY series
                ORDER BY count DESC
                LIMIT 10
            """)
        ).fetchall()

        print("Top 10 series by volume count:")
        for series, count in sample:
            print(f"  • {series}: {count} volumes")

def main():
    """Main function"""
    libraries = ["Comics", "Manga", "Webtoon"]

    for lib_name in libraries:
        try:
            migrate_library_series(lib_name)
        except Exception as e:
            print(f"❌ Error processing {lib_name}: {e}")
            continue

    print(f"\n{'='*70}")
    print("Migration complete!")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()

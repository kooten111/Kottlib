#!/usr/bin/env python3
"""
Rebuild Series Table from Comics

This script rebuilds the series table by grouping existing comics
by their normalized_series_name field.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from database import Database, get_default_db_path
from database.models import Comic, Series, Library
from sqlalchemy import func
import time

def rebuild_series_for_library(db: Database, library_id: int):
    """Rebuild series table for a specific library"""

    with db.get_session() as session:
        library = session.query(Library).filter_by(id=library_id).first()
        if not library:
            print(f"Library {library_id} not found")
            return 0

        print(f"Rebuilding series for library: {library.name} (ID: {library_id})")

        # Get all unique series names with comic counts
        series_data = session.query(
            Comic.normalized_series_name,
            func.count(Comic.id).label('comic_count')
        ).filter(
            Comic.library_id == library_id,
            Comic.normalized_series_name.isnot(None)
        ).group_by(
            Comic.normalized_series_name
        ).all()

        if not series_data:
            print("  No comics with series names found")
            return 0

        print(f"  Found {len(series_data)} unique series")

        created = 0
        now = int(time.time())

        for series_name, comic_count in series_data:
            if not series_name:
                continue

            # Check if series already exists
            existing = session.query(Series).filter(
                Series.library_id == library_id,
                Series.name == series_name
            ).first()

            if existing:
                # Update comic count
                existing.comic_count = comic_count
                existing.updated_at = now
                print(f"  Updated: {series_name} ({comic_count} comics)")
            else:
                # Create new series
                new_series = Series(
                    library_id=library_id,
                    name=series_name,
                    display_name=series_name,
                    comic_count=comic_count,
                    total_issues=comic_count,
                    created_at=now,
                    updated_at=now
                )
                session.add(new_series)
                created += 1
                print(f"  Created: {series_name} ({comic_count} comics)")

        session.commit()
        print(f"  Done! Created {created} new series")
        return created

def main():
    """Main function"""
    db_path = get_default_db_path()
    print(f"Using database: {db_path}\n")

    db = Database(db_path)

    with db.get_session() as session:
        libraries = session.query(Library).all()

        if not libraries:
            print("No libraries found")
            return 1

        print(f"Found {len(libraries)} libraries:\n")

        total_created = 0
        for library in libraries:
            created = rebuild_series_for_library(db, library.id)
            total_created += created
            print()

        print(f"\nTotal series created: {total_created}")

    db.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())

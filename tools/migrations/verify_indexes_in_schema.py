#!/usr/bin/env python3
"""
Verify Performance Indexes in Schema

This script verifies that all performance indexes are properly defined
in the SQLAlchemy models and will be created automatically for new databases.
"""

import sys
from pathlib import Path

# Add src to path so we can import the models
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from database.models import (
    Comic, ReadingProgress, Series, Folder, Collection, Favorite
)

# Expected indexes for each model
EXPECTED_INDEXES = {
    'comics': [
        'idx_comics_title',
        'idx_comics_publisher',
        'idx_comics_year',
        'idx_comics_filename',
        'idx_comics_library_series',
        'idx_comics_library_folder',
        'idx_comics_file_modified',
        'idx_comics_library_count',
    ],
    'reading_progress': [
        'idx_reading_progress_continue',
        'idx_reading_progress_completed',
        'idx_reading_progress_percent',
    ],
    'series': [
        'idx_series_library_name',
        'idx_series_year_start',
    ],
    'folders': [
        'idx_folders_library_path',
        'idx_folders_name',
    ],
    'collections': [
        'idx_collections_user_position',
    ],
    'favorites': [
        'idx_favorites_user_created',
    ],
}


def extract_index_names(model):
    """Extract index names from a model's __table_args__"""
    if not hasattr(model, '__table_args__'):
        return []

    index_names = []
    table_args = model.__table_args__

    if isinstance(table_args, tuple):
        from sqlalchemy import Index
        for arg in table_args:
            if isinstance(arg, Index):
                index_names.append(arg.name)

    return index_names


def main():
    print("=" * 70)
    print("  Performance Indexes Verification")
    print("=" * 70)
    print()

    models = {
        'comics': Comic,
        'reading_progress': ReadingProgress,
        'series': Series,
        'folders': Folder,
        'collections': Collection,
        'favorites': Favorite,
    }

    all_ok = True
    total_expected = 0
    total_found = 0

    for table_name, model in models.items():
        expected = EXPECTED_INDEXES.get(table_name, [])
        found = extract_index_names(model)

        # Filter to only performance indexes
        performance_indexes = [idx for idx in found if idx in expected]

        print(f"📋 {table_name.upper()}")
        print(f"   Expected: {len(expected)} performance indexes")
        print(f"   Found: {len(performance_indexes)} performance indexes")

        missing = set(expected) - set(performance_indexes)

        if missing:
            print(f"   ❌ Missing: {len(missing)}")
            for idx in sorted(missing):
                print(f"      • {idx}")
            all_ok = False
        else:
            print(f"   ✅ All performance indexes defined")

        print()

        total_expected += len(expected)
        total_found += len(performance_indexes)

    print("=" * 70)
    print("  Summary")
    print("=" * 70)
    print(f"Total expected: {total_expected}")
    print(f"Total found: {total_found}")

    if all_ok:
        print()
        print("✅ All performance indexes are properly defined in the models!")
        print("   New databases will automatically include these indexes.")
        return 0
    else:
        print()
        print("❌ Some performance indexes are missing from the models.")
        print("   Please add them to src/database/models.py")
        return 1


if __name__ == '__main__':
    sys.exit(main())

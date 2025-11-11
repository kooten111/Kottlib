#!/usr/bin/env python3
"""
Apply Series Tree Cache Migration

This script adds cache fields to the libraries table to speed up
series tree loading by pre-computing and storing the tree structure.

Usage:
    python apply_cache_migration.py [--db-path /path/to/yaclib.db]
"""

import sqlite3
import sys
import argparse
from pathlib import Path
import platform
import time


def get_default_db_path():
    """Get the default database path based on platform."""
    system = platform.system()

    if system == "Linux":
        return Path.home() / ".local/share/yaclib/yaclib.db"
    elif system == "Darwin":  # macOS
        return Path.home() / "Library/Application Support/YACLib/yaclib.db"
    elif system == "Windows":
        import os
        return Path(os.getenv("APPDATA")) / "YACLib/yaclib.db"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


def check_column_exists(conn, table, column):
    """Check if a column exists in a table."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def apply_migration(db_path, dry_run=False):
    """Apply the cache migration."""

    print(f"\n{'='*70}")
    print(f"  YACLib Series Tree Cache Migration")
    print(f"{'='*70}\n")

    if not db_path.exists():
        print(f"ERROR: Database not found at: {db_path}")
        return False

    print(f"Database: {db_path}")
    print(f"Database size: {db_path.stat().st_size / 1024 / 1024:.2f} MB\n")

    if dry_run:
        print("DRY RUN MODE - No changes will be made\n")

    try:
        with sqlite3.connect(db_path) as conn:
            # Check if columns already exist
            has_tree_cache = check_column_exists(conn, 'libraries', 'cached_series_tree')
            has_updated_at = check_column_exists(conn, 'libraries', 'tree_cache_updated_at')

            if has_tree_cache and has_updated_at:
                print("SUCCESS: Migration already applied - cache columns exist")
                return True

            if dry_run:
                print("Would add the following columns to 'libraries' table:")
                if not has_tree_cache:
                    print("  - cached_series_tree (TEXT)")
                if not has_updated_at:
                    print("  - tree_cache_updated_at (INTEGER)")
                print("\nDry run completed - no changes made")
                return True

            # Create backup
            backup_path = db_path.with_suffix('.db.backup')
            print(f"Creating backup: {backup_path}")
            import shutil
            try:
                shutil.copy2(db_path, backup_path)
                print(f"Backup created successfully\n")
            except Exception as e:
                print(f"WARNING: Could not create backup: {e}\n")

            # Apply migration
            print("Applying migration...")
            cursor = conn.cursor()

            changes_made = 0

            if not has_tree_cache:
                print("  - Adding cached_series_tree column...")
                cursor.execute("ALTER TABLE libraries ADD COLUMN cached_series_tree TEXT")
                changes_made += 1

            if not has_updated_at:
                print("  - Adding tree_cache_updated_at column...")
                cursor.execute("ALTER TABLE libraries ADD COLUMN tree_cache_updated_at INTEGER")
                changes_made += 1

            # Create index
            print("  - Creating index on tree_cache_updated_at...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_libraries_cache_updated
                ON libraries(tree_cache_updated_at)
            """)

            conn.commit()

            print(f"\n{'='*70}")
            print(f"  Migration Summary")
            print(f"{'='*70}")
            print(f"Columns added: {changes_made}")
            print(f"Index created: idx_libraries_cache_updated")

            # Show new database size
            new_size = db_path.stat().st_size / 1024 / 1024
            print(f"\nDatabase size after migration: {new_size:.2f} MB")

            print(f"\n{'='*70}")
            print(f"Migration completed successfully!")
            print(f"{'='*70}\n")

            if backup_path.exists():
                print(f"Backup saved at: {backup_path}")
                print(f"   You can delete this once you've verified everything works\n")

            return True

    except Exception as e:
        print(f"ERROR: Error during migration: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Apply series tree cache migration to YACLib database"
    )
    parser.add_argument(
        '--db-path',
        type=Path,
        help='Path to yaclib.db (default: platform-specific location)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )

    args = parser.parse_args()

    # Determine database path
    if args.db_path:
        db_path = args.db_path
    else:
        db_path = get_default_db_path()

    # Apply migration
    success = apply_migration(db_path, dry_run=args.dry_run)

    if not success:
        sys.exit(1)

    print("Done!\n")


if __name__ == "__main__":
    main()

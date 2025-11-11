#!/usr/bin/env python3
"""
Apply Performance Indexes Migration

This script adds performance indexes to speed up common queries.
Safe to run multiple times (uses CREATE INDEX IF NOT EXISTS).

Usage:
    python apply_performance_indexes.py [--db-path /path/to/yaclib.db]

If no path is provided, uses default platform-specific location.
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
        return Path(os.getenv("APPDATA")) / "YACLib/yaclib.db"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


def check_database_exists(db_path):
    """Check if database file exists."""
    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        print("\nPlease provide the correct path using --db-path option")
        return False
    return True


def backup_database(db_path):
    """Create a backup of the database before migration."""
    backup_path = db_path.with_suffix('.db.backup')
    print(f"📦 Creating backup: {backup_path}")

    import shutil
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✅ Backup created successfully")
        return backup_path
    except Exception as e:
        print(f"⚠️  Warning: Could not create backup: {e}")
        return None


def get_current_indexes(conn):
    """Get list of current indexes."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, tbl_name
        FROM sqlite_master
        WHERE type='index'
        AND name LIKE 'idx_%'
        ORDER BY tbl_name, name
    """)
    return cursor.fetchall()


def apply_migration(db_path, dry_run=False):
    """Apply the performance indexes migration."""

    print(f"\n{'='*70}")
    print(f"  YACLib Performance Indexes Migration")
    print(f"{'='*70}\n")

    if not check_database_exists(db_path):
        return False

    print(f"📂 Database: {db_path}")
    print(f"📊 Database size: {db_path.stat().st_size / 1024 / 1024:.2f} MB\n")

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")

    # Read migration SQL
    migration_file = Path(__file__).parent / "002_performance_indexes.sql"
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False

    with open(migration_file, 'r') as f:
        migration_sql = f.read()

    # Extract only the CREATE INDEX statements (skip comments and FTS)
    index_statements = []
    for line in migration_sql.split('\n'):
        line = line.strip()
        if line.startswith('CREATE INDEX IF NOT EXISTS'):
            # Find the complete statement (may span multiple lines)
            stmt = line
            if not stmt.endswith(';'):
                # Statement continues on next line - but for simplicity we'll keep it single line
                pass
            index_statements.append(stmt)

    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Get current indexes
        print("📋 Current indexes:")
        current_indexes = get_current_indexes(conn)
        for idx_name, tbl_name in current_indexes:
            print(f"  • {idx_name} on {tbl_name}")
        print(f"\nTotal: {len(current_indexes)} indexes\n")

        if dry_run:
            print("📝 Indexes that would be created:")
            # Parse index names from SQL
            for stmt in index_statements:
                if 'CREATE INDEX IF NOT EXISTS' in stmt:
                    idx_name = stmt.split('idx_')[1].split()[0].strip()
                    print(f"  • idx_{idx_name}")
            print(f"\n✅ Dry run completed - no changes made")
            return True

        # Create backup
        backup_path = backup_database(db_path)

        # Apply indexes
        print("\n🔨 Creating indexes...")
        cursor = conn.cursor()

        created_count = 0
        skipped_count = 0
        start_time = time.time()

        # Execute the full migration SQL
        try:
            # Split into individual statements and execute
            statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]

            for statement in statements:
                # Skip comments and empty lines
                if not statement or statement.startswith('/*') or statement.startswith('--'):
                    continue

                # Skip FTS statements (they're commented out)
                if 'CREATE VIRTUAL TABLE' in statement or 'CREATE TRIGGER' in statement:
                    continue

                try:
                    cursor.execute(statement)

                    # Extract index name for reporting
                    if 'CREATE INDEX IF NOT EXISTS' in statement:
                        idx_name = statement.split('idx_')[1].split()[0].strip()
                        if idx_name not in [name for name, _ in current_indexes]:
                            print(f"  ✅ Created: idx_{idx_name}")
                            created_count += 1
                        else:
                            skipped_count += 1
                except sqlite3.OperationalError as e:
                    if 'already exists' in str(e):
                        skipped_count += 1
                    else:
                        print(f"  ⚠️  Warning: {e}")

            # Commit changes
            conn.commit()

            elapsed = time.time() - start_time

            print(f"\n{'='*70}")
            print(f"  Migration Summary")
            print(f"{'='*70}")
            print(f"✅ Indexes created: {created_count}")
            print(f"⏭️  Indexes skipped (already exist): {skipped_count}")
            print(f"⏱️  Time elapsed: {elapsed:.2f} seconds")

            # Get new index count
            new_indexes = get_current_indexes(conn)
            print(f"📊 Total indexes now: {len(new_indexes)}")

            # Analyze database to update statistics
            print(f"\n🔍 Analyzing database to update query planner statistics...")
            cursor.execute("ANALYZE")
            conn.commit()
            print(f"✅ Analysis complete")

            # Show new database size
            new_size = db_path.stat().st_size / 1024 / 1024
            print(f"\n📊 Database size after migration: {new_size:.2f} MB")

            print(f"\n{'='*70}")
            print(f"✅ Migration completed successfully!")
            print(f"{'='*70}\n")

            if backup_path:
                print(f"💾 Backup saved at: {backup_path}")
                print(f"   You can delete this once you've verified everything works\n")

            return True

        except Exception as e:
            print(f"\n❌ Error during migration: {e}")
            print(f"Rolling back changes...")
            conn.rollback()
            return False
        finally:
            conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def verify_indexes(db_path):
    """Verify that indexes were created successfully."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all indexes we expect to be created
        expected_indexes = [
            'idx_comics_title',
            'idx_comics_publisher',
            'idx_comics_year',
            'idx_comics_filename',
            'idx_comics_library_series',
            'idx_comics_library_folder',
            'idx_comics_file_modified',
            'idx_reading_progress_continue',
            'idx_reading_progress_completed',
            'idx_reading_progress_percent',
            'idx_series_library_name',
            'idx_series_year_start',
            'idx_folders_library_path',
            'idx_folders_name',
            'idx_collections_user_position',
            'idx_favorites_user_created',
            'idx_comics_library_count',
        ]

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name IN ({})
        """.format(','.join('?' * len(expected_indexes))), expected_indexes)

        found_indexes = [row[0] for row in cursor.fetchall()]
        missing = set(expected_indexes) - set(found_indexes)

        print(f"\n📊 Index Verification:")
        print(f"  Expected: {len(expected_indexes)}")
        print(f"  Found: {len(found_indexes)}")

        if missing:
            print(f"  ⚠️  Missing: {len(missing)}")
            for idx in missing:
                print(f"    • {idx}")
        else:
            print(f"  ✅ All indexes created successfully!")

        conn.close()
        return len(missing) == 0

    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Apply performance indexes to YACLib database"
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
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify indexes after creation'
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

    # Verify if requested
    if args.verify and not args.dry_run:
        if not verify_indexes(db_path):
            sys.exit(1)

    print("🎉 Done!\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Apply YACReader compatibility migration to existing database.

Usage:
    python migrations/apply_migration.py <database_path>
"""

import sys
import sqlite3
from pathlib import Path


def apply_migration(db_path: str):
    """Apply the YACReader compatibility migration."""

    migration_sql = Path(__file__).parent / "001_yacreader_compatibility.sql"

    if not migration_sql.exists():
        print(f"❌ Migration file not found: {migration_sql}")
        return False

    print(f"📋 Reading migration: {migration_sql.name}")
    sql = migration_sql.read_text()

    try:
        print(f"🔌 Connecting to database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")

        print("🚀 Applying migration...")
        # Execute migration (split by semicolon and execute each statement)
        statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]

        for i, statement in enumerate(statements, 1):
            # Skip comment-only statements
            if not statement or all(line.startswith('--') for line in statement.split('\n') if line.strip()):
                continue

            try:
                cursor.execute(statement)
                print(f"  ✓ Statement {i}/{len(statements)}")
            except sqlite3.Error as e:
                # Some statements might fail if column already exists, which is fine
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"  ⊘ Statement {i}/{len(statements)} - already applied")
                else:
                    print(f"  ⚠ Statement {i}/{len(statements)} - {e}")

        conn.commit()
        print("✅ Migration applied successfully!")

        # Show table info for verification
        print("\n📊 Verifying new tables...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        new_tables = ['favorites', 'labels', 'comic_labels', 'reading_lists', 'reading_list_items']
        for table in new_tables:
            if (table,) in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  ✓ {table}: {count} rows")
            else:
                print(f"  ✗ {table}: NOT FOUND")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    if len(sys.argv) != 2:
        print("Usage: python apply_migration.py <database_path>")
        print("\nExample:")
        print("  python migrations/apply_migration.py ~/.yaclib/library.db")
        sys.exit(1)

    db_path = sys.argv[1]

    if not Path(db_path).exists():
        print(f"❌ Database file not found: {db_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("  YACReader API Compatibility Migration")
    print(f"{'='*60}\n")

    success = apply_migration(db_path)

    print(f"\n{'='*60}\n")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

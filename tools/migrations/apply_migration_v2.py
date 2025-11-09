#!/usr/bin/env python3
"""
Apply YACReader compatibility migration to existing database.
This version handles SQLite's limitations with ALTER TABLE.

Usage:
    python migrations/apply_migration_v2.py <database_path>
"""

import sys
import sqlite3
from pathlib import Path


def column_exists(cursor, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def apply_migration(db_path: str):
    """Apply the YACReader compatibility migration."""

    print(f"\n{'='*60}")
    print("  YACReader API Compatibility Migration v2")
    print(f"{'='*60}\n")

    try:
        print(f"🔌 Connecting to database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")

        print("🚀 Applying migration...\n")

        # Define all columns to add to comics table
        comic_columns = [
            ("penciller", "TEXT"),
            ("inker", "TEXT"),
            ("colorist", "TEXT"),
            ("letterer", "TEXT"),
            ("cover_artist", "TEXT"),
            ("editor", "TEXT"),
            ("story_arc", "TEXT"),
            ("arc_number", "TEXT"),
            ("arc_count", "INTEGER"),
            ("alternate_series", "TEXT"),
            ("alternate_number", "TEXT"),
            ("alternate_count", "INTEGER"),
            ("genre", "TEXT"),
            ("language_iso", "TEXT"),
            ("age_rating", "TEXT"),
            ("imprint", "TEXT"),
            ("format_type", "TEXT"),
            ("is_color", "BOOLEAN"),
            ("characters", "TEXT"),
            ("teams", "TEXT"),
            ("locations", "TEXT"),
            ("main_character_or_team", "TEXT"),
            ("series_group", "TEXT"),
            ("notes", "TEXT"),
            ("review", "TEXT"),
            ("tags", "TEXT"),
            ("comic_vine_id", "TEXT"),
            ("is_bis", "BOOLEAN DEFAULT FALSE"),
            ("count", "INTEGER"),
            ("date", "TEXT"),
            ("rating", "REAL DEFAULT 0.0"),
            ("brightness", "INTEGER DEFAULT 0"),
            ("contrast", "INTEGER DEFAULT 0"),
            ("gamma", "REAL DEFAULT 1.0"),
            ("bookmark1", "INTEGER DEFAULT 0"),
            ("bookmark2", "INTEGER DEFAULT 0"),
            ("bookmark3", "INTEGER DEFAULT 0"),
            ("cover_page", "INTEGER DEFAULT 1"),
            ("cover_size_ratio", "REAL DEFAULT 0.0"),
            ("original_cover_size", "TEXT"),
            ("last_time_opened", "INTEGER"),
            ("has_been_opened", "BOOLEAN DEFAULT FALSE"),
            ("edited", "BOOLEAN DEFAULT FALSE"),
        ]

        # Add columns to comics table
        print("📝 Adding columns to comics table...")
        added_count = 0
        skipped_count = 0

        for col_name, col_type in comic_columns:
            if not column_exists(cursor, "comics", col_name):
                try:
                    cursor.execute(f"ALTER TABLE comics ADD COLUMN {col_name} {col_type}")
                    added_count += 1
                    print(f"  ✓ Added: {col_name}")
                except sqlite3.Error as e:
                    print(f"  ✗ Failed to add {col_name}: {e}")
            else:
                skipped_count += 1

        print(f"\n  Summary: {added_count} columns added, {skipped_count} already existed\n")

        # Add columns to sessions table
        print("📝 Adding columns to sessions table...")
        session_columns = [
            ("device_type", "TEXT"),
            ("display_type", "TEXT"),
            ("downloaded_comics", "TEXT"),
        ]

        added_count = 0
        skipped_count = 0

        for col_name, col_type in session_columns:
            if not column_exists(cursor, "sessions", col_name):
                try:
                    cursor.execute(f"ALTER TABLE sessions ADD COLUMN {col_name} {col_type}")
                    added_count += 1
                    print(f"  ✓ Added: {col_name}")
                except sqlite3.Error as e:
                    print(f"  ✗ Failed to add {col_name}: {e}")
            else:
                skipped_count += 1

        print(f"\n  Summary: {added_count} columns added, {skipped_count} already existed\n")

        # Create new tables (these are idempotent with IF NOT EXISTS)
        print("📝 Creating new tables...")

        # Favorites
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                library_id INTEGER NOT NULL,
                comic_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (library_id) REFERENCES libraries (id) ON DELETE CASCADE,
                FOREIGN KEY (comic_id) REFERENCES comics (id) ON DELETE CASCADE,
                UNIQUE (user_id, comic_id)
            )
        """)
        print("  ✓ favorites")

        # Labels
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS labels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                library_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                color_id INTEGER DEFAULT 0,
                position INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (library_id) REFERENCES libraries (id) ON DELETE CASCADE,
                UNIQUE (library_id, name)
            )
        """)
        print("  ✓ labels")

        # Comic Labels
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comic_labels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comic_id INTEGER NOT NULL,
                label_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (comic_id) REFERENCES comics (id) ON DELETE CASCADE,
                FOREIGN KEY (label_id) REFERENCES labels (id) ON DELETE CASCADE,
                UNIQUE (comic_id, label_id)
            )
        """)
        print("  ✓ comic_labels")

        # Reading Lists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reading_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                library_id INTEGER NOT NULL,
                user_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                is_public BOOLEAN DEFAULT FALSE,
                position INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (library_id) REFERENCES libraries (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        print("  ✓ reading_lists")

        # Reading List Items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reading_list_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reading_list_id INTEGER NOT NULL,
                comic_id INTEGER NOT NULL,
                position INTEGER DEFAULT 0,
                added_at INTEGER NOT NULL,
                FOREIGN KEY (reading_list_id) REFERENCES reading_lists (id) ON DELETE CASCADE,
                FOREIGN KEY (comic_id) REFERENCES comics (id) ON DELETE CASCADE,
                UNIQUE (reading_list_id, comic_id)
            )
        """)
        print("  ✓ reading_list_items")

        # Create indexes
        print("\n📝 Creating indexes...")

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_favorites_library ON favorites (library_id)",
            "CREATE INDEX IF NOT EXISTS idx_favorites_comic ON favorites (comic_id)",
            "CREATE INDEX IF NOT EXISTS idx_labels_library ON labels (library_id)",
            "CREATE INDEX IF NOT EXISTS idx_comic_labels_comic ON comic_labels (comic_id)",
            "CREATE INDEX IF NOT EXISTS idx_comic_labels_label ON comic_labels (label_id)",
            "CREATE INDEX IF NOT EXISTS idx_reading_lists_library ON reading_lists (library_id)",
            "CREATE INDEX IF NOT EXISTS idx_reading_lists_user ON reading_lists (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_reading_list_items_list ON reading_list_items (reading_list_id)",
            "CREATE INDEX IF NOT EXISTS idx_reading_list_items_comic ON reading_list_items (comic_id)",
            "CREATE INDEX IF NOT EXISTS idx_reading_list_items_position ON reading_list_items (reading_list_id, position)",
        ]

        for idx_sql in indexes:
            cursor.execute(idx_sql)
            print(f"  ✓ {idx_sql.split('ON')[0].strip().split()[-1]}")

        conn.commit()
        print("\n✅ Migration applied successfully!")

        # Show table info for verification
        print("\n📊 Verifying tables...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        target_tables = ['comics', 'sessions', 'favorites', 'labels', 'comic_labels', 'reading_lists', 'reading_list_items']
        for table in target_tables:
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
        import traceback
        traceback.print_exc()
        return False


def main():
    if len(sys.argv) != 2:
        print("Usage: python apply_migration_v2.py <database_path>")
        print("\nExample:")
        print("  python migrations/apply_migration_v2.py ~/.local/share/yaclib/yaclib.db")
        sys.exit(1)

    db_path = sys.argv[1]

    if not Path(db_path).exists():
        print(f"❌ Database file not found: {db_path}")
        sys.exit(1)

    success = apply_migration(db_path)

    print(f"\n{'='*60}\n")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

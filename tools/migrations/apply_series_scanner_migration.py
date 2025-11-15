#!/usr/bin/env python3
"""
Apply Series Scanner Metadata Migration

Adds scanner metadata fields to the series table to support saving
scanned metadata from series-level scanners like AniList.
"""

import sqlite3
import sys
from pathlib import Path

def apply_migration(db_path: str):
    """Apply the series scanner metadata migration"""
    
    print(f"Applying series scanner metadata migration to: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if migration is needed
        cursor.execute("PRAGMA table_info(series)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'scanner_source' in columns:
            print("✓ Migration already applied - scanner_source column exists")
            return
        
        print("Adding scanner metadata fields...")
        
        # Read migration SQL
        migration_file = Path(__file__).parent / '005_add_series_scanner_metadata.sql'
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        # Execute migration
        cursor.executescript(sql)
        conn.commit()
        
        # Verify
        cursor.execute("PRAGMA table_info(series)")
        new_columns = [row[1] for row in cursor.fetchall()]
        
        expected_columns = [
            'scanner_source', 'scanner_source_id', 'scanner_source_url',
            'scanned_at', 'scan_confidence', 'writer', 'artist', 'genre',
            'tags', 'status', 'format', 'chapters', 'volumes'
        ]
        
        missing = [col for col in expected_columns if col not in new_columns]
        if missing:
            print(f"✗ Migration incomplete - missing columns: {missing}")
            sys.exit(1)
        
        print("✓ Migration completed successfully")
        print(f"  Added {len(expected_columns)} new columns to series table")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python apply_series_scanner_migration.py <path_to_yaclib.db>")
        print("\nExample:")
        print("  python apply_series_scanner_migration.py ../../yaclib.db")
        sys.exit(1)
    
    db_path = sys.argv[1]
    
    if not Path(db_path).exists():
        print(f"✗ Database not found: {db_path}")
        sys.exit(1)
    
    apply_migration(db_path)

#!/usr/bin/env python3
"""
Apply series search indexes migration

Adds indexes to series metadata fields for improved search performance.
"""

import sys
import sqlite3
from pathlib import Path


def apply_migration(db_path: Path):
    """Apply the series search indexes migration"""
    
    migration_file = Path(__file__).parent / "006_add_series_search_indexes.sql"
    
    print(f"Applying series search indexes migration to: {db_path}")
    
    # Read migration SQL
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Execute migration
        cursor.executescript(migration_sql)
        conn.commit()
        
        # Verify indexes were created
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_series_%'
            ORDER BY name
        """)
        
        indexes = cursor.fetchall()
        print(f"\n✓ Migration applied successfully!")
        print(f"\nCreated/verified {len(indexes)} indexes:")
        for idx in indexes:
            print(f"  - {idx[0]}")
        
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Migration failed: {e}")
        raise
    
    finally:
        conn.close()


def main():
    """Main entry point"""
    
    # Default to yaclib.db in current directory
    db_path = Path('yaclib.db')
    
    # Allow command-line argument to override
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        print("Usage: python apply_series_search_indexes.py [path/to/yaclib.db]")
        print("       (defaults to ./yaclib.db)")
        sys.exit(1)
    
    apply_migration(db_path)
    print("\n✓ Series search indexes migration complete!")


if __name__ == '__main__':
    main()

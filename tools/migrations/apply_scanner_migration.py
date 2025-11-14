#!/usr/bin/env python3
"""
Apply scanner metadata migration to database

Adds scanner metadata fields to the comics table.
This migration can be safely run multiple times - it will only apply if needed.
"""

import sqlite3
import sys
from pathlib import Path

def check_column_exists(cursor, table: str, column: str) -> bool:
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns

def apply_migration(db_path: str):
    """Apply the scanner metadata migration"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if migration already applied
        if check_column_exists(cursor, 'comics', 'scanner_source'):
            print("✓ Migration already applied. Scanner metadata fields exist.")
            
            # Verify all fields
            expected_fields = ['web', 'scanner_source', 'scanner_source_id', 
                             'scanner_source_url', 'scanned_at', 'scan_confidence']
            
            missing_fields = []
            for field in expected_fields:
                if not check_column_exists(cursor, 'comics', field):
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"⚠ Warning: Some fields are missing: {missing_fields}")
                print("  Attempting to add missing fields...")
                
                for field in missing_fields:
                    try:
                        if field == 'scan_confidence':
                            cursor.execute(f"ALTER TABLE comics ADD COLUMN {field} REAL")
                        elif field == 'scanned_at':
                            cursor.execute(f"ALTER TABLE comics ADD COLUMN {field} INTEGER")
                        else:
                            cursor.execute(f"ALTER TABLE comics ADD COLUMN {field} TEXT")
                        print(f"  ✓ Added {field}")
                    except Exception as e:
                        print(f"  ✗ Failed to add {field}: {e}")
                
                conn.commit()
            
            return
        
        print("Applying scanner metadata migration...")
        
        # Add new columns
        columns_to_add = [
            ("web", "TEXT"),
            ("scanner_source", "TEXT"),
            ("scanner_source_id", "TEXT"),
            ("scanner_source_url", "TEXT"),
            ("scanned_at", "INTEGER"),
            ("scan_confidence", "REAL"),
        ]
        
        for column_name, column_type in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE comics ADD COLUMN {column_name} {column_type}")
                print(f"  ✓ Added {column_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"  - {column_name} already exists")
                else:
                    raise
        
        # Add indexes
        indexes_to_add = [
            ("idx_comics_scanner_source", "comics(scanner_source)"),
            ("idx_comics_scanned_at", "comics(scanned_at)"),
        ]
        
        for index_name, index_def in indexes_to_add:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {index_def}")
                print(f"  ✓ Created index {index_name}")
            except Exception as e:
                print(f"  - Index {index_name}: {e}")
        
        conn.commit()
        
        # Update schema version if table exists
        if check_column_exists(cursor, 'schema_version', 'version'):
            cursor.execute("SELECT MAX(version) FROM schema_version")
            current_version = cursor.fetchone()[0] or 0
            
            if current_version < 2:
                cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (2, ?)",
                             (int(__import__('time').time()),))
                conn.commit()
                print(f"  ✓ Updated schema version to 2")
        
        print("\n✓ Migration completed successfully!")
        
        # Verify all fields are present
        cursor.execute("PRAGMA table_info(comics)")
        columns = [row[1] for row in cursor.fetchall()]
        
        print("\nVerification:")
        expected_fields = ['web', 'scanner_source', 'scanner_source_id', 
                         'scanner_source_url', 'scanned_at', 'scan_confidence']
        for field in expected_fields:
            if field in columns:
                print(f"  ✓ {field}")
            else:
                print(f"  ✗ {field} (MISSING!)")
        
    except Exception as e:
        print(f"\n✗ Error applying migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python apply_scanner_migration.py <path_to_database.db>")
        print("\nThis script adds scanner metadata fields to the comics table.")
        print("It can be safely run multiple times - it will only apply if needed.")
        sys.exit(1)
    
    db_path = sys.argv[1]
    
    if not Path(db_path).exists():
        print(f"✗ Error: Database not found: {db_path}")
        sys.exit(1)
    
    apply_migration(db_path)

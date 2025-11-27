import sqlite3
import os
import sys

def migrate_db():
    db_path = 'data/main.db'
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(libraries)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'scan_interval' in columns:
            print("Column 'scan_interval' already exists in 'libraries' table.")
        else:
            print("Adding 'scan_interval' column to 'libraries' table...")
            cursor.execute("ALTER TABLE libraries ADD COLUMN scan_interval INTEGER DEFAULT 0")
            conn.commit()
            print("Column added successfully.")
            
    except Exception as e:
        print(f"Error migrating database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()

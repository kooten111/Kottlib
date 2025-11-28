#!/usr/bin/env python3
"""
Clean up bad genre metadata

Removes invalid genre values like "mitsuwa building" from comics
that shouldn't have them (e.g., Western comics like Fables).
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from database.database import Database
from sqlalchemy import text

def clean_fables_metadata():
    """Remove bad genre data from Fables series"""
    db = Database()
    
    with db.get_session() as session:
        print("Cleaning Fables metadata...")
        
        # Update comics with bad genre data
        result = session.execute(
            text("""
                UPDATE comics 
                SET genre = NULL 
                WHERE series = 'Fables' 
                AND genre LIKE '%mitsuwa building%'
            """)
        )
        
        print(f"  - Cleaned {result.rowcount} comic records")
        
        # Update series table if it exists
        try:
            result = session.execute(
                text("""
                    UPDATE series 
                    SET genre = NULL 
                    WHERE name = 'Fables' 
                    AND genre LIKE '%mitsuwa building%'
                """)
            )
            print(f"  - Cleaned {result.rowcount} series records")
        except Exception as e:
            print(f"  - Series table cleanup skipped: {e}")
        
        session.commit()
        print("✓ Metadata cleanup complete!")

if __name__ == '__main__':
    clean_fables_metadata()

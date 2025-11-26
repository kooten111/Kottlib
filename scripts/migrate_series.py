import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database import get_default_db_path
from src.database.models import Comic, Folder, Series
from src.utils.series_utils import get_series_name_from_comic

def migrate_series():
    db_path = get_default_db_path()
    print(f"Migrating database: {db_path}")
    
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get all comics
        comics = session.query(Comic).all()
        print(f"Found {len(comics)} comics")
        
        updated_count = 0
        
        # Cache folder names
        folders = session.query(Folder).all()
        folder_map = {f.id: f.name for f in folders}
        
        for comic in comics:
            folder_name = folder_map.get(comic.folder_id)
            
            # Determine new series name
            # We pass None for comic.series to force recalculation based on folder/filename
            # But wait, get_series_name_from_comic uses comic.series if present.
            # We want to enforce folder name if it's the primary source, 
            # but the utils logic prioritizes metadata series if present.
            # The user said "THE FOLDER IS THE SERIES".
            # So we should probably prioritize folder name if available.
            
            new_series_name = "Unknown"
            if folder_name and folder_name != "__ROOT__":
                new_series_name = folder_name
            elif comic.series:
                new_series_name = comic.series
            else:
                # Fallback to filename logic
                from src.utils.series_utils import get_series_name
                new_series_name = get_series_name(filename=comic.filename)
            
            if comic.series != new_series_name:
                comic.series = new_series_name
                updated_count += 1
                
        session.commit()
        print(f"Updated {updated_count} comics with new series names")
        
        # Now rebuild series table
        print("Rebuilding series table...")
        
        # Clear existing series? Or just update?
        # Let's clear to be safe and remove "Untitled" ones
        session.execute(text("DELETE FROM series"))
        session.commit()
        
        # Group by series
        from sqlalchemy import func
        import time
        
        series_data = session.query(
            Comic.series,
            func.count(Comic.id).label('comic_count')
        ).filter(
            Comic.series.isnot(None)
        ).group_by(
            Comic.series
        ).all()
        
        created = 0
        now = int(time.time())
        
        for series_name, comic_count in series_data:
            if not series_name:
                continue
                
            # We deleted all series, so just create new ones
            # We need library_id. Since we are grouping by series name globally, 
            # we might have issues if same series name exists in different libraries.
            # We should group by library_id AND series.
            pass
        
        # Correct query grouping by library_id and series
        series_data_lib = session.query(
            Comic.library_id,
            Comic.series,
            func.count(Comic.id).label('comic_count')
        ).filter(
            Comic.series.isnot(None)
        ).group_by(
            Comic.library_id,
            Comic.series
        ).all()
        
        for library_id, series_name, comic_count in series_data_lib:
            if not series_name:
                continue
                
            new_series = Series(
                library_id=library_id,
                name=series_name,
                display_name=series_name,
                comic_count=comic_count,
                total_issues=comic_count,
                created_at=now,
                updated_at=now
            )
            session.add(new_series)
            created += 1
            
        session.commit()
        print(f"Created {created} series records")
        
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate_series()

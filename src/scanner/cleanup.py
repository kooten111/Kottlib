"""
Cleanup module for removing stale comics from the database.

Handles removal of comics whose files no longer exist on disk.
"""

import logging
from pathlib import Path
from typing import Set, Optional

from src.database import Database, get_covers_dir
from src.database.operations.comic import get_comics_in_library

from .thumbnail_generator import get_thumbnail_path


logger = logging.getLogger(__name__)


def cleanup_missing_comics(
    db: Database,
    library_id: int,
    library_path: Path,
    discovered_paths: Set[str],
    library_name: Optional[str] = None
) -> int:
    """
    Remove comics from database whose files no longer exist on disk.

    This is called after file discovery to ensure the database reflects
    the current state of the filesystem.

    Args:
        db: Database instance
        library_id: Library ID to clean up
        library_path: Root path of the library
        discovered_paths: Set of absolute paths to files that were discovered
        library_name: Optional library name for thumbnail cleanup

    Returns:
        Number of comics removed
    """
    removed_count = 0
    removed_hashes = []

    with db.get_session() as session:
        # Get all comics in this library
        comics = get_comics_in_library(session, library_id)
        
        for comic in comics:
            comic_path = Path(comic.path)
            
            # Check if the file path is in our discovered set
            # Also verify the file actually exists (in case of path changes)
            if str(comic_path) not in discovered_paths and not comic_path.exists():
                logger.info(f"Removing missing comic: {comic.filename} (was at {comic.path})")
                
                # Track hash for thumbnail cleanup
                if comic.hash:
                    removed_hashes.append(comic.hash)
                
                # Delete the comic (cascade will handle related records)
                session.delete(comic)
                removed_count += 1
        
        if removed_count > 0:
            session.commit()
            logger.info(f"Removed {removed_count} comics that no longer exist on disk")
    
    # Clean up orphaned thumbnails for removed comics
    if library_name and removed_hashes:
        covers_dir = get_covers_dir(library_name)
        _cleanup_thumbnails_for_hashes(covers_dir, removed_hashes)
    
    return removed_count


def _cleanup_thumbnails_for_hashes(covers_dir: Path, hashes: list) -> int:
    """
    Remove thumbnails for specific file hashes.

    Args:
        covers_dir: Covers directory (data/<LibraryName>/covers/)
        hashes: List of file hashes to remove thumbnails for

    Returns:
        Number of thumbnails removed
    """
    removed = 0
    
    for file_hash in hashes:
        # Get thumbnail paths using the hierarchical storage structure
        for format_type in ['JPEG', 'WEBP']:
            thumb_path = get_thumbnail_path(covers_dir, file_hash, format_type)
            if thumb_path.exists():
                try:
                    thumb_path.unlink()
                    removed += 1
                    logger.debug(f"Removed thumbnail: {thumb_path.name}")
                except Exception as e:
                    logger.error(f"Failed to remove thumbnail {thumb_path}: {e}")
    
    if removed > 0:
        logger.info(f"Cleaned up {removed} thumbnails for removed comics")
    
    return removed

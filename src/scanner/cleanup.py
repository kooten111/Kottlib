"""
Cleanup module for removing stale library records from the database.

Handles removal of comics and folders whose filesystem entries no longer exist.
"""

import logging
from pathlib import Path
from typing import Set, Optional

from src.constants import ROOT_FOLDER_MARKER
from src.database import Database, get_covers_dir
from src.database.models import Folder
from src.database.operations.comic import get_comics_in_library

from .thumbnail_generator import get_thumbnail_path


logger = logging.getLogger(__name__)


def _normalize_path(path_value: str) -> str:
    """Return a canonical absolute path string for robust comparisons."""
    return str(Path(path_value).resolve(strict=False))


def cleanup_missing_comics(
    db: Database,
    library_id: int,
    library_path: Path,
    discovered_paths: Set[str],
    discovered_folder_paths: Optional[Set[str]] = None,
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
        discovered_folder_paths: Set of absolute folder paths that still exist
        library_name: Optional library name for thumbnail cleanup

    Returns:
        Number of comics removed
    """
    removed_count = 0
    removed_hashes = []
    normalized_discovered_paths = {_normalize_path(path) for path in discovered_paths}
    normalized_discovered_folder_paths = {
        _normalize_path(path) for path in (discovered_folder_paths or set())
    }
    normalized_library_path = _normalize_path(str(library_path))

    with db.get_session() as session:
        # Get all comics in this library
        comics = get_comics_in_library(session, library_id)
        
        for comic in comics:
            comic_path = _normalize_path(comic.path)
            
            # Check if the file path is in our discovered set
            # STRICT MODE: If it's not in the discovered set, it's gone.
            # We trust discover_files returned the complete state of the library.
            if comic_path not in normalized_discovered_paths:
                logger.info(f"Removing missing comic: {comic.filename} (was at {comic.path})")
                
                # Track hash for thumbnail cleanup
                if comic.hash:
                    removed_hashes.append(comic.hash)
                
                # Delete the comic (cascade will handle related records)
                session.delete(comic)
                removed_count += 1
                
                # Commit in batches to avoid holding the database lock for too long
                # This prevents "database is locked" errors during massive cleanups
                if removed_count % 50 == 0:
                    try:
                        session.commit()
                        logger.debug(f"Committed batch of 50 removed comics")
                    except Exception as e:
                        logger.error(f"Error committing batch cleanup: {e}")
                        session.rollback()
        
        try:
            session.commit()
            if removed_count > 0:
                logger.info(f"Removed {removed_count} comics that no longer exist on disk")
        except Exception as e:
            logger.error(f"Error committing final comic cleanup: {e}")
            session.rollback()

        removed_folders = 0
        existing_folder_paths = normalized_discovered_folder_paths

        # Remove folders that no longer exist on disk, deepest first.
        folders = session.query(Folder).filter(Folder.library_id == library_id).all()
        stale_folders = sorted(
            (
                folder for folder in folders
                if folder.name != ROOT_FOLDER_MARKER
                and _normalize_path(folder.path) != normalized_library_path
                and _normalize_path(folder.path) not in existing_folder_paths
            ),
            key=lambda folder: len(Path(folder.path).parts),
            reverse=True,
        )

        for folder in stale_folders:
            logger.info(f"Removing missing folder: {folder.path}")
            session.delete(folder)
            removed_folders += 1

        if removed_folders > 0:
            try:
                session.commit()
                logger.info(f"Removed {removed_folders} folders that no longer exist on disk")
            except Exception as e:
                logger.error(f"Error committing folder cleanup: {e}")
                session.rollback()

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

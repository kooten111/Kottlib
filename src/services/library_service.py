"""
Library Service

High-level library operations including:
- Creating libraries with statistics
- Retrieving library information
- Updating library details
- Deleting libraries with cleanup
- Computing library statistics
"""

import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from ..database import (
    get_library_by_id,
    get_all_libraries,
    create_library,
    update_library,
    delete_library,
    get_library_stats,
)

logger = logging.getLogger(__name__)


def create_library_with_stats(
    session: Session,
    name: str,
    path: str,
    settings: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a new library and return it with statistics.
    
    Args:
        session: Database session
        name: Library name
        path: Library path
        settings: Optional settings dictionary
        
    Returns:
        Dictionary with library info and statistics
    """
    library = create_library(session, name=name, path=path, settings=settings)
    stats = get_library_stats(session, library.id)
    
    return {
        "id": library.id,
        "uuid": library.uuid,
        "name": library.name,
        "path": library.path,
        "created_at": library.created_at,
        "updated_at": library.updated_at,
        "last_scan_at": library.last_scan_at,
        "scan_status": library.scan_status,
        "comic_count": stats.get('comic_count', 0),
        "folder_count": stats.get('folder_count', 0),
    }


def get_library_with_stats(session: Session, library_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a library by ID with statistics.
    
    Args:
        session: Database session
        library_id: Library ID
        
    Returns:
        Dictionary with library info and statistics, or None if not found
    """
    library = get_library_by_id(session, library_id)
    if not library:
        return None
        
    stats = get_library_stats(session, library.id)
    
    return {
        "id": library.id,
        "uuid": library.uuid,
        "name": library.name,
        "path": library.path,
        "created_at": library.created_at,
        "updated_at": library.updated_at,
        "last_scan_at": library.last_scan_at,
        "scan_status": library.scan_status,
        "comic_count": stats.get('comic_count', 0),
        "folder_count": stats.get('folder_count', 0),
    }


def list_libraries_with_stats(session: Session) -> List[Dict[str, Any]]:
    """
    Get all libraries with statistics.
    
    Args:
        session: Database session
        
    Returns:
        List of dictionaries with library info and statistics
    """
    libraries = get_all_libraries(session)
    
    result = []
    for lib in libraries:
        stats = get_library_stats(session, lib.id)
        
        result.append({
            "id": lib.id,
            "uuid": lib.uuid,
            "name": lib.name,
            "path": lib.path,
            "created_at": lib.created_at,
            "updated_at": lib.updated_at,
            "last_scan_at": lib.last_scan_at,
            "scan_status": lib.scan_status,
            "comic_count": stats.get('comic_count', 0),
            "folder_count": stats.get('folder_count', 0),
        })
    
    return result


def update_library_with_stats(
    session: Session,
    library_id: int,
    name: Optional[str] = None,
    path: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Update a library and return it with statistics.
    
    Args:
        session: Database session
        library_id: Library ID
        name: Optional new name
        path: Optional new path
        settings: Optional settings dictionary
        
    Returns:
        Dictionary with updated library info and statistics, or None if not found
    """
    library = update_library(session, library_id, name=name, path=path, settings=settings)
    
    if not library:
        return None
        
    stats = get_library_stats(session, library.id)
    
    return {
        "id": library.id,
        "uuid": library.uuid,
        "name": library.name,
        "path": library.path,
        "created_at": library.created_at,
        "updated_at": library.updated_at,
        "last_scan_at": library.last_scan_at,
        "scan_status": library.scan_status,
        "comic_count": stats.get('comic_count', 0),
        "folder_count": stats.get('folder_count', 0),
    }


def delete_library_with_cleanup(session: Session, library_id: int) -> bool:
    """
    Delete a library and clean up associated data.
    
    This includes:
    - Comics
    - Folders
    - Covers
    - Series records
    - Reading progress
    - Other associated data
    
    Args:
        session: Database session
        library_id: Library ID
        
    Returns:
        True if deleted successfully, False if library not found
    """
    logger.info(f"Deleting library {library_id} with cleanup")
    
    # The delete_library function from database operations already handles cleanup
    success = delete_library(session, library_id)
    
    if success:
        logger.info(f"Successfully deleted library {library_id}")
    else:
        logger.warning(f"Library {library_id} not found for deletion")
        
    return success


def get_library_statistics(session: Session, library_id: int) -> Optional[Dict[str, Any]]:
    """
    Get detailed statistics for a library.
    
    Args:
        session: Database session
        library_id: Library ID
        
    Returns:
        Dictionary with library statistics, or None if library not found
    """
    library = get_library_by_id(session, library_id)
    if not library:
        return None
        
    stats = get_library_stats(session, library_id)
    
    return {
        "library_id": library_id,
        "comic_count": stats.get('comic_count', 0),
        "folder_count": stats.get('folder_count', 0),
        "total_size": stats.get('total_size', 0),
        "series_count": stats.get('series_count', 0),
    }

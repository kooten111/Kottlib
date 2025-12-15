"""
Scan Service

Orchestrates scanning operations including:
- Library scans
- Single comic scans
- Series scans
- Progress tracking
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from ..database.models import Comic, Library
from .metadata_service import MetadataService

logger = logging.getLogger(__name__)


def scan_single_comic(
    session: Session,
    comic_id: int,
    scanner_name: str,
    overwrite: bool = False,
    confidence_threshold: Optional[float] = None
) -> Dict[str, Any]:
    """
    Scan a single comic with a metadata scanner.
    
    Args:
        session: Database session
        comic_id: Comic ID to scan
        scanner_name: Name of scanner to use
        overwrite: Whether to overwrite existing metadata
        confidence_threshold: Minimum confidence score to accept results
        
    Returns:
        Dictionary with scan results
        
    Raises:
        ValueError: If comic not found or scanner not available
    """
    from ..api.routers.scanners.manager import get_scanner_manager
    
    comic = session.query(Comic).filter(Comic.id == comic_id).first()
    if not comic:
        raise ValueError(f"Comic {comic_id} not found")
        
    manager = get_scanner_manager()
    if scanner_name not in manager.get_available_scanners():
        raise ValueError(f"Scanner {scanner_name} not available")
        
    # Get scanner configuration from library settings
    library = session.query(Library).filter(Library.id == comic.library_id).first()
    settings = library.settings or {} if library else {}
    scanner_config = settings.get('scanner', {})
    scanner_specific_config = scanner_config.get('scanner_configs', {}).get(scanner_name, {})
    
    # Get scanner instance
    scanner = manager.get_scanner(scanner_name, config=scanner_specific_config)
    
    # Perform scan
    result, _ = scanner.scan(comic.filename, confidence_threshold=confidence_threshold)
    
    if not result:
        return {
            "success": False,
            "message": "No metadata found",
            "comic_id": comic_id,
        }
        
    # Apply metadata
    application_result = MetadataService.apply_scan_result_to_comic(
        session,
        comic,
        result,
        scanner_name,
        overwrite=overwrite
    )
    
    return {
        "success": application_result.success,
        "message": application_result.message,
        "comic_id": comic_id,
        "confidence": result.confidence,
    }


def scan_series(
    session: Session,
    library_id: int,
    series_name: str,
    scanner_name: str,
    overwrite: bool = False,
    confidence_threshold: Optional[float] = None
) -> Dict[str, Any]:
    """
    Scan a series with a metadata scanner.
    
    Args:
        session: Database session
        library_id: Library ID
        series_name: Name of series to scan
        scanner_name: Name of scanner to use
        overwrite: Whether to overwrite existing metadata
        confidence_threshold: Minimum confidence score to accept results
        
    Returns:
        Dictionary with scan results
        
    Raises:
        ValueError: If scanner not available
    """
    from ..api.routers.scanners.manager import get_scanner_manager
    import time
    from ..database.models import Series
    
    manager = get_scanner_manager()
    if scanner_name not in manager.get_available_scanners():
        raise ValueError(f"Scanner {scanner_name} not available")
        
    # Get scanner configuration from library settings
    library = session.query(Library).filter(Library.id == library_id).first()
    settings = library.settings or {} if library else {}
    scanner_config = settings.get('scanner', {})
    scanner_specific_config = scanner_config.get('scanner_configs', {}).get(scanner_name, {})
    
    # Get scanner instance
    scanner = manager.get_scanner(scanner_name, config=scanner_specific_config)
    
    # Perform scan
    result, _ = scanner.scan(series_name, confidence_threshold=confidence_threshold)
    
    if not result:
        return {
            "success": False,
            "message": "No metadata found",
            "series_name": series_name,
        }
        
    # Get or create series record
    series = session.query(Series).filter(
        Series.library_id == library_id,
        Series.name == series_name
    ).first()
    
    if not series:
        series = Series(
            library_id=library_id,
            name=series_name,
            display_name=series_name,
            created_at=int(time.time()),
            updated_at=int(time.time())
        )
        session.add(series)
        session.flush()
    
    # Apply metadata to series
    metadata = result.metadata
    
    def should_update(field_value):
        return overwrite or not field_value
    
    if metadata.get('title') and should_update(series.display_name):
        series.display_name = metadata['title']
    
    if metadata.get('description') and should_update(series.description):
        series.description = metadata['description']
    
    if metadata.get('writer') and should_update(series.writer):
        series.writer = metadata['writer']
    
    if metadata.get('artist') and should_update(series.artist):
        series.artist = metadata['artist']
    
    if metadata.get('genre') and should_update(series.genre):
        series.genre = metadata['genre']
    
    if metadata.get('year') and should_update(series.year_start):
        series.year_start = metadata['year']
    
    if metadata.get('publisher') and should_update(series.publisher):
        series.publisher = metadata['publisher']
    
    if metadata.get('status') and should_update(series.status):
        series.status = metadata['status']
    
    if metadata.get('format') and should_update(series.format):
        series.format = metadata['format']
    
    if metadata.get('volume') and should_update(series.volumes):
        series.volumes = metadata['volume']
    
    if metadata.get('count') and should_update(series.chapters):
        series.chapters = metadata['count']
    
    if result.tags and should_update(series.tags):
        series.tags = ', '.join(result.tags) if isinstance(result.tags, list) else str(result.tags)
    
    # Store scanner metadata
    series.scanner_source = scanner_name
    series.scanner_source_id = result.source_id
    series.scanner_source_url = result.source_url
    series.scanned_at = int(time.time())
    series.scan_confidence = result.confidence
    series.updated_at = int(time.time())
    
    session.commit()
    
    return {
        "success": True,
        "message": "Series metadata updated",
        "series_name": series_name,
        "confidence": result.confidence,
    }


def scan_library(
    db,
    library_id: int,
    scanner_name: str,
    overwrite: bool = False,
    rescan_existing: bool = False,
    confidence_threshold: Optional[float] = None
) -> Dict[str, Any]:
    """
    Trigger a library scan as a background task.
    
    Args:
        db: Database instance
        library_id: Library ID to scan
        scanner_name: Name of scanner to use
        overwrite: Whether to overwrite existing metadata
        rescan_existing: Whether to rescan already-scanned comics
        confidence_threshold: Minimum confidence score to accept results
        
    Returns:
        Dictionary with task information
        
    Raises:
        ValueError: If library not found or scanner not available
    """
    from ..api.routers.scanners.manager import get_scanner_manager
    
    with db.get_session() as session:
        library = session.query(Library).filter(Library.id == library_id).first()
        if not library:
            raise ValueError(f"Library {library_id} not found")
            
        manager = get_scanner_manager()
        if scanner_name not in manager.get_available_scanners():
            raise ValueError(f"Scanner {scanner_name} not available")
    
    # Start background task
    import threading
    from ..api.routers.scanners.tasks import run_library_scan_task
    
    thread = threading.Thread(
        target=run_library_scan_task,
        args=(db, library_id, scanner_name, overwrite, rescan_existing, confidence_threshold),
        daemon=True
    )
    thread.start()
    
    return {
        "success": True,
        "message": "Library scan started",
        "library_id": library_id,
        "scanner": scanner_name,
    }


def get_scan_progress(library_id: int) -> Optional[Dict[str, Any]]:
    """
    Get the current scan progress for a library.
    
    Args:
        library_id: Library ID
        
    Returns:
        Dictionary with progress information, or None if no scan in progress
    """
    from ..api.routers.scanners.progress import get_internal_progress
    
    return get_internal_progress(library_id)


def start_library_scan_task(
    db,
    library_id: int,
    scanner_name: str,
    overwrite: bool = False,
    rescan_existing: bool = False,
    confidence_threshold: Optional[float] = None
) -> None:
    """
    Background task function for library scanning.
    
    This is a wrapper around the existing task implementation.
    
    Args:
        db: Database instance
        library_id: Library ID to scan
        scanner_name: Name of scanner to use
        overwrite: Whether to overwrite existing metadata
        rescan_existing: Whether to rescan already-scanned comics
        confidence_threshold: Minimum confidence score to accept results
    """
    from ..api.routers.scanners.tasks import run_library_scan_task
    
    run_library_scan_task(
        db, library_id, scanner_name, overwrite, rescan_existing, confidence_threshold
    )

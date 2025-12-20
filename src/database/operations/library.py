"""
Library database operations.
"""

import time
import uuid
import logging
from pathlib import Path
from typing import Optional, List

from sqlalchemy.orm import Session

from ..models import Library


logger = logging.getLogger(__name__)


def create_library(
    session: Session,
    name: str,
    path: str,
    settings: Optional[dict] = None
) -> Library:
    """Create a new library."""
    now = int(time.time())

    library = Library(
        uuid=str(uuid.uuid4()),
        name=name,
        path=str(Path(path).resolve()),
        created_at=now,
        updated_at=now,
        scan_status='pending',
        settings=settings or {},
        scan_interval=0
    )

    session.add(library)
    session.flush()  # Flush to get the ID without committing

    logger.info(f"Created library: {name} at {path}")
    return library


def get_library_by_id(session: Session, library_id: int) -> Optional[Library]:
    """Get library by ID."""
    logger.debug(f"[DB] get_library_by_id: library_id={library_id}")
    result = session.query(Library).filter_by(id=library_id).first()
    if result:
        logger.debug(f"[DB] Library found: id={result.id}, name={result.name}, path={result.path}")
    else:
        logger.debug(f"[DB] Library not found: library_id={library_id}")
    return result


def get_library_by_path(session: Session, path: str) -> Optional[Library]:
    """Get library by filesystem path."""
    return session.query(Library).filter_by(path=str(Path(path).resolve())).first()


def update_library(
    session: Session,
    library_id: int,
    name: Optional[str] = None,
    path: Optional[str] = None,
    settings: Optional[dict] = None,
    scan_interval: Optional[int] = None
) -> Optional[Library]:
    """Update library details."""
    library = get_library_by_id(session, library_id)
    if not library:
        return None

    if name is not None:
        library.name = name
    
    if path is not None:
        library.path = str(Path(path).resolve())
        
    if settings is not None:
        # Merge settings instead of overwriting completely if desired, 
        # but for now we'll do a shallow merge or replacement.
        # Let's do a merge to preserve other settings if partial update
        current_settings = dict(library.settings or {})
        current_settings.update(settings)
        library.settings = current_settings
        # Explicitly flag as modified for JSON fields to ensure persistence
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(library, "settings")
    
    if scan_interval is not None:
        library.scan_interval = scan_interval

    library.updated_at = int(time.time())
    session.flush()
    return library


def delete_library(session: Session, library_id: int) -> bool:
    """Delete a library and all its content."""
    library = get_library_by_id(session, library_id)
    if not library:
        return False

    session.delete(library)
    session.flush()
    return True


def get_all_libraries(session: Session) -> List[Library]:
    """Get all libraries."""
    return session.query(Library).all()


def update_library_scan_status(
    session: Session,
    library_id: int,
    status: str,
    timestamp: Optional[int] = None
):
    """Update library scan status."""
    library = get_library_by_id(session, library_id)
    if library:
        library.scan_status = status
        library.last_scan_completed = timestamp or int(time.time())
        library.updated_at = int(time.time())
        session.flush()  # Flush changes without committing


def update_library_series_tree_cache(
    session: Session,
    library_id: int,
    tree_data: str
):
    """
    Update the pre-computed series tree cache for a library.

    Args:
        session: Database session
        library_id: Library ID
        tree_data: JSON string containing the serialized tree structure
    """
    library = get_library_by_id(session, library_id)
    if library:
        library.cached_series_tree = tree_data
        library.tree_cache_updated_at = int(time.time())
        library.updated_at = int(time.time())
        session.flush()  # Flush changes without committing

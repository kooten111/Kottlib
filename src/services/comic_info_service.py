"""
Comic Info Service

Provides shared logic for retrieving comic metadata used by both V1 and V2 API routers.
This reduces duplication between legacy_v1.py and v2/comics.py.
"""

from typing import Optional, Tuple
from pathlib import Path
import logging

from sqlalchemy.orm import Session

from ..database.operations import (
    get_comic_by_id,
    get_library_by_id,
    get_reading_progress,
)
from ..database.models import Comic, Library, ReadingProgress, User

logger = logging.getLogger(__name__)


class ComicMetadata:
    """
    Container for comic metadata used by both V1 and V2 APIs.
    
    This class holds all the data needed by both API versions, allowing
    them to format it differently without duplicating the data fetching logic.
    """
    
    def __init__(
        self,
        comic: Comic,
        library: Library,
        progress: Optional[ReadingProgress] = None,
        relative_path: Optional[str] = None,
        prev_comic_id: Optional[int] = None,
        next_comic_id: Optional[int] = None
    ):
        self.comic = comic
        self.library = library
        self.progress = progress
        self.relative_path = relative_path
        self.prev_comic_id = prev_comic_id
        self.next_comic_id = next_comic_id
    
    @property
    def current_page(self) -> int:
        """Get current reading page (0 if not started)."""
        return self.progress.current_page if self.progress else 0
    
    @property
    def is_completed(self) -> bool:
        """Check if comic is marked as completed."""
        return self.progress.is_completed if self.progress else False
    
    @property
    def progress_percent(self) -> int:
        """Get reading progress percentage."""
        return self.progress.progress_percent if self.progress else 0
    
    @property
    def has_been_opened(self) -> bool:
        """Check if comic has been opened before."""
        return self.current_page > 0
    
    @property
    def is_manga(self) -> bool:
        """Check if comic should be read right-to-left."""
        return self.comic.reading_direction == 'rtl' if hasattr(self.comic, 'reading_direction') else False


def get_comic_metadata(
    session: Session,
    library_id: int,
    comic_id: int,
    user: Optional[User] = None,
    include_navigation: bool = False
) -> ComicMetadata:
    """
    Get comic metadata for API responses.
    
    Fetches comic, library, and reading progress data in a single function.
    This is used by both V1 and V2 API endpoints to avoid duplication.
    
    Args:
        session: Database session
        library_id: Library ID
        comic_id: Comic ID
        user: Optional user for reading progress
        include_navigation: Whether to fetch prev/next comic IDs
    
    Returns:
        ComicMetadata object containing all fetched data
    
    Raises:
        ValueError: If library or comic not found
    """
    logger.debug(f"Fetching comic metadata: library_id={library_id}, comic_id={comic_id}")
    
    # Get library
    library = get_library_by_id(session, library_id)
    if not library:
        logger.error(f"Library not found: library_id={library_id}")
        raise ValueError(f"Library not found: {library_id}")
    
    logger.debug(f"Library found: name={library.name}, path={library.path}")
    
    # Get comic
    comic = get_comic_by_id(session, comic_id)
    if not comic:
        logger.error(f"Comic not found: comic_id={comic_id}")
        raise ValueError(f"Comic not found: {comic_id}")
    
    logger.debug(f"Comic found: filename={comic.filename}, num_pages={comic.num_pages}")
    
    # Get reading progress
    progress = None
    if user:
        progress = get_reading_progress(session, user.id, comic_id)
        if progress:
            logger.debug(f"Reading progress found: current_page={progress.current_page}, is_completed={progress.is_completed}")
        else:
            logger.debug(f"No reading progress found for user_id={user.id}, comic_id={comic_id}")
    
    # Calculate relative path
    relative_path = None
    try:
        relative_path = str(Path(comic.path).relative_to(library.path))
        logger.debug(f"Calculated relative path: {relative_path}")
    except ValueError as e:
        logger.warning(f"Failed to calculate relative path: {e}, using filename as fallback")
        relative_path = comic.filename  # Fallback
    
    # Get navigation (prev/next) if requested
    prev_comic_id = None
    next_comic_id = None
    if include_navigation:
        from .database import get_sibling_comics
        try:
            prev_comic_id, next_comic_id = get_sibling_comics(session, comic_id)
        except Exception as e:
            logger.warning(f"Failed to get sibling comics: {e}")
    
    return ComicMetadata(
        comic=comic,
        library=library,
        progress=progress,
        relative_path=relative_path,
        prev_comic_id=prev_comic_id,
        next_comic_id=next_comic_id
    )


def get_comic_cover_hash(
    session: Session,
    comic_id: int
) -> Optional[str]:
    """
    Get cover hash for a comic.
    
    Simple utility to fetch just the hash without other metadata.
    
    Args:
        session: Database session
        comic_id: Comic ID
    
    Returns:
        Comic hash string or None if not found
    """
    comic = get_comic_by_id(session, comic_id)
    if comic:
        return comic.hash
    return None

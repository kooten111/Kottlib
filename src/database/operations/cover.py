"""
Cover database operations.
"""

import time
import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from ..models import Cover


logger = logging.getLogger(__name__)


def create_cover(
    session: Session,
    comic_id: int,
    cover_type: str,
    page_number: int,
    jpeg_path: str,
    webp_path: Optional[str] = None,
    source: str = 'archive',
    source_url: Optional[str] = None
) -> Cover:
    """
    Create a new cover entry.

    Args:
        session: Database session
        comic_id: Comic ID
        cover_type: Type of cover ('auto' or 'custom')
        page_number: Page number used for cover (0-indexed)
        jpeg_path: Path to JPEG thumbnail
        webp_path: Path to WebP thumbnail (optional)
        source: Source of the cover ('archive', 'mangadex', 'upload')
        source_url: Original URL for external covers (optional)

    Returns:
        Cover object
    """
    now = int(time.time())

    # Check if cover of this type already exists
    existing_cover = session.query(Cover).filter_by(
        comic_id=comic_id,
        type=cover_type
    ).first()

    if existing_cover:
        # Update existing
        existing_cover.page_number = page_number
        existing_cover.jpeg_path = jpeg_path
        existing_cover.webp_path = webp_path
        existing_cover.generated_at = now
        existing_cover.source = source
        existing_cover.source_url = source_url

        session.flush()  # Flush changes without committing
        return existing_cover

    # Create new
    cover = Cover(
        comic_id=comic_id,
        type=cover_type,
        page_number=page_number,
        jpeg_path=jpeg_path,
        webp_path=webp_path,
        generated_at=now,
        source=source,
        source_url=source_url
    )

    session.add(cover)
    session.flush()  # Flush to get the ID without committing

    logger.debug(f"Created {cover_type} cover for comic {comic_id} from page {page_number}")
    return cover


def get_cover(session: Session, comic_id: int, cover_type: str = 'auto') -> Optional[Cover]:
    """
    Get cover for a comic.

    Args:
        session: Database session
        comic_id: Comic ID
        cover_type: Type of cover ('auto' or 'custom')

    Returns:
        Cover object or None
    """
    return session.query(Cover).filter_by(
        comic_id=comic_id,
        type=cover_type
    ).first()


def get_best_cover(session: Session, comic_id: int) -> Optional[Cover]:
    """
    Get the best cover for a comic (custom if available, otherwise auto).

    Args:
        session: Database session
        comic_id: Comic ID

    Returns:
        Cover object or None
    """
    # Try custom first
    custom = get_cover(session, comic_id, 'custom')
    if custom:
        return custom

    # Fall back to auto
    return get_cover(session, comic_id, 'auto')


def delete_cover(session: Session, comic_id: int, cover_type: str):
    """
    Delete a cover.

    Args:
        session: Database session
        comic_id: Comic ID
        cover_type: Type of cover to delete
    """
    cover = get_cover(session, comic_id, cover_type)
    if cover:
        # Delete files
        jpeg_path = Path(cover.jpeg_path)
        if jpeg_path.exists():
            jpeg_path.unlink()

        if cover.webp_path:
            webp_path = Path(cover.webp_path)
            if webp_path.exists():
                webp_path.unlink()

        # Delete from database
        session.delete(cover)
        session.flush()  # Flush changes without committing
        logger.debug(f"Deleted {cover_type} cover for comic {comic_id}")

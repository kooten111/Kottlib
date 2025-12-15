"""
Reading progress database operations.
"""

import time
import logging
from typing import Optional, List

from sqlalchemy.orm import Session

from ..models import ReadingProgress, Comic


logger = logging.getLogger(__name__)


def update_reading_progress(
    session: Session,
    user_id: int,
    comic_id: int,
    current_page: int,
    total_pages: int
) -> ReadingProgress:
    """
    Update or create reading progress for a comic.

    Args:
        session: Database session
        user_id: User ID
        comic_id: Comic ID
        current_page: Current page number (0-indexed)
        total_pages: Total number of pages

    Returns:
        ReadingProgress object
    """
    now = int(time.time())

    # Calculate progress percentage
    progress_percent = (current_page / total_pages * 100) if total_pages > 0 else 0
    is_completed = current_page >= total_pages - 1  # Last page

    # Get existing progress or create new
    progress = session.query(ReadingProgress).filter_by(
        user_id=user_id,
        comic_id=comic_id
    ).first()

    if progress:
        # Update existing
        progress.current_page = current_page
        progress.total_pages = total_pages
        progress.progress_percent = progress_percent
        progress.last_read_at = now

        if is_completed and not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = now
    else:
        # Create new
        progress = ReadingProgress(
            user_id=user_id,
            comic_id=comic_id,
            current_page=current_page,
            total_pages=total_pages,
            progress_percent=progress_percent,
            is_completed=is_completed,
            started_at=now,
            last_read_at=now,
            completed_at=now if is_completed else None
        )
        session.add(progress)

    session.flush()  # Flush changes without committing

    logger.debug(f"Updated reading progress for comic {comic_id}: page {current_page}/{total_pages}")
    return progress


def get_reading_progress(
    session: Session,
    user_id: int,
    comic_id: int
) -> Optional[ReadingProgress]:
    """Get reading progress for a specific comic."""
    logger.debug(f"[DB] get_reading_progress: user_id={user_id}, comic_id={comic_id}")
    result = session.query(ReadingProgress).filter_by(
        user_id=user_id,
        comic_id=comic_id
    ).first()
    if result:
        logger.debug(f"[DB] Reading progress found: current_page={result.current_page}, total_pages={result.total_pages}, progress={result.progress_percent}%, completed={result.is_completed}")
    else:
        logger.debug(f"[DB] No reading progress found for user_id={user_id}, comic_id={comic_id}")
    return result


def get_continue_reading(
    session: Session,
    user_id: int,
    limit: int = 10
) -> List[tuple[ReadingProgress, Comic]]:
    """
    Get recently read comics for "continue reading" feature.

    Args:
        session: Database session
        user_id: User ID
        limit: Maximum number of results (default: 10)

    Returns:
        List of tuples (ReadingProgress, Comic) ordered by most recently read
    """
    results = session.query(ReadingProgress, Comic).join(
        Comic, ReadingProgress.comic_id == Comic.id
    ).filter(
        ReadingProgress.user_id == user_id,
        ReadingProgress.is_completed == False  # Only in-progress comics
    ).order_by(
        ReadingProgress.last_read_at.desc()
    ).limit(limit).all()

    return results


def get_recently_completed(
    session: Session,
    user_id: int,
    limit: int = 10
) -> List[tuple[ReadingProgress, Comic]]:
    """
    Get recently completed comics.

    Args:
        session: Database session
        user_id: User ID
        limit: Maximum number of results (default: 10)

    Returns:
        List of tuples (ReadingProgress, Comic) ordered by most recently completed
    """
    results = session.query(ReadingProgress, Comic).join(
        Comic, ReadingProgress.comic_id == Comic.id
    ).filter(
        ReadingProgress.user_id == user_id,
        ReadingProgress.is_completed == True
    ).order_by(
        ReadingProgress.completed_at.desc()
    ).limit(limit).all()

    return results

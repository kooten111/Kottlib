"""
Favorites database operations.
"""

import time
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from ..models import Favorite, Comic


logger = logging.getLogger(__name__)


def add_favorite(session: Session, user_id: int, library_id: int, comic_id: int):
    """
    Add a comic to user's favorites.

    Args:
        session: Database session
        user_id: User ID
        library_id: Library ID
        comic_id: Comic ID

    Returns:
        Favorite object
    """
    # Check if already favorited
    existing = session.query(Favorite).filter_by(
        user_id=user_id,
        comic_id=comic_id
    ).first()

    if existing:
        return existing

    favorite = Favorite(
        user_id=user_id,
        library_id=library_id,
        comic_id=comic_id,
        created_at=int(time.time())
    )

    session.add(favorite)
    session.flush()  # Flush to get the ID without committing
    logger.debug(f"Added favorite: user={user_id}, comic={comic_id}")
    return favorite


def remove_favorite(session: Session, user_id: int, comic_id: int) -> bool:
    """
    Remove a comic from user's favorites.

    Args:
        session: Database session
        user_id: User ID
        comic_id: Comic ID

    Returns:
        True if removed, False if not found
    """
    favorite = session.query(Favorite).filter_by(
        user_id=user_id,
        comic_id=comic_id
    ).first()

    if favorite:
        session.delete(favorite)
        session.flush()  # Flush changes without committing
        logger.debug(f"Removed favorite: user={user_id}, comic={comic_id}")
        return True

    return False


def get_user_favorites(session: Session, user_id: int, library_id: Optional[int] = None) -> List[Favorite]:
    """
    Get all favorites for a user, optionally filtered by library.

    Args:
        session: Database session
        user_id: User ID
        library_id: Optional library ID to filter

    Returns:
        List of Favorite objects
    """
    query = session.query(Favorite).filter(Favorite.user_id == user_id)
    if library_id is not None:
        query = query.filter(Favorite.library_id == library_id)
    return query.order_by(Favorite.created_at.desc()).all()


def is_favorite(session: Session, user_id: int, comic_id: int) -> bool:
    """
    Check if a comic is in user's favorites.

    Args:
        session: Database session
        user_id: User ID
        comic_id: Comic ID

    Returns:
        True if favorited, False otherwise
    """
    count = session.query(Favorite).filter_by(
        user_id=user_id,
        comic_id=comic_id
    ).count()

    return count > 0

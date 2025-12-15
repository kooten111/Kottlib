"""
Reading lists database operations.
"""

import time
import logging
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from ..models import ReadingList, ReadingListItem, Comic


logger = logging.getLogger(__name__)


def create_reading_list(
    session: Session,
    library_id: int,
    name: str,
    user_id: Optional[int] = None,
    description: Optional[str] = None,
    is_public: bool = False
) -> ReadingList:
    """
    Create a new reading list.

    Args:
        session: Database session
        library_id: Library ID
        name: Reading list name
        user_id: Owner user ID (optional for public lists)
        description: Description (optional)
        is_public: Whether list is public

    Returns:
        ReadingList object
    """
    reading_list = ReadingList(
        library_id=library_id,
        user_id=user_id,
        name=name,
        description=description,
        is_public=is_public,
        position=0,
        created_at=int(time.time()),
        updated_at=int(time.time())
    )

    session.add(reading_list)
    session.flush()  # Flush to get the ID without committing
    logger.debug(f"Created reading list: library={library_id}, name={name}")
    return reading_list


def get_reading_list_by_id(session: Session, list_id: int) -> Optional[ReadingList]:
    """
    Get reading list by ID.

    Args:
        session: Database session
        list_id: Reading list ID

    Returns:
        ReadingList object or None
    """
    return session.query(ReadingList).filter_by(id=list_id).first()


def get_reading_lists_in_library(session: Session, library_id: int, user_id: Optional[int] = None) -> List[ReadingList]:
    """
    Get all reading lists in a library.

    Args:
        session: Database session
        library_id: Library ID
        user_id: Filter by user ID (optional, includes public lists)

    Returns:
        List of ReadingList objects
    """
    query = session.query(ReadingList).filter_by(library_id=library_id)

    if user_id is not None:
        # Get user's lists + public lists
        query = query.filter(
            or_(
                ReadingList.user_id == user_id,
                ReadingList.is_public == True
            )
        )
    else:
        # Get all public lists
        query = query.filter(ReadingList.is_public == True)

    return query.order_by(ReadingList.position, ReadingList.name).all()


def delete_reading_list(session: Session, list_id: int) -> bool:
    """
    Delete a reading list.

    Args:
        session: Database session
        list_id: Reading list ID

    Returns:
        True if deleted, False if not found
    """
    reading_list = get_reading_list_by_id(session, list_id)
    if reading_list:
        session.delete(reading_list)
        session.flush()  # Flush changes without committing
        logger.debug(f"Deleted reading list: id={list_id}")
        return True

    return False


def add_comic_to_reading_list(session: Session, list_id: int, comic_id: int, position: Optional[int] = None):
    """
    Add a comic to a reading list.

    Args:
        session: Database session
        list_id: Reading list ID
        comic_id: Comic ID
        position: Position in list (optional, appends to end if not specified)

    Returns:
        ReadingListItem object
    """
    # Check if already in list
    existing = session.query(ReadingListItem).filter_by(
        reading_list_id=list_id,
        comic_id=comic_id
    ).first()

    if existing:
        return existing

    # Get next position if not specified
    if position is None:
        max_position = session.query(func.max(ReadingListItem.position)).filter_by(
            reading_list_id=list_id
        ).scalar() or -1
        position = max_position + 1

    item = ReadingListItem(
        reading_list_id=list_id,
        comic_id=comic_id,
        position=position,
        added_at=int(time.time())
    )

    session.add(item)
    session.flush()  # Flush to get the ID without committing
    logger.debug(f"Added comic to reading list: list={list_id}, comic={comic_id}, position={position}")
    return item


def remove_comic_from_reading_list(session: Session, list_id: int, comic_id: int) -> bool:
    """
    Remove a comic from a reading list.

    Args:
        session: Database session
        list_id: Reading list ID
        comic_id: Comic ID

    Returns:
        True if removed, False if not found
    """
    item = session.query(ReadingListItem).filter_by(
        reading_list_id=list_id,
        comic_id=comic_id
    ).first()

    if item:
        session.delete(item)
        session.flush()  # Flush changes without committing
        logger.debug(f"Removed comic from reading list: list={list_id}, comic={comic_id}")
        return True

    return False


def get_reading_list_comics(session: Session, list_id: int) -> List[Comic]:
    """
    Get all comics in a reading list (ordered by position).

    Args:
        session: Database session
        list_id: Reading list ID

    Returns:
        List of Comic objects in order
    """
    comics = session.query(Comic).join(ReadingListItem).filter(
        ReadingListItem.reading_list_id == list_id
    ).order_by(ReadingListItem.position).all()

    return comics

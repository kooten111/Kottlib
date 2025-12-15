"""
Labels/Tags database operations.
"""

import time
import logging
from typing import Optional, List

from sqlalchemy.orm import Session

from ..models import Label, ComicLabel, Comic


logger = logging.getLogger(__name__)


def create_label(session: Session, library_id: int, name: str, color_id: int = 0) -> Label:
    """
    Create a new label/tag.

    Args:
        session: Database session
        library_id: Library ID
        name: Label name
        color_id: Color identifier (default: 0)

    Returns:
        Label object
    """
    # Check if label already exists
    existing = session.query(Label).filter_by(
        library_id=library_id,
        name=name
    ).first()

    if existing:
        return existing

    label = Label(
        library_id=library_id,
        name=name,
        color_id=color_id,
        position=0,
        created_at=int(time.time()),
        updated_at=int(time.time())
    )

    session.add(label)
    session.flush()  # Flush to get the ID without committing
    logger.debug(f"Created label: library={library_id}, name={name}")
    return label


def get_label_by_id(session: Session, label_id: int) -> Optional[Label]:
    """
    Get label by ID.

    Args:
        session: Database session
        label_id: Label ID

    Returns:
        Label object or None
    """
    return session.query(Label).filter_by(id=label_id).first()


def get_labels_in_library(session: Session, library_id: int) -> List[Label]:
    """
    Get all labels in a library.

    Args:
        session: Database session
        library_id: Library ID

    Returns:
        List of Label objects
    """
    return session.query(Label).filter_by(library_id=library_id).order_by(Label.position, Label.name).all()


def delete_label(session: Session, label_id: int) -> bool:
    """
    Delete a label.

    Args:
        session: Database session
        label_id: Label ID

    Returns:
        True if deleted, False if not found
    """
    label = get_label_by_id(session, label_id)
    if label:
        session.delete(label)
        session.flush()  # Flush changes without committing
        logger.debug(f"Deleted label: id={label_id}")
        return True

    return False


def add_label_to_comic(session: Session, comic_id: int, label_id: int):
    """
    Add a label to a comic.

    Args:
        session: Database session
        comic_id: Comic ID
        label_id: Label ID

    Returns:
        ComicLabel object
    """
    # Check if already labeled
    existing = session.query(ComicLabel).filter_by(
        comic_id=comic_id,
        label_id=label_id
    ).first()

    if existing:
        return existing

    comic_label = ComicLabel(
        comic_id=comic_id,
        label_id=label_id,
        created_at=int(time.time())
    )

    session.add(comic_label)
    session.flush()  # Flush to get the ID without committing
    logger.debug(f"Added label to comic: comic={comic_id}, label={label_id}")
    return comic_label


def remove_label_from_comic(session: Session, comic_id: int, label_id: int) -> bool:
    """
    Remove a label from a comic.

    Args:
        session: Database session
        comic_id: Comic ID
        label_id: Label ID

    Returns:
        True if removed, False if not found
    """
    comic_label = session.query(ComicLabel).filter_by(
        comic_id=comic_id,
        label_id=label_id
    ).first()

    if comic_label:
        session.delete(comic_label)
        session.flush()  # Flush changes without committing
        logger.debug(f"Removed label from comic: comic={comic_id}, label={label_id}")
        return True

    return False


def get_comics_with_label(session: Session, label_id: int) -> List[Comic]:
    """
    Get all comics with a specific label.

    Args:
        session: Database session
        label_id: Label ID

    Returns:
        List of Comic objects
    """
    comics = session.query(Comic).join(ComicLabel).filter(
        ComicLabel.label_id == label_id
    ).all()

    return comics


def get_comic_labels(session: Session, comic_id: int) -> List[Label]:
    """
    Get all labels for a comic.

    Args:
        session: Database session
        comic_id: Comic ID

    Returns:
        List of Label objects
    """
    labels = session.query(Label).join(ComicLabel).filter(
        ComicLabel.comic_id == comic_id
    ).all()

    return labels

"""
Reading Service

Reading progress and user interaction operations including:
- Reading progress tracking
- Favorites management
- Labels management
- Reading lists management
"""

import logging
import time
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from ..database.models import (
    Comic, ReadingProgress, Favorite, Label, ComicLabel,
    ReadingList, ReadingListItem, User
)

logger = logging.getLogger(__name__)


def update_reading_progress(
    session: Session,
    user_id: int,
    comic_id: int,
    current_page: int,
    total_pages: Optional[int] = None
) -> Dict[str, Any]:
    """
    Update reading progress for a user on a comic.
    
    Args:
        session: Database session
        user_id: User ID
        comic_id: Comic ID
        current_page: Current page number
        total_pages: Total pages (optional)
        
    Returns:
        Dictionary with updated progress info
    """
    # Get or create progress record
    progress = session.query(ReadingProgress).filter(
        ReadingProgress.user_id == user_id,
        ReadingProgress.comic_id == comic_id
    ).first()
    
    if not progress:
        progress = ReadingProgress(
            user_id=user_id,
            comic_id=comic_id,
            current_page=current_page,
            updated_at=int(time.time())
        )
        session.add(progress)
    else:
        progress.current_page = current_page
        progress.updated_at = int(time.time())
        
    if total_pages is not None:
        progress.total_pages = total_pages
        
    session.commit()
    
    return {
        "user_id": user_id,
        "comic_id": comic_id,
        "current_page": current_page,
        "total_pages": progress.total_pages,
        "updated_at": progress.updated_at,
    }


def get_continue_reading(
    session: Session,
    user_id: int,
    library_id: Optional[int] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get comics that a user is currently reading.
    
    Args:
        session: Database session
        user_id: User ID
        library_id: Optional library ID to filter by
        limit: Maximum number of results
        
    Returns:
        List of comics with reading progress
    """
    query = session.query(ReadingProgress, Comic).join(
        Comic, ReadingProgress.comic_id == Comic.id
    ).filter(
        ReadingProgress.user_id == user_id,
        ReadingProgress.current_page > 0
    )
    
    if library_id:
        query = query.filter(Comic.library_id == library_id)
        
    # Order by most recently updated
    query = query.order_by(ReadingProgress.updated_at.desc()).limit(limit)
    
    results = []
    for progress, comic in query.all():
        results.append({
            "comic_id": comic.id,
            "comic": comic,
            "current_page": progress.current_page,
            "total_pages": progress.total_pages,
            "updated_at": progress.updated_at,
        })
        
    return results


# ============================================================================
# Favorites
# ============================================================================

def get_user_favorites(session: Session, user_id: int) -> List[Dict[str, Any]]:
    """Get all favorites for a user."""
    favorites = session.query(Favorite).filter(Favorite.user_id == user_id).all()
    
    return [
        {
            "comic_id": f.comic_id,
            "library_id": f.library_id,
            "created_at": f.created_at,
        }
        for f in favorites
    ]


def add_to_favorites(
    session: Session,
    user_id: int,
    comic_id: int
) -> Dict[str, Any]:
    """
    Add a comic to user's favorites.
    
    Args:
        session: Database session
        user_id: User ID
        comic_id: Comic ID
        
    Returns:
        Dictionary with success status
        
    Raises:
        ValueError: If comic not found
    """
    # Check if comic exists
    comic = session.query(Comic).filter(Comic.id == comic_id).first()
    if not comic:
        raise ValueError(f"Comic {comic_id} not found")
        
    # Check if already favorite
    existing = session.query(Favorite).filter(
        Favorite.user_id == user_id,
        Favorite.comic_id == comic_id
    ).first()
    
    if existing:
        return {"success": True, "message": "Already in favorites"}
        
    favorite = Favorite(
        user_id=user_id,
        library_id=comic.library_id,
        comic_id=comic_id,
        created_at=int(time.time())
    )
    session.add(favorite)
    session.commit()
    
    return {"success": True, "message": "Added to favorites"}


def remove_from_favorites(
    session: Session,
    user_id: int,
    comic_id: int
) -> Dict[str, Any]:
    """Remove a comic from user's favorites."""
    favorite = session.query(Favorite).filter(
        Favorite.user_id == user_id,
        Favorite.comic_id == comic_id
    ).first()
    
    if not favorite:
        return {"success": False, "message": "Not in favorites"}
        
    session.delete(favorite)
    session.commit()
    
    return {"success": True, "message": "Removed from favorites"}


# ============================================================================
# Labels
# ============================================================================

def get_user_labels(session: Session, user_id: int) -> List[Dict[str, Any]]:
    """Get all labels for a user."""
    labels = session.query(Label).filter(Label.user_id == user_id).all()
    
    return [
        {
            "id": label.id,
            "name": label.name,
            "color_id": label.color_id,
        }
        for label in labels
    ]


def create_label(
    session: Session,
    user_id: int,
    name: str,
    color_id: int = 0
) -> Dict[str, Any]:
    """Create a new label for a user."""
    label = Label(
        user_id=user_id,
        name=name,
        color_id=color_id
    )
    session.add(label)
    session.commit()
    
    return {
        "id": label.id,
        "name": label.name,
        "color_id": label.color_id,
    }


def add_label_to_comic(
    session: Session,
    user_id: int,
    comic_id: int,
    label_id: int
) -> Dict[str, Any]:
    """
    Add a label to a comic.
    
    Args:
        session: Database session
        user_id: User ID (for verification)
        comic_id: Comic ID
        label_id: Label ID
        
    Returns:
        Dictionary with success status
        
    Raises:
        ValueError: If comic or label not found, or label doesn't belong to user
    """
    # Verify label belongs to user
    label = session.query(Label).filter(
        Label.id == label_id,
        Label.user_id == user_id
    ).first()
    
    if not label:
        raise ValueError("Label not found or doesn't belong to user")
        
    # Verify comic exists
    comic = session.query(Comic).filter(Comic.id == comic_id).first()
    if not comic:
        raise ValueError(f"Comic {comic_id} not found")
        
    # Check if already labeled
    existing = session.query(ComicLabel).filter(
        ComicLabel.comic_id == comic_id,
        ComicLabel.label_id == label_id
    ).first()
    
    if existing:
        return {"success": True, "message": "Label already applied"}
        
    comic_label = ComicLabel(
        comic_id=comic_id,
        label_id=label_id
    )
    session.add(comic_label)
    session.commit()
    
    return {"success": True, "message": "Label added"}


def remove_label_from_comic(
    session: Session,
    user_id: int,
    comic_id: int,
    label_id: int
) -> Dict[str, Any]:
    """Remove a label from a comic."""
    # Verify label belongs to user
    label = session.query(Label).filter(
        Label.id == label_id,
        Label.user_id == user_id
    ).first()
    
    if not label:
        raise ValueError("Label not found or doesn't belong to user")
        
    comic_label = session.query(ComicLabel).filter(
        ComicLabel.comic_id == comic_id,
        ComicLabel.label_id == label_id
    ).first()
    
    if not comic_label:
        return {"success": False, "message": "Label not applied to comic"}
        
    session.delete(comic_label)
    session.commit()
    
    return {"success": True, "message": "Label removed"}


# ============================================================================
# Reading Lists
# ============================================================================

def get_user_reading_lists(
    session: Session,
    user_id: int,
    include_public: bool = False
) -> List[Dict[str, Any]]:
    """Get all reading lists for a user."""
    query = session.query(ReadingList)
    
    if include_public:
        query = query.filter(
            (ReadingList.user_id == user_id) | (ReadingList.is_public == True)
        )
    else:
        query = query.filter(ReadingList.user_id == user_id)
        
    lists = query.all()
    
    return [
        {
            "id": rl.id,
            "name": rl.name,
            "description": rl.description,
            "is_public": rl.is_public,
            "created_at": rl.created_at,
        }
        for rl in lists
    ]


def create_reading_list(
    session: Session,
    user_id: int,
    name: str,
    description: Optional[str] = None,
    is_public: bool = False
) -> Dict[str, Any]:
    """Create a new reading list."""
    reading_list = ReadingList(
        user_id=user_id,
        name=name,
        description=description,
        is_public=is_public,
        created_at=int(time.time())
    )
    session.add(reading_list)
    session.commit()
    
    return {
        "id": reading_list.id,
        "name": reading_list.name,
        "description": reading_list.description,
        "is_public": reading_list.is_public,
        "created_at": reading_list.created_at,
    }


def add_comic_to_reading_list(
    session: Session,
    user_id: int,
    reading_list_id: int,
    comic_id: int
) -> Dict[str, Any]:
    """
    Add a comic to a reading list.
    
    Args:
        session: Database session
        user_id: User ID (for verification)
        reading_list_id: Reading list ID
        comic_id: Comic ID
        
    Returns:
        Dictionary with success status
        
    Raises:
        ValueError: If list or comic not found, or list doesn't belong to user
    """
    # Verify reading list belongs to user
    reading_list = session.query(ReadingList).filter(
        ReadingList.id == reading_list_id,
        ReadingList.user_id == user_id
    ).first()
    
    if not reading_list:
        raise ValueError("Reading list not found or doesn't belong to user")
        
    # Verify comic exists
    comic = session.query(Comic).filter(Comic.id == comic_id).first()
    if not comic:
        raise ValueError(f"Comic {comic_id} not found")
        
    # Check if already in list
    existing = session.query(ReadingListItem).filter(
        ReadingListItem.reading_list_id == reading_list_id,
        ReadingListItem.comic_id == comic_id
    ).first()
    
    if existing:
        return {"success": True, "message": "Comic already in reading list"}
        
    # Get current max position
    max_position = session.query(ReadingListItem).filter(
        ReadingListItem.reading_list_id == reading_list_id
    ).count()
    
    item = ReadingListItem(
        reading_list_id=reading_list_id,
        comic_id=comic_id,
        position=max_position,
        added_at=int(time.time())
    )
    session.add(item)
    session.commit()
    
    return {"success": True, "message": "Comic added to reading list"}


def remove_comic_from_reading_list(
    session: Session,
    user_id: int,
    reading_list_id: int,
    comic_id: int
) -> Dict[str, Any]:
    """Remove a comic from a reading list."""
    # Verify reading list belongs to user
    reading_list = session.query(ReadingList).filter(
        ReadingList.id == reading_list_id,
        ReadingList.user_id == user_id
    ).first()
    
    if not reading_list:
        raise ValueError("Reading list not found or doesn't belong to user")
        
    item = session.query(ReadingListItem).filter(
        ReadingListItem.reading_list_id == reading_list_id,
        ReadingListItem.comic_id == comic_id
    ).first()
    
    if not item:
        return {"success": False, "message": "Comic not in reading list"}
        
    session.delete(item)
    session.commit()
    
    return {"success": True, "message": "Comic removed from reading list"}

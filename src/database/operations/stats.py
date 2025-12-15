"""
Statistics database operations.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import Comic, Folder


def get_library_stats(session: Session, library_id: int) -> dict:
    """Get statistics for a library."""
    comic_count = session.query(func.count(Comic.id)).filter_by(library_id=library_id).scalar()
    folder_count = session.query(func.count(Folder.id)).filter_by(library_id=library_id).scalar()

    return {
        'comic_count': comic_count or 0,
        'folder_count': folder_count or 0,
    }

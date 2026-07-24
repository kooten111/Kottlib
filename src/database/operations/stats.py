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


def get_all_library_stats(session: Session) -> dict:
    """
    Batch comic/folder counts for all libraries in two grouped queries.

    Returns:
        Dict mapping library_id -> {'comic_count': int, 'folder_count': int}
    """
    comic_rows = session.query(
        Comic.library_id,
        func.count(Comic.id),
    ).group_by(Comic.library_id).all()
    folder_rows = session.query(
        Folder.library_id,
        func.count(Folder.id),
    ).group_by(Folder.library_id).all()

    stats = {}
    for library_id, count in comic_rows:
        if library_id is None:
            continue
        stats.setdefault(library_id, {'comic_count': 0, 'folder_count': 0})
        stats[library_id]['comic_count'] = count or 0
    for library_id, count in folder_rows:
        if library_id is None:
            continue
        stats.setdefault(library_id, {'comic_count': 0, 'folder_count': 0})
        stats[library_id]['folder_count'] = count or 0
    return stats

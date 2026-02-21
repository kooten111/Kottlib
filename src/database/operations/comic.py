"""
Comic database operations.
"""

import time
import logging
from pathlib import Path
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import text

from ..models import Comic, Series as SeriesModel

# Import series utilities
try:
    from ...utils.series_utils import get_series_name_from_comic
    from ...utils.sorting import natural_filename_sort_key
except ImportError:
    from utils.series_utils import get_series_name_from_comic
    from utils.sorting import natural_filename_sort_key


logger = logging.getLogger(__name__)


def create_comic(
    session: Session,
    library_id: int,
    path: str,
    filename: str,
    file_hash: str,
    file_size: int,
    file_modified_at: int,
    format: str,
    num_pages: int,
    folder_id: Optional[int] = None,
    **metadata
) -> Comic:
    """Create a new comic entry."""
    now = int(time.time())

    if "summary" in metadata and "description" not in metadata:
        metadata["description"] = metadata.pop("summary")

    # Get IMMEDIATE parent folder name for series
    # The folder containing the comic IS the series
    # Example: "Batman/Night of Owls/Batman Vol 1.cbz"
    #   -> SERIES = "Night of Owls" (immediate parent)
    # Example: "Berserk/Berserk v01.cbz"
    #   -> SERIES = "Berserk" (immediate parent)
    immediate_folder_name = None
    if folder_id:
        result = session.execute(
            text("SELECT name FROM folders WHERE id = :folder_id"),
            {"folder_id": folder_id}
        ).fetchone()

        if result:
            immediate_folder_name = result[0]


    # Create comic with metadata
    comic = Comic(
        library_id=library_id,
        folder_id=folder_id,
        path=str(Path(path).resolve()),
        filename=filename,
        hash=file_hash,
        file_size=file_size,
        file_modified_at=file_modified_at,
        format=format,
        num_pages=num_pages,
        created_at=now,
        updated_at=now,
        **metadata
    )

    # Auto-populate series field from folder structure if not provided by ComicInfo.xml
    # Use immediate parent folder name (the folder IS the series)
    if not comic.series:
        comic.series = get_series_name_from_comic(comic, immediate_folder_name)

    session.add(comic)
    session.flush()  # Flush to get the ID without committing

    logger.debug(f"Created comic: {filename} (series: {comic.series})")
    return comic


def get_comic_by_id(session: Session, comic_id: int) -> Optional[Comic]:
    """Get comic by ID."""
    logger.debug(f"[DB] get_comic_by_id: comic_id={comic_id}")
    result = session.query(Comic).filter_by(id=comic_id).first()
    if result:
        logger.debug(f"[DB] Comic found: id={result.id}, filename={result.filename}, path={result.path}, num_pages={result.num_pages}")
    else:
        logger.debug(f"[DB] Comic not found: comic_id={comic_id}")
    return result


def get_comic_by_hash(session: Session, file_hash: str, library_id: Optional[int] = None) -> Optional[Comic]:
    """
    Get comic by file hash.

    Args:
        session: Database session
        file_hash: File hash to search for
        library_id: Optional library ID to filter by (allows same file in different libraries)
    """
    query = session.query(Comic).filter_by(hash=file_hash)
    if library_id is not None:
        query = query.filter_by(library_id=library_id)
    return query.first()


def get_comic_by_path_and_mtime(
    session: Session,
    path: str,
    file_modified_at: int,
    library_id: Optional[int] = None
) -> Optional[Comic]:
    """
    Get comic by file path and modification time (fast check before hashing).

    This is used to quickly skip unchanged files during re-scans without
    calculating expensive file hashes.

    Args:
        session: Database session
        path: Full file path to search for
        file_modified_at: File modification timestamp (Unix timestamp)
        library_id: Optional library ID to filter by

    Returns:
        Comic if found with matching path and mtime, None otherwise
    """
    query = session.query(Comic).filter_by(path=path, file_modified_at=file_modified_at)
    if library_id is not None:
        query = query.filter_by(library_id=library_id)
    return query.first()


def get_comics_in_library(session: Session, library_id: int) -> List[Comic]:
    """
    Get all comics in a library from the main database.
    """
    return session.query(Comic).filter_by(library_id=library_id).all()


def get_all_comics_in_db(session: Session) -> List[Comic]:
    """
    Get all comics from the database.
    """
    return session.query(Comic).all()


def get_comics_in_folder(session: Session, folder_id: int, library_id: Optional[int] = None) -> List[Comic]:
    """
    Get all comics in a folder.
    """
    query = session.query(Comic).filter_by(folder_id=folder_id)
    if library_id is not None:
        query = query.filter_by(library_id=library_id)
    return query.all()


def get_comics_in_folder_simple(session: Session, folder_id: int) -> List[Comic]:
    """
    Get all comics in a folder.
    """
    return session.query(Comic).filter_by(folder_id=folder_id).all()


def search_comics(
    session: Session,
    library_id: int,
    query_str: Optional[str] = None,
    query: Optional[str] = None,
) -> List[Comic]:
    """
    Search for comics in a library by metadata.

    Searches across multiple fields:
    - title
    - series
    - filename
    - writer
    - publisher
    - description
    - genre
    - characters
    - AND series table metadata (writer, artist, genre, tags, description, status)

    Args:
        session: Database session
        library_id: ID of the library to search in
        query_str: Search query string (case-insensitive)
        query: Backward-compatible alias for query_str

    Returns:
        List of matching comics, ordered by relevance (title/series matches first)
    """
    if query_str is None:
        query_str = query

    if not query_str or not query_str.strip():
        return []

    # Normalize search query (case-insensitive)
    search_pattern = f"%{query_str.strip()}%"

    # First, search for matching series
    series_matches = session.query(SeriesModel).filter(
        SeriesModel.library_id == library_id
    ).filter(
        (SeriesModel.name.ilike(search_pattern)) |
        (SeriesModel.display_name.ilike(search_pattern)) |
        (SeriesModel.writer.ilike(search_pattern)) |
        (SeriesModel.artist.ilike(search_pattern)) |
        (SeriesModel.genre.ilike(search_pattern)) |
        (SeriesModel.tags.ilike(search_pattern)) |
        (SeriesModel.description.ilike(search_pattern)) |
        (SeriesModel.publisher.ilike(search_pattern)) |
        (SeriesModel.status.ilike(search_pattern))
    ).all()

    # Get series names that matched
    matched_series_names = {series.name for series in series_matches}

    # Build query with OR conditions across multiple fields
    query = session.query(Comic).filter(
        Comic.library_id == library_id
    ).filter(
        (Comic.title.ilike(search_pattern)) |
        (Comic.series.ilike(search_pattern)) |
        # normalized_series_name removed
        (Comic.filename.ilike(search_pattern)) |
        (Comic.writer.ilike(search_pattern)) |
        (Comic.publisher.ilike(search_pattern)) |
        (Comic.description.ilike(search_pattern)) |
        (Comic.penciller.ilike(search_pattern)) |
        (Comic.inker.ilike(search_pattern)) |
        (Comic.colorist.ilike(search_pattern)) |
        (Comic.genre.ilike(search_pattern)) |
        (Comic.characters.ilike(search_pattern))
    )

    # Get results
    results = query.all()
    
    # Also add comics from matched series (if not already included)
    if matched_series_names:
        series_comics = session.query(Comic).filter(
            Comic.library_id == library_id,
            Comic.series.in_(matched_series_names)
        ).all()
        
        # Merge results, avoiding duplicates
        existing_ids = {comic.id for comic in results}
        for comic in series_comics:
            if comic.id not in existing_ids:
                results.append(comic)
                existing_ids.add(comic.id)

    # Sort results by relevance (series metadata > title > series > filename > others)
    def relevance_score(comic):
        q_lower = query_str.lower()
        score = 0
        
        # Highest priority: series-level metadata match
        comic_series_name = comic.series
        if comic_series_name and comic_series_name in matched_series_names:
            # Further boost if the query matches the series metadata directly
            for series in series_matches:
                if series.name == comic_series_name:
                    if series.writer and q_lower in series.writer.lower():
                        score += 200
                    if series.artist and q_lower in series.artist.lower():
                        score += 150
                    if series.genre and q_lower in series.genre.lower():
                        score += 120
                    if series.tags and q_lower in series.tags.lower():
                        score += 110
                    if series.name and q_lower in series.name.lower():
                        score += 100
                    if series.display_name and q_lower in series.display_name.lower():
                        score += 100
                    break
        
        # Comic-level field matches
        if comic.title and q_lower in comic.title.lower():
            score += 100
        if comic.series and q_lower in comic.series.lower():
            score += 50
        if comic.filename and q_lower in comic.filename.lower():
            score += 25
        return score

    results.sort(key=relevance_score, reverse=True)

    return results


def get_sibling_comics(session: Session, comic_id: int) -> tuple[Optional[int], Optional[int]]:
    """
    Get the previous and next comic IDs in the same folder.
    Returns (previous_comic_id, next_comic_id)

    Comics are ordered by natural filename order within the folder.
    This keeps numeric names in intuitive order (1, 2, 10).
    """
    comic = get_comic_by_id(session, comic_id)
    if not comic:
        return (None, None)

    # Get all comics in the same folder, then apply natural filename sort.
    # This ensures 1, 2, 10 ordering instead of 1, 10, 2.
    comics = (
        session.query(Comic)
        .filter_by(folder_id=comic.folder_id)
        .all()
    )
    comics.sort(key=lambda item: natural_filename_sort_key(item.filename or ""))

    # Find current comic's position
    current_index = None
    for i, c in enumerate(comics):
        if c.id == comic_id:
            current_index = i
            break

    if current_index is None:
        return (None, None)

    # Get previous and next
    prev_id = comics[current_index - 1].id if current_index > 0 else None
    next_id = comics[current_index + 1].id if current_index < len(comics) - 1 else None

    return (prev_id, next_id)

"""
Search Service

Search logic including:
- Basic comic search
- Full-text search
- Advanced search with filters
"""

import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from ..database import get_library_by_id
from ..database.enhanced_search import (
    search_with_fts,
    search_comics_advanced,
)

logger = logging.getLogger(__name__)


def search_comics(
    session: Session,
    library_id: int,
    query: str,
    limit: Optional[int] = None
) -> List[Any]:
    """
    Basic comic search using query string.
    
    Args:
        session: Database session
        library_id: Library ID to search in
        query: Search query string
        limit: Optional limit on number of results
        
    Returns:
        List of matching comics
        
    Raises:
        ValueError: If library not found
    """
    library = get_library_by_id(session, library_id)
    if not library:
        raise ValueError(f"Library {library_id} not found")
        
    # Use database layer search
    from ..database.models import Comic
    
    results = session.query(Comic).filter(
        Comic.library_id == library_id,
        Comic.filename.contains(query) | Comic.series.contains(query)
    )
    
    if limit:
        results = results.limit(limit)
        
    return results.all()


def search_comics_fts(
    session: Session,
    library_id: int,
    query: str
) -> List[Any]:
    """
    Full-text search for comics.
    
    Uses the FTS (Full-Text Search) index for better search results.
    
    Args:
        session: Database session
        library_id: Library ID to search in
        query: Search query string
        
    Returns:
        List of matching comics ordered by relevance
        
    Raises:
        ValueError: If library not found or query empty
    """
    if not query or not query.strip():
        return []
        
    library = get_library_by_id(session, library_id)
    if not library:
        raise ValueError(f"Library {library_id} not found")
        
    # Use enhanced search from database layer
    comics = search_with_fts(session, library_id, query)
    
    logger.info(f"FTS search in library {library_id} for '{query}' found {len(comics)} results")
    
    return comics


def advanced_search(
    session: Session,
    library_id: int,
    filters: Dict[str, Any],
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> Dict[str, Any]:
    """
    Advanced search with multiple filters.
    
    Args:
        session: Database session
        library_id: Library ID to search in
        filters: Dictionary of filters to apply
            Examples:
            - series: Series name
            - writer: Writer name
            - artist: Artist name
            - genre: Genre
            - year: Publication year
            - publisher: Publisher name
            - has_metadata: Boolean for metadata presence
        sort_by: Field to sort by
        sort_order: Sort order ('asc' or 'desc')
        limit: Maximum number of results
        offset: Number of results to skip
        
    Returns:
        Dictionary with:
        - results: List of matching comics
        - total: Total count of matches
        - limit: Applied limit
        - offset: Applied offset
        
    Raises:
        ValueError: If library not found
    """
    library = get_library_by_id(session, library_id)
    if not library:
        raise ValueError(f"Library {library_id} not found")
        
    # Use enhanced search from database layer
    results, total = search_comics_advanced(
        session,
        library_id,
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )
    
    logger.info(
        f"Advanced search in library {library_id} with filters {filters} "
        f"found {total} results (returning {len(results)})"
    )
    
    return {
        "results": results,
        "total": total,
        "limit": limit,
        "offset": offset or 0,
    }

"""
API v2 Router - Search

Endpoints for comic search functionality.
"""

import logging
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from ....database import (
    get_library_by_id,
    get_user_by_username,
    get_user_by_id,
    get_reading_progress,
)
from ....database.enhanced_search import (
    search_with_fts,
    search_series,
    search_comics_advanced,
    get_searchable_fields,
    parse_search_query,
)
from ....database.models import Folder as FolderModel
from ...middleware import get_current_user_id, get_request_user

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Search
# ============================================================================

@router.get("/library/{library_id}/search")
@router.post("/library/{library_id}/search")
async def search_comics_v2(
    library_id: int,
    request: Request,
    q: Optional[str] = None
):
    """
    Search for comics (v2 JSON format)

    Supports both GET and POST methods:
    - GET: query via ?q=search_term
    - POST: query via JSON body {"q": "search_term"} or form data

    Args:
        library_id: ID of the library to search in
        q: Search query string (GET parameter)

    Returns:
        JSON array of matching comics in same format as folder content
    """
    # Get query from GET parameter or POST body
    query = q

    # If it's a POST request and no query param, try to get from body
    if request.method == "POST" and not query:
        try:
            # Try to parse JSON body
            body = await request.json()
            # YACReader uses "query" field in POST body, but also support "q" for compatibility
            query = body.get("query", body.get("q", ""))
        except:
            # If JSON parsing fails, try form data
            try:
                form = await request.form()
                query = form.get("query", form.get("q", ""))
            except:
                pass

    if not query or not query.strip():
        return JSONResponse([])

    logger.info(f"v2 API: Search in library {library_id} for '{query}'")

    db = request.app.state.db
    with db.get_session() as session:
        # Get library
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Perform search using enhanced FTS search
        comics_results = search_with_fts(session, library_id, query)
        
        # Search for series first (prioritized)
        series_results = search_series(session, library_id, query, limit=5)

        logger.info(f"v2 API: Found {len(series_results)} series and {len(comics_results)} comics matching '{query}'")

        # Get cover hashes for series by looking up their folders
        series_names = [s.name for s in series_results]
        folder_covers = {}
        if series_names:
            folders = session.query(FolderModel.name, FolderModel.first_child_hash).filter(
                FolderModel.library_id == library_id,
                FolderModel.name.in_(series_names),
                FolderModel.first_child_hash.isnot(None)
            ).all()
            folder_covers = {f.name: f.first_child_hash for f in folders}

        # Get user for reading progress
        user = get_request_user(request, session)

        # Format results
        results = []

        
        # Add series results first
        for series in series_results:
            results.append({
                "type": "series",
                "id": str(series.id),
                "libraryId": str(library_id),
                "name": series.name,
                "publisher": series.publisher,
                "comic_count": series.comic_count,
                # Helper for frontend icon/display
                "file_name": series.name, 
                "path": f"/series/{library_id}/{series.name}",
                "coverHash": folder_covers.get(series.name),
            })
            
        for comic in comics_results:
            # Get reading progress
            current_page = 0
            is_read = False
            has_been_opened = False
            if user:
                progress = get_reading_progress(session, user.id, comic.id)
                if progress:
                    current_page = progress.current_page
                    is_read = progress.is_completed
                    has_been_opened = current_page > 0

            # Build relative path
            try:
                relative_path = str(Path(comic.path).relative_to(library.path))
            except ValueError:
                relative_path = comic.filename

            api_path = f"/{relative_path}"

            results.append({
                "type": "comic",
                "id": str(comic.id),
                "comic_info_id": str(comic.id),
                "parent_id": str(comic.folder_id) if comic.folder_id is not None else "0",
                "library_id": str(library_id),
                "library_uuid": library.uuid,
                "file_name": comic.filename,
                "file_size": str(comic.file_size),
                "hash": comic.hash,
                "path": api_path,
                "current_page": current_page,
                "num_pages": comic.num_pages,
                "read": is_read,
                "manga": (comic.reading_direction == 'rtl') if comic.reading_direction else False,
                "file_type": 1,  # 1 = comic
                "cover_size_ratio": comic.cover_size_ratio if comic.cover_size_ratio > 0 else 0.67,  # Use stored ratio or default comic aspect ratio (2:3)
                "number": 0,
                "has_been_opened": has_been_opened
            })

        logger.debug(f"v2 API: Returning {len(results)} search results")
        return JSONResponse(results)


@router.get("/library/{library_id}/search/advanced")
@router.post("/library/{library_id}/search/advanced")
async def search_comics_advanced_v2(
    library_id: int,
    request: Request,
    q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Advanced search with filters and pagination

    Supports:
    - Field-specific queries: "writer:Stan Lee", "genre:superhero"
    - Boolean operators: AND, OR, NOT
    - Pagination via limit/offset
    - Dynamic metadata search

    Args:
        library_id: ID of the library to search in
        q: Search query string
        limit: Maximum number of results (default: 100)
        offset: Number of results to skip (default: 0)

    Returns:
        JSON object with:
        - results: Array of comics
        - total: Total number of matches
        - limit: Applied limit
        - offset: Applied offset
    """
    # Get query from GET parameter or POST body
    query = q

    # If it's a POST request and no query param, try to get from body
    if request.method == "POST" and not query:
        try:
            body = await request.json()
            query = body.get("query", body.get("q", ""))
            limit = body.get("limit", limit)
            offset = body.get("offset", offset)
        except:
            pass

    if not query or not query.strip():
        return JSONResponse({"results": [], "total": 0, "limit": limit, "offset": offset})

    logger.info(f"v2 API: Advanced search in library {library_id} for '{query}'")

    db = request.app.state.db
    with db.get_session() as session:
        # Get library
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Perform advanced search
        comics, total = search_comics_advanced(
            session,
            library_id=library_id,
            query_str=query,
            limit=limit,
            offset=offset
        )

        logger.info(f"v2 API: Found {total} comics matching '{query}' (returning {len(comics)})")

        # Get user for reading progress
        user = get_request_user(request, session)

        # Format results
        results = []
        for comic in comics:
            # Get reading progress
            current_page = 0
            is_read = False
            has_been_opened = False
            if user:
                progress = get_reading_progress(session, user.id, comic.id)
                if progress:
                    current_page = progress.current_page
                    is_read = progress.is_completed
                    has_been_opened = current_page > 0

            # Build relative path
            try:
                relative_path = str(Path(comic.path).relative_to(library.path))
            except ValueError:
                relative_path = comic.filename

            api_path = f"/{relative_path}"

            results.append({
                "type": "comic",
                "id": str(comic.id),
                "comic_info_id": str(comic.id),
                "parent_id": str(comic.folder_id) if comic.folder_id is not None else "0",
                "library_id": str(library_id),
                "library_uuid": library.uuid,
                "file_name": comic.filename,
                "file_size": str(comic.file_size),
                "hash": comic.hash,
                "path": api_path,
                "current_page": current_page,
                "num_pages": comic.num_pages,
                "read": is_read,
                "manga": (comic.reading_direction == 'rtl') if comic.reading_direction else False,
                "file_type": 1,  # 1 = comic
                "cover_size_ratio": comic.cover_size_ratio if comic.cover_size_ratio > 0 else 0.67,  # Use stored ratio or default comic aspect ratio (2:3)
                "number": 0,
                "has_been_opened": has_been_opened
            })

        return JSONResponse({
            "results": results,
            "total": total,
            "limit": limit,
            "offset": offset
        })


@router.get("/library/{library_id}/search/fields")
async def get_search_fields_v2(library_id: int, request: Request):
    """
    Get list of searchable fields for a library

    Returns field names, types, descriptions, and examples
    to help users construct advanced search queries.

    Returns:
        JSON object with field information
    """
    db = request.app.state.db
    with db.get_session() as session:
        # Get library
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        fields = get_searchable_fields(session, library_id)
        return JSONResponse(fields)


@router.get("/search/query/parse")
async def parse_query_v2(q: str):
    """
    Parse a search query to show how it will be interpreted

    Useful for debugging and showing users what their query will search for.

    Args:
        q: Search query string

    Returns:
        JSON object with parsed query components
    """
    parsed = parse_search_query(q)

    return JSONResponse({
        "original_query": q,
        "field_queries": parsed.field_queries,
        "general_terms": parsed.general_terms,
        "exclude_terms": parsed.exclude_terms,
        "is_empty": parsed.is_empty()
    })

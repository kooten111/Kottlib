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
from ...middleware import get_current_user_id

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

        # Perform search
        from ....database.database import search_comics
        comics = search_comics(session, library_id, query)

        logger.info(f"v2 API: Found {len(comics)} comics matching '{query}'")

        # Get user for reading progress
        user_id = get_current_user_id(request)
        if user_id:
            user = get_user_by_id(session, user_id)
        else:
            user = get_user_by_username(session, 'admin')

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
                "cover_size_ratio": 0.0,
                "number": 0,
                "has_been_opened": has_been_opened
            })

        logger.debug(f"v2 API: Returning {len(results)} search results")
        return JSONResponse(results)

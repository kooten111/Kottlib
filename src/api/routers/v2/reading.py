"""
API v2 Router - Reading Progress

Endpoints for reading progress and continue reading.
"""

import logging
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Request, Cookie, HTTPException
from fastapi.responses import JSONResponse

from ....database import (
    get_library_by_id,
    get_user_by_id,
    get_continue_reading,
)
from ...middleware import get_current_user_id, get_request_user
from ._shared import get_comic_display_name

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Reading Progress / Continue Reading
# ============================================================================

@router.get("/library/{library_id}/reading")
async def get_reading_list(
    library_id: int,
    request: Request,
    limit: int = 10,
    yacread_session: Optional[str] = Cookie(None)
):
    """
    Get reading list / continue reading (v2 JSON format)

    Returns recently read comics that are in progress
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Validate library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get user from session
        user = get_request_user(request, session)
        if not user:
            return JSONResponse([])

        # Get continue reading list
        results = get_continue_reading(session, user.id, limit)

        comics_list = []
        for progress, comic in results:
            # Only include comics from this library
            if comic.library_id != library_id:
                continue

            # Calculate relative path
            try:
                relative_path = str(Path(comic.path).relative_to(library.path))
            except ValueError:
                relative_path = comic.filename

            api_path = f"/{relative_path}"

            # Format comic data matching YACReader v2 format
            comics_list.append({
                "type": "comic",
                "id": str(comic.id),
                "comic_info_id": str(comic.id),
                "parent_id": str(comic.folder_id) if comic.folder_id is not None else "0",
                "library_id": str(library_id),
                "library_uuid": library.uuid if library else "",
                "file_name": comic.filename,
                "file_size": str(comic.file_size),
                "hash": comic.hash,
                "path": api_path,
                "current_page": progress.current_page,
                "num_pages": progress.total_pages or comic.num_pages,
                "read": progress.is_completed,
                "manga": getattr(comic, 'reading_direction', 'ltr') == 'rtl',
                "file_type": 1,
                "cover_size_ratio": comic.cover_size_ratio if comic.cover_size_ratio > 0 else 0.67,  # Use stored ratio or default comic aspect ratio (2:3)
                "number": 0,
                "count": 0,
                "date": "",
                "rating": 0,
                "synopsis": "",
                "title": get_comic_display_name(comic),
                "has_been_opened": progress.current_page > 0,
                "last_time_opened": progress.last_read_at,
                "current_page_bookmarked": False,
                "cover_page": 0,
                "brightness": 0,
                "contrast": 0,
                "gamma": 1.0
            })

        return JSONResponse(comics_list)

"""
API v2 Router - Session Management

Endpoints for session management and reading progress synchronization:
- GET /recoverSession - Recover session information
- POST /sync - Sync reading progress data
"""

import logging
import json
from typing import Optional

from fastapi import APIRouter, Request, Cookie
from fastapi.responses import JSONResponse
from sqlalchemy import func

from ....database import (
    get_library_by_id,
    get_user_by_username,
    get_user_by_id,
    update_reading_progress,
)
from ...middleware import get_current_user_id, get_request_user

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Session Management
# ============================================================================

@router.get("/recoverSession")
async def recover_session(request: Request):
    """
    Recover session (stub)

    This endpoint can be used by clients to check if a session can be recovered
    after a connection loss.

    Returns:
        JSON with recovery status
    """
    return JSONResponse({"recovered": False})


@router.post("/sync")
async def sync_session_v2(request: Request, yacread_session: Optional[str] = Cookie(None)):
    """
    Sync reading progress (v2 API)

    Accepts JSON body with reading progress data and syncs it to the server.
    Expected format:
    {
        "comics": [
            {"comicId": 123, "libraryId": 1, "currentPage": 5, "totalPages": 20},
            ...
        ]
    }

    Returns JSON with sync results

    Args:
        request: HTTP request
        yacread_session: Optional session cookie

    Returns:
        JSON with sync results including number of synced comics and any errors
    """
    main_db = request.app.state.db

    try:
        # Parse JSON body
        # Handle "Extra data" error by using raw_decode to parse only the valid JSON part
        try:
            body_bytes = await request.body()
            body_str = body_bytes.decode('utf-8')
            body, _ = json.JSONDecoder().raw_decode(body_str)
        except json.JSONDecodeError:
             # Fallback to standard parsing if raw_decode fails (or if it was empty)
            body = await request.json()

        comics = body.get("comics", [])

        # Get user from session
        with main_db.get_session() as session:
            user = get_request_user(request, session)

        if not user:
            return JSONResponse({"success": False, "error": "User not found"}, status_code=401)

        # Update reading progress for each comic
        synced_count = 0
        errors = []

        for comic_data in comics:
            comic_id = comic_data.get("comicId")
            library_id = comic_data.get("libraryId")
            current_page = comic_data.get("currentPage", 0)
            total_pages = comic_data.get("totalPages")

            if comic_id is None or library_id is None:
                errors.append(f"Missing comicId or libraryId in comic data: {comic_data}")
                continue

            try:
                # Get library from main DB
                with main_db.get_session() as session:
                    library = get_library_by_id(session, library_id)
                    if not library:
                        errors.append(f"Library {library_id} not found")
                        continue
                    library_name = library.name

                # Update progress in main DB
                with main_db.get_session() as session:
                    update_reading_progress(
                        session,
                        user_id=user.id,
                        comic_id=comic_id,
                        current_page=current_page,
                        total_pages=total_pages
                    )
                    synced_count += 1

            except Exception as e:
                logger.error(f"Error syncing comic {comic_id}: {e}")
                errors.append(f"Comic {comic_id}: {str(e)}")

        logger.info(f"v2 Sync: Updated {synced_count} comics for user {user.username}")

        return JSONResponse({
            "success": True,
            "synced": synced_count,
            "errors": errors if errors else None
        })

    except Exception as e:
        logger.error(f"v2 Sync error: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

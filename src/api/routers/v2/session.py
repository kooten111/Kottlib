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
    get_comic_by_id,
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

    Accepts tab-separated values (YACReader format) with reading progress data.

    iOS Format (per line):
    {libraryId}\t{comicId}\t{hash}\t{currentPage}\t{rating}\t{lastTimeOpened}\t{read}\t{lastTimeImageFiltersSet}\t{imageFiltersJson}\n

    Android Format (per line):
    u\t{libraryUUID}\t{comicId}\t{hash}\t{currentPage}\t{rating}\t{lastTimeOpened}\t{hasBeenOpened}\t{read}\t{lastTimeImageFiltersSet}\t{imageFiltersJson}\n

    Returns: JSON array of comics that are more recent on server

    Args:
        request: HTTP request
        yacread_session: Optional session cookie

    Returns:
        JSON array of comics with more recent server timestamps
    """
    main_db = request.app.state.db

    try:
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8').strip()
        logger.info(f"v2 Sync: Received raw body: {body_str[:200]}")

        lines = []
        json_comics = []

        if body_str:
            try:
                payload = json.loads(body_str)
                if isinstance(payload, dict) and isinstance(payload.get("comics"), list):
                    json_comics = payload.get("comics", [])
            except Exception:
                lines = body_str.split('\n')

        if not lines and not json_comics:
            logger.warning("v2 Sync: Empty body received")
            return JSONResponse([])

        # Get user from session
        with main_db.get_session() as session:
            user = get_request_user(request, session)

        if not user:
            logger.warning("v2 Sync: No user found in session")
            return JSONResponse([])

        # Update reading progress for each line
        synced_count = 0
        server_updates = []  # Comics that are more recent on server
        touched_library_ids = set()

        for comic_data in json_comics:
            try:
                comic_id = comic_data.get("comicId")
                current_page = int(comic_data.get("currentPage", 0) or 0)
                total_pages = comic_data.get("totalPages")

                if comic_id is None:
                    continue

                with main_db.get_session() as session:
                    comic = get_comic_by_id(session, comic_id)
                    if not comic:
                        continue
                    if total_pages is None:
                        total_pages = comic.num_pages

                    update_reading_progress(
                        session,
                        user_id=user.id,
                        comic_id=comic_id,
                        current_page=current_page,
                        total_pages=total_pages
                    )
                    synced_count += 1
                    if comic.library_id:
                        touched_library_ids.add(comic.library_id)
            except Exception as e:
                logger.error(f"v2 Sync: Error parsing JSON comic entry: {e}")
                continue

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                parts = line.split('\t')

                # Determine format based on first field
                if parts[0] == 'u':
                    # Android format: u\t{libraryUUID}\t{comicId}\t{hash}\t{currentPage}\t{rating}\t{lastTimeOpened}\t{hasBeenOpened}\t{read}\t{lastTimeImageFiltersSet}\t{imageFiltersJson}
                    if len(parts) < 7:
                        logger.warning(f"v2 Sync: Invalid Android format line: {line[:100]}")
                        continue

                    library_uuid = parts[1]
                    comic_id = int(parts[2]) if parts[2] else None
                    comic_hash = parts[3] if len(parts) > 3 else None
                    current_page = int(parts[4]) if len(parts) > 4 and parts[4] else 0
                    # rating = float(parts[5]) if len(parts) > 5 and parts[5] else 0
                    # last_time_opened = int(parts[6]) if len(parts) > 6 and parts[6] else None
                    # has_been_opened = parts[7] == '1' if len(parts) > 7 else False
                    # is_read = parts[8] == '1' if len(parts) > 8 else False

                    # Find library by UUID
                    with main_db.get_session() as session:
                        from ...database import get_all_libraries
                        libs = get_all_libraries(session)
                        library = next((lib for lib in libs if str(lib.uuid) == library_uuid), None)
                        if not library:
                            logger.warning(f"v2 Sync: Library UUID {library_uuid} not found")
                            continue
                        library_id = library.id

                elif parts[0] == 'unknown':
                    # Unknown library format: unknown\t\t{hash}\t{currentPage}\t...
                    logger.info(f"v2 Sync: Skipping unknown library entry")
                    continue
                else:
                    # iOS format: {libraryId}\t{comicId}\t{hash}\t{currentPage}\t{rating}\t{lastTimeOpened}\t{read}\t{lastTimeImageFiltersSet}\t{imageFiltersJson}
                    # But sometimes mobile apps send incomplete data (just library ID)
                    if len(parts) == 1:
                        # Just a single value (likely library ID) - this is not valid sync data
                        logger.warning(f"v2 Sync: Received incomplete sync data (single value): {line[:100]}")
                        logger.warning("v2 Sync: Mobile app may be sending malformed sync request")
                        continue

                    if len(parts) < 4:
                        logger.warning(f"v2 Sync: Invalid iOS format line (expected at least 4 fields, got {len(parts)}): {line[:100]}")
                        continue

                    library_id = int(parts[0]) if parts[0] else None
                    comic_id = int(parts[1]) if parts[1] else None
                    comic_hash = parts[2] if len(parts) > 2 else None
                    current_page = int(parts[3]) if len(parts) > 3 and parts[3] else 0
                    # rating = float(parts[4]) if len(parts) > 4 and parts[4] else 0
                    # last_time_opened = int(parts[5]) if len(parts) > 5 and parts[5] else None
                    # is_read = parts[6] == '1' if len(parts) > 6 else False

                if comic_id is None or library_id is None:
                    logger.warning(f"v2 Sync: Missing comic_id or library_id in line: {line[:100]}")
                    continue

                # Get comic to find total pages
                with main_db.get_session() as session:
                    comic = get_comic_by_id(session, comic_id)
                    if not comic:
                        logger.warning(f"v2 Sync: Comic {comic_id} not found")
                        continue
                    total_pages = comic.num_pages

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
                    touched_library_ids.add(library_id)

            except Exception as e:
                logger.error(f"v2 Sync: Error parsing line '{line[:100]}': {e}")
                continue

        logger.info(f"v2 Sync: Updated {synced_count} comics for user {user.username}")

        if touched_library_ids:
            try:
                from ....services.library_cache import get_library_cache
                for lib_id in touched_library_ids:
                    get_library_cache(lib_id).invalidate_all()
                get_library_cache(0).invalidate_all()
            except Exception as cache_err:
                logger.warning(f"Failed to invalidate browse cache after sync: {cache_err}")

        return JSONResponse(server_updates)

    except Exception as e:
        logger.error(f"v2 Sync error: {e}", exc_info=True)
        return JSONResponse([], status_code=500)

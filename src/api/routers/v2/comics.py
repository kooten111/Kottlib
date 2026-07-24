"""
API v2 Router - Comics

Endpoints for comic information, pages, and covers.
"""

import json
import logging
import asyncio
from typing import Optional, Tuple
from pathlib import Path

from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from sqlalchemy import text

from ....database import (
    get_library_by_id,
    get_all_libraries,
    get_comic_by_id,
    get_user_by_username,
    get_user_by_id,
    get_reading_progress,
    get_sibling_comics,
    get_covers_dir,
    update_reading_progress,
    get_reading_list_comics,
)
from ...middleware import get_current_user_id, get_request_user
from ...error_handling import handle_file_operation, handle_comic_archive_errors, safe_path_exists
from ...cover_utils import find_cover_file
from ...response_builders import build_comic_metadata_response
from ._shared import get_comic_display_name

logger = logging.getLogger(__name__)

router = APIRouter()


def _detect_page_count(comic_path: Path) -> int:
    """Open archive and return page count (runs in a worker thread)."""
    from ....scanner import open_comic

    with open_comic(comic_path) as archive:
        if archive is None:
            return 0
        return archive.page_count or 0


def _extract_page_bytes(comic_path: Path, page_num: int) -> Tuple[Optional[bytes], str]:
    """
    Extract a page from an archive (runs in a worker thread).

    Uses the process-local open-archive + page-bytes caches so remote readers
    do not reopen CBZ/CBR on every turn.

    Returns:
        (page_bytes, content_type) or (None, "") on failure / out of range.
    """
    from ....services.page_cache import extract_page_bytes

    return extract_page_bytes(comic_path, page_num)


# ============================================================================
# Comic Information
# ============================================================================

@router.get("/library/{library_id}/comic/{comic_id}/fullinfo")
async def get_comic_fullinfo_v2(
    library_id: int,
    comic_id: int,
    request: Request
):
    """
    Get full comic information (v2 JSON format)

    This endpoint is called when opening a comic to get all metadata
    """
    logger.info(f"[FULLINFO] Request: library_id={library_id}, comic_id={comic_id}")
    logger.debug(f"[FULLINFO] Client: {request.client.host if request.client else 'unknown'}")
    logger.debug(f"[FULLINFO] User-Agent: {request.headers.get('user-agent', 'unknown')}")

    # Get main database
    db = request.app.state.db

    # Use main database for everything
    with db.get_session() as session:
        logger.debug(f"[FULLINFO] Fetching library: library_id={library_id}")
        library = get_library_by_id(session, library_id)
        if not library:
            logger.error(f"[FULLINFO] Library not found: library_id={library_id}")
            raise HTTPException(status_code=404, detail="Library not found")
        library_name = library.name
        library_path = library.path
        logger.debug(f"[FULLINFO] Library found: name={library_name}, path={library_path}")

        # Get user for reading progress
        user = get_request_user(request, session)
        logger.debug(f"[FULLINFO] User: {user.username if user else None}")

        logger.debug(f"[FULLINFO] Fetching comic: comic_id={comic_id}")
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            logger.error(f"[FULLINFO] Comic not found: comic_id={comic_id}")
            raise HTTPException(status_code=404, detail="Comic not found")

        logger.info(f"[FULLINFO] Comic found: filename={comic.filename}, path={comic.path}, num_pages={comic.num_pages}, hash={comic.hash[:12]}...")

        # Fix missing page count off the event loop (scan should usually populate this)
        if comic.num_pages == 0:
            logger.warning(
                "[FULLINFO] Comic has num_pages=0, detecting page count from archive"
            )
            comic_path = Path(comic.path)
            try:
                if comic_path.exists():
                    loop = asyncio.get_running_loop()
                    actual_page_count = await loop.run_in_executor(
                        None, _detect_page_count, comic_path
                    )
                    if actual_page_count > 0:
                        comic.num_pages = actual_page_count
                        session.commit()
                        logger.info(
                            "[FULLINFO] Updated comic.num_pages to %s",
                            actual_page_count,
                        )
                else:
                    logger.error("[FULLINFO] Comic file does not exist: %s", comic_path)
            except Exception as e:
                logger.error(
                    "[FULLINFO] Error detecting page count: %s", e, exc_info=True
                )

        # Get reading progress
        current_page = 0
        is_read = False
        if user:
            logger.debug(f"[FULLINFO] User found: username={user.username}")
            progress = get_reading_progress(session, user.id, comic_id)
            if progress:
                current_page = progress.current_page
                is_read = progress.is_completed
                logger.debug(f"[FULLINFO] Reading progress found: current_page={current_page}, is_completed={is_read}, progress_percent={progress.progress_percent}")
            else:
                logger.debug(f"[FULLINFO] No reading progress found for user_id={user.id}, comic_id={comic_id}")
        else:
            logger.warning(f"[FULLINFO] No user found for session")

        try:
            # Calculate the relative path from the library root
            relative_path = str(Path(comic.path).relative_to(library_path))
            logger.debug(f"[FULLINFO] Calculated relative path: {relative_path}")
        except ValueError as e:
            logger.warning(f"[FULLINFO] Failed to calculate relative path: {e}, using filename as fallback")
            relative_path = comic.filename  # Fallback

        # Prepend a slash as the API requires
        api_path = f"/{relative_path}"
        logger.debug(f"[FULLINFO] API path: {api_path}")

        # Build full comic info response matching YACReader format
        response = {
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
            "current_page": current_page,
            "num_pages": comic.num_pages,
            "read": is_read,
            "manga": comic.reading_direction == 'rtl' if hasattr(comic, 'reading_direction') else False,
            "file_type": 1,
            "cover_size_ratio": comic.cover_size_ratio if comic.cover_size_ratio > 0 else 0.67,
            "number": 0,
            "has_been_opened": current_page > 0,
        }

        # Add optional core fields
        if comic.title:
            response["title"] = comic.title
        if comic.series:
            response["series"] = comic.series
        if comic.volume:
            response["volume"] = str(comic.volume)
        if comic.issue_number:
            response["universal_number"] = str(comic.issue_number)

        # Add all optional metadata fields using the response builder utility
        metadata = build_comic_metadata_response(comic)
        response.update(metadata)

        logger.info(f"[FULLINFO] Response built successfully: comic_id={comic.id}, num_pages={comic.num_pages}, current_page={current_page}, has_title={bool(comic.title)}, has_series={bool(comic.series)}")
        logger.debug(f"[FULLINFO] Full response keys: {list(response.keys())}")
        return JSONResponse(response)


@router.get("/library/{library_id}/comic/{comic_id}/info")
async def get_comic_info_v2(
    library_id: int,
    comic_id: int,
    request: Request
):
    """
    Get comic download info in text format (v2 API)

    Returns:
    fileName:{fileName}
    fileSize:{fileSize}
    """
    # Get main database for library metadata
    db = request.app.state.db

    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        response_text = f"fileName:{comic.filename}\r\nfileSize:{comic.file_size}\r\n"
        return PlainTextResponse(response_text, media_type="text/plain; charset=utf-8")


@router.get("/library/{library_id}/comic/{comic_id}")
async def open_comic_download_v2(
    library_id: int,
    comic_id: int,
    request: Request
):
    """
    Open comic for downloading (v2 API)

    Returns similar format to /info but indicates comic is being opened for download.
    """
    # Get main database for library metadata
    db = request.app.state.db

    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Return basic info for download
        response_text = f"fileName:{comic.filename}\r\nfileSize:{comic.file_size}\r\npath:{comic.path}\r\n"
        return PlainTextResponse(response_text, media_type="text/plain; charset=utf-8")


@router.get("/library/{library_id}/comic/{comic_id}/remote")
async def open_comic_remote_v2(
    library_id: int,
    comic_id: int,
    request: Request
):
    """
    Open comic for remote reading (v2 PLAIN TEXT format)

    Returns the same plain text format as v1 for compatibility
    """
    # Get main database for library and user data
    db = request.app.state.db

    # First, get library info from main database
    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")
        library_name = library.name
        library_path = library.path

        # Get user for reading progress (from main DB)
        user = get_request_user(request, session)

        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Get reading progress
        current_page = 0
        is_read = 0
        if user:
            progress = get_reading_progress(session, user.id, comic_id)
            if progress:
                current_page = progress.current_page
                is_read = 1 if progress.is_completed else 0

        # Get previous/next comic for navigation
        prev_comic_id, next_comic_id = get_sibling_comics(session, comic_id)

        # Get hashes for previous/next comics (v2 requirement)
        prev_comic_hash = None
        next_comic_hash = None
        if prev_comic_id is not None:
            prev_result = session.execute(text("SELECT hash FROM comics WHERE id = :id"), {"id": prev_comic_id}).fetchone()
            if prev_result:
                prev_comic_hash = prev_result[0]
        if next_comic_id is not None:
            next_result = session.execute(text("SELECT hash FROM comics WHERE id = :id"), {"id": next_comic_id}).fetchone()
            if next_result:
                next_comic_hash = next_result[0]

        try:
            relative_path = str(Path(comic.path).relative_to(library_path))
        except ValueError:
            relative_path = comic.filename
        api_path = f"/{relative_path}"

        # Build plain text response in YACReader format
        lines = []
        lines.append(f"library:{library_name}")
        lines.append(f"libraryId:{library_id}")

        # Add navigation (previousComic/nextComic) with hashes (v2 format)
        if prev_comic_id is not None:
            lines.append(f"previousComic:{prev_comic_id}")
            if prev_comic_hash:
                lines.append(f"previousComicHash:{prev_comic_hash}")
        if next_comic_id is not None:
            lines.append(f"nextComic:{next_comic_id}")
            if next_comic_hash:
                lines.append(f"nextComicHash:{next_comic_hash}")

        # Comic info (matching comic.toTXT() format)
        lines.append(f"comicid:{comic_id}")
        lines.append(f"hash:{comic.hash}")
        lines.append(f"path:{api_path}")
        lines.append(f"numpages:{comic.num_pages}")
        lines.append(f"rating:0")
        lines.append(f"currentPage:{current_page}")
        lines.append(f"contrast:0")
        lines.append(f"read:{is_read}")
        lines.append(f"coverPage:1")

        if comic.title:
            lines.append(f"title:{comic.title}")
        if comic.issue_number:
            lines.append(f"number:{comic.issue_number}")
        if comic.series:
            lines.append(f"series:{comic.series}")
        if comic.volume:
            lines.append(f"volume:{comic.volume}")

        # File type (manga flag)
        manga_flag = 1 if (hasattr(comic, 'reading_direction') and comic.reading_direction == 'rtl') else 0
        lines.append(f"manga:{manga_flag}")

        if comic.created_at:
            lines.append(f"added:{comic.created_at}")

        response_text = "\r\n".join(lines) + "\r\n"

        return PlainTextResponse(
            response_text,
            media_type="text/plain; charset=utf-8"
        )


@router.get("/library/{library_id}/reading_list/{list_id}/comic/{comic_id}/remote")
async def open_reading_list_comic_remote_v2(
    library_id: int,
    list_id: int,
    comic_id: int,
    request: Request
):
    """Open comic for remote reading within a reading list context."""
    db = request.app.state.db

    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        user = get_request_user(request, session)
        current_page = 0
        is_read = 0
        if user:
            progress = get_reading_progress(session, user.id, comic_id)
            if progress:
                current_page = progress.current_page
                is_read = 1 if progress.is_completed else 0

        items = get_reading_list_comics(session, list_id)
        comic_ids = []
        for item in items:
            if hasattr(item, "comic") and item.comic:
                comic_ids.append(item.comic.id)
            elif hasattr(item, "id"):
                comic_ids.append(item.id)

        previous_comic = None
        next_comic = None
        if comic_id in comic_ids:
            idx = comic_ids.index(comic_id)
            if idx > 0:
                previous_comic = get_comic_by_id(session, comic_ids[idx - 1])
            if idx < len(comic_ids) - 1:
                next_comic = get_comic_by_id(session, comic_ids[idx + 1])

        try:
            relative_path = str(Path(comic.path).relative_to(library.path))
        except ValueError:
            relative_path = comic.filename
        api_path = f"/{relative_path}"

        lines = [
            f"library:{library.name}",
            f"libraryId:{library_id}",
        ]
        if previous_comic:
            lines.append(f"previousComic:{previous_comic.id}")
            lines.append(f"previousComicHash:{previous_comic.hash}")
        if next_comic:
            lines.append(f"nextComic:{next_comic.id}")
            lines.append(f"nextComicHash:{next_comic.hash}")
        lines.extend([
            f"comicid:{comic_id}",
            f"hash:{comic.hash}",
            f"path:{api_path}",
            f"numpages:{comic.num_pages}",
            "rating:0",
            f"currentPage:{current_page}",
            "contrast:0",
            f"read:{is_read}",
            "coverPage:1",
            f"manga:{1 if (hasattr(comic, 'reading_direction') and comic.reading_direction == 'rtl') else 0}",
        ])
        if comic.title:
            lines.append(f"title:{comic.title}")
        if comic.issue_number:
            lines.append(f"number:{comic.issue_number}")
        if comic.series:
            lines.append(f"series:{comic.series}")
        if comic.volume:
            lines.append(f"volume:{comic.volume}")
        if comic.created_at:
            lines.append(f"added:{comic.created_at}")

        return PlainTextResponse("\r\n".join(lines) + "\r\n", media_type="text/plain; charset=utf-8")


# ============================================================================
# Comic Pages
# ============================================================================

@router.get("/library/{library_id}/comic/{comic_id}/page/{page_num}")
@handle_comic_archive_errors("Failed to extract comic page")
async def get_comic_page_v2_nonremote(
    library_id: int,
    comic_id: int,
    page_num: int,
    request: Request
):
    """
    Get comic page image (v2 non-remote)

    Standard page access without remote reading context
    """
    logger.info(f"[PAGE-NONREMOTE] Request: library_id={library_id}, comic_id={comic_id}, page_num={page_num}")

    # Get main database for library metadata
    db = request.app.state.db

    # Use main database for everything
    with db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        comic_path = Path(comic.path)

    loop = asyncio.get_running_loop()
    page_data, content_type = await loop.run_in_executor(
        None, _extract_page_bytes, comic_path, page_num
    )
    if page_data is None:
        raise HTTPException(status_code=404, detail="Page not found")

    from ....services.page_cache import schedule_warm_neighbors

    schedule_warm_neighbors(comic_path, page_num)

    return Response(
        content=page_data,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"}
    )


@router.get("/library/{library_id}/comic/{comic_id}/page/{page_num}/remote")
@router.get("/library/{library_id}/comic/{comic_id}/remote/page/{page_num}")
@handle_comic_archive_errors("Failed to extract comic page")
async def get_comic_page_v2_remote(
    library_id: int,
    comic_id: int,
    page_num: int,
    request: Request
):
    """
    Get comic page image (v2)

    Same as v1 but accessed via v2 path
    """
    logger.info(f"[PAGE] Request: library_id={library_id}, comic_id={comic_id}, page_num={page_num}")

    db = request.app.state.db

    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        if page_num < 0:
            raise HTTPException(status_code=404, detail="Page not found")

        comic_path = Path(comic.path)

    loop = asyncio.get_running_loop()
    try:
        page_data, content_type = await loop.run_in_executor(
            None, _extract_page_bytes, comic_path, page_num
        )
    except Exception as e:
        logger.error(f"[PAGE] Exception while processing page: {type(e).__name__}: {e}", exc_info=True)
        raise

    if page_data is None:
        raise HTTPException(status_code=404, detail="Page not found")

    from ....services.page_cache import schedule_warm_neighbors

    schedule_warm_neighbors(comic_path, page_num)

    return Response(
        content=page_data,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"}
    )


# ============================================================================
# Comic Progress Update
# ============================================================================

@router.post("/library/{library_id}/comic/{comic_id}/update")
async def update_comic_progress_v2(
    library_id: int,
    comic_id: int,
    request: Request
):
    """
    Update comic reading progress (v2)

    YACReader format (plain text body):
    Line 1: currentPage:{page_number}
    Line 2 (optional): {next_comic_id}
    Line 3 (optional): {timestamp}\t{image_filters_json}
    """
    # Get raw body as text (YACReader sends plain text, not JSON/form data)
    try:
        body_bytes = await request.body()
        body_text = body_bytes.decode('utf-8')
        logger.info(f"v2 API: Raw body received: {repr(body_text)}")
    except Exception as e:
        logger.error(f"v2 API: Failed to read body: {e}")
        raise HTTPException(status_code=400, detail="Failed to read request body")

    # Parse YACReader format: "currentPage:5\nnextComicId\n..."
    current_page = None
    if body_text.strip():
        lines = body_text.split('\n')
        if len(lines) > 0 and lines[0].strip():
            # Line 1: "currentPage:5"
            first_line = lines[0].strip()
            if ':' in first_line:
                parts = first_line.split(':', 1)
                if parts[0] == 'currentPage':
                    try:
                        current_page = int(parts[1])
                        logger.info(f"v2 API: Parsed currentPage: {current_page}")
                    except ValueError:
                        logger.error(f"v2 API: Invalid currentPage value: {parts[1]}")

    if current_page is None:
        logger.error(f"v2 API: Could not parse currentPage from body: {repr(body_text)}")
        raise HTTPException(status_code=400, detail="Invalid format - expected 'currentPage:{number}'")

    # Get main database for library and user data
    db = request.app.state.db

    # Use main database for everything
    with db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get user from session
        user = get_request_user(request, session)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get comic to verify it exists and get num_pages
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Use comic's num_pages as default (form data doesn't usually include this)
        total_pages = comic.num_pages

        # Update reading progress
        logger.info(f"v2 API: Updating progress for comic {comic_id}: page {current_page}/{total_pages}")
        progress = update_reading_progress(
            session,
            user.id,
            comic_id,
            current_page,
            total_pages
        )

        try:
            from ....services.library_cache import get_library_cache
            get_library_cache(library_id).invalidate_all()
            get_library_cache(0).invalidate_all()
        except Exception as cache_err:
            logger.warning(f"Failed to invalidate browse cache after progress update: {cache_err}")

        return PlainTextResponse("OK")


@router.get("/library/{library_id}/comic/{comic_id}/progress")
async def get_comic_progress_v2(
    library_id: int,
    comic_id: int,
    request: Request
):
    """Get reading progress for a comic (v2 JSON compatibility endpoint)."""
    db = request.app.state.db

    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        user = get_request_user(request, session)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        progress = get_reading_progress(session, user.id, comic_id)
        if not progress:
            raise HTTPException(status_code=404, detail="Reading progress not found")

        return JSONResponse({
            "current_page": progress.current_page,
            "total_pages": progress.total_pages,
            "progress_percent": progress.progress_percent,
            "is_completed": progress.is_completed,
            "last_read_at": progress.last_read_at,
        })


@router.post("/library/{library_id}/comic/{comic_id}/progress")
async def update_comic_progress_v2_json(
    library_id: int,
    comic_id: int,
    request: Request
):
    """Update reading progress from JSON payload for compatibility with tests/clients."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Invalid JSON body")

    current_page_raw = payload.get("current_page", payload.get("currentPage"))
    if current_page_raw is None:
        raise HTTPException(status_code=422, detail="current_page is required")

    try:
        current_page = int(current_page_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="current_page must be an integer")

    db = request.app.state.db
    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        user = get_request_user(request, session)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        total_pages = payload.get("total_pages") or comic.num_pages
        try:
            total_pages = int(total_pages)
        except (TypeError, ValueError):
            total_pages = comic.num_pages

        progress = update_reading_progress(
            session,
            user.id,
            comic_id,
            current_page,
            total_pages
        )

        return JSONResponse({
            "success": True,
            "current_page": progress.current_page,
            "total_pages": progress.total_pages,
            "progress_percent": progress.progress_percent,
            "is_completed": progress.is_completed,
        })


# ============================================================================
# Cover Images
# ============================================================================

@router.get("/library/{library_id}/cover/{cover_path:path}")
@handle_file_operation("Failed to retrieve cover image")
async def get_cover_v2(
    library_id: int,
    cover_path: str,
    request: Request
):
    """
    Get cover image for a comic (v2)

    The cover_path is the hash.jpg / hash.webp filename.
    Covers are stored in hierarchical structure: covers/ab/abc123.jpg

    Serves WebP when available (WebUI), with JPEG fallback for compatibility.
    """
    from ...cover_utils import get_cached_library_name

    db = request.app.state.db
    library_name = get_cached_library_name(library_id, db)

    # Extract hash and preferred format from path
    lower_path = cover_path.lower()
    prefer_format = None
    if lower_path.endswith(".webp"):
        prefer_format = "webp"
    elif lower_path.endswith((".jpg", ".jpeg")):
        prefer_format = "jpg"

    hash_value = (
        cover_path
        .replace(".jpg", "")
        .replace(".jpeg", "")
        .replace(".png", "")
        .replace(".webp", "")
        .replace(".JPG", "")
        .replace(".JPEG", "")
        .replace(".WEBP", "")
    )

    cover_headers = {
        # Hash-addressed; new content => new URL. Long cache for cold grid loads.
        "Cache-Control": "public, max-age=31536000, immutable",
    }

    if library_name:
        result = find_cover_file(
            hash_value,
            library_name,
            try_webp=True,
            prefer_format=prefer_format,
        )
        if result:
            cover_file, media_type = result
            return FileResponse(
                cover_file,
                media_type=media_type,
                stat_result=cover_file.stat(),
                headers=cover_headers,
            )

    # Fallback: Search in other libraries for the same hash (Browse All wrong library_id)
    logger.debug(
        "[COVER] Cover not found in primary library %s, searching others: hash=%s",
        library_name,
        hash_value,
    )

    with db.get_session() as session:
        all_libs = get_all_libraries(session)
        for lib in all_libs:
            if lib.id == library_id:
                continue
            fallback_result = find_cover_file(
                hash_value,
                lib.name,
                try_webp=True,
                prefer_format=prefer_format,
            )
            if fallback_result:
                cover_file, media_type = fallback_result
                return FileResponse(
                    cover_file,
                    media_type=media_type,
                    stat_result=cover_file.stat(),
                    headers=cover_headers,
                )

    logger.warning(
        "[COVER] Cover not found: library_id=%s, cover_path=%s, hash=%s",
        library_id,
        cover_path,
        hash_value,
    )
    raise HTTPException(status_code=404, detail="Cover not found")

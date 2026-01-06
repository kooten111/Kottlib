"""
API v2 Router - Comics

Endpoints for comic information, pages, and covers.
"""

import json
import logging
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from sqlalchemy import text

from ....database import (
    get_library_by_id,
    get_comic_by_id,
    get_user_by_username,
    get_user_by_id,
    get_reading_progress,
    get_sibling_comics,
    get_covers_dir,
    update_reading_progress,
)
from ...middleware import get_current_user_id, get_request_user
from ...error_handling import handle_file_operation, handle_comic_archive_errors, safe_path_exists
from ...cover_utils import find_cover_file
from ._shared import get_comic_display_name

logger = logging.getLogger(__name__)

router = APIRouter()


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
            "cover_size_ratio": comic.cover_size_ratio if comic.cover_size_ratio > 0 else 0.67,  # Use stored ratio or default comic aspect ratio (2:3)
            "number": 0,
            "has_been_opened": current_page > 0,
        }

        # Add optional metadata fields if available
        # Add optional metadata fields if available
        if comic.title:
            response["title"] = comic.title
        if comic.series:
            response["series"] = comic.series
        if comic.volume:
            response["volume"] = str(comic.volume)
        if comic.issue_number:
            response["universal_number"] = str(comic.issue_number)
        
        # Description/Synopsis
        if hasattr(comic, 'description') and comic.description:
            response["synopsis"] = comic.description
        elif hasattr(comic, 'synopsis') and comic.synopsis:
            response["synopsis"] = comic.synopsis

        # People
        if hasattr(comic, 'writer') and comic.writer:
            response["writer"] = comic.writer
        if hasattr(comic, 'artist') and comic.artist:
            response["artist"] = comic.artist
        if hasattr(comic, 'penciller') and comic.penciller:
            response["penciller"] = comic.penciller
        if hasattr(comic, 'inker') and comic.inker:
            response["inker"] = comic.inker
        if hasattr(comic, 'colorist') and comic.colorist:
            response["colorist"] = comic.colorist
        if hasattr(comic, 'letterer') and comic.letterer:
            response["letterer"] = comic.letterer
        if hasattr(comic, 'cover_artist') and comic.cover_artist:
            response["cover_artist"] = comic.cover_artist
        if hasattr(comic, 'editor') and comic.editor:
            response["editor"] = comic.editor
        if hasattr(comic, 'publisher') and comic.publisher:
            response["publisher"] = comic.publisher

        # Classification
        if hasattr(comic, 'genre') and comic.genre:
            response["genre"] = comic.genre
        if hasattr(comic, 'year') and comic.year:
            response["year"] = comic.year
        if hasattr(comic, 'language_iso') and comic.language_iso:
            response["language_iso"] = comic.language_iso
        if hasattr(comic, 'age_rating') and comic.age_rating:
            response["age_rating"] = comic.age_rating
        if hasattr(comic, 'format_type') and comic.format_type:
            response["format"] = comic.format_type
        if hasattr(comic, 'is_color') and comic.is_color is not None:
            response["is_color"] = comic.is_color

        # Lists
        if hasattr(comic, 'characters') and comic.characters:
            response["characters"] = comic.characters
        if hasattr(comic, 'teams') and comic.teams:
            response["teams"] = comic.teams
        if hasattr(comic, 'locations') and comic.locations:
            response["locations"] = comic.locations

        # Series/Arc
        if hasattr(comic, 'story_arc') and comic.story_arc:
            response["story_arc"] = comic.story_arc
        if hasattr(comic, 'arc_number') and comic.arc_number:
            response["arc_number"] = comic.arc_number
        if hasattr(comic, 'arc_count') and comic.arc_count:
            response["arc_count"] = comic.arc_count
        if hasattr(comic, 'alternate_series') and comic.alternate_series:
            response["alternate_series"] = comic.alternate_series
        if hasattr(comic, 'alternate_number') and comic.alternate_number:
            response["alternate_number"] = comic.alternate_number
        if hasattr(comic, 'alternate_count') and comic.alternate_count:
            response["alternate_count"] = comic.alternate_count
        if hasattr(comic, 'count') and comic.count:
            response["count"] = comic.count

        # Additional
        if hasattr(comic, 'web') and comic.web:
            response["web"] = comic.web
        if hasattr(comic, 'notes') and comic.notes:
            response["notes"] = comic.notes
        if hasattr(comic, 'review') and comic.review:
            response["review"] = comic.review

        # Flexible Metadata (JSON)
        if hasattr(comic, 'metadata_json') and comic.metadata_json:
            try:
                response["metadata"] = json.loads(comic.metadata_json)
            except Exception as e:
                logger.warning(f"[FULLINFO] Failed to parse metadata_json for comic {comic.id}: {e}")

        # Add scanner metadata fields
        if hasattr(comic, 'scanner_source') and comic.scanner_source:
            response["scanner_source"] = comic.scanner_source
        if hasattr(comic, 'scanner_source_id') and comic.scanner_source_id:
            response["scanner_source_id"] = comic.scanner_source_id
        if hasattr(comic, 'scanner_source_url') and comic.scanner_source_url:
            response["scanner_source_url"] = comic.scanner_source_url
        if hasattr(comic, 'scan_confidence') and comic.scan_confidence is not None:
            response["scan_confidence"] = comic.scan_confidence
        if hasattr(comic, 'scanned_at') and comic.scanned_at:
            response["scanned_at"] = comic.scanned_at
        if hasattr(comic, 'tags') and comic.tags:
            response["tags"] = comic.tags

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

        # Import here to avoid circular imports
        from ....scanner import open_comic

        # Open comic archive
        comic_path = Path(comic.path)
        with open_comic(comic_path) as archive:
            if archive is None:
                raise HTTPException(status_code=500, detail="Failed to open comic")

            if page_num < 0 or page_num >= archive.page_count:
                raise HTTPException(status_code=404, detail="Page not found")

            # Get page data
            page_data = archive.get_page(page_num)
            if page_data is None:
                raise HTTPException(status_code=404, detail="Failed to read page")

            # Determine content type from page filename
            page = archive.pages[page_num]
            ext = Path(page.filename).suffix.lower()

            content_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.bmp': 'image/bmp',
            }

            content_type = content_type_map.get(ext, 'image/jpeg')

            return Response(
                content=page_data,
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=86400"}
            )


@router.get("/library/{library_id}/comic/{comic_id}/page/{page_num}/remote")
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
    logger.debug(f"[PAGE] Client: {request.client.host if request.client else 'unknown'}")

    # Get main database for library metadata
    db = request.app.state.db

    # Use main database for everything
    with db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        logger.debug(f"[PAGE] Fetching comic from main database: comic_id={comic_id}")
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            logger.error(f"[PAGE] Comic not found: comic_id={comic_id}")
            raise HTTPException(status_code=404, detail="Comic not found")

        logger.info(f"[PAGE] Comic found: filename={comic.filename}, path={comic.path}, num_pages={comic.num_pages}")
        logger.debug(f"[PAGE] Checking page bounds: page_num={page_num}, num_pages={comic.num_pages}")

        # Import here to avoid circular imports
        from ....scanner import open_comic

        # Open comic archive
        comic_path = Path(comic.path)
        logger.debug(f"[PAGE] Opening comic archive: {comic_path}")
        logger.debug(f"[PAGE] Archive exists: {comic_path.exists()}, is_file: {comic_path.is_file()}")

        try:
            with open_comic(comic_path) as archive:
                if archive is None:
                    logger.error(f"[PAGE] Failed to open comic archive: {comic_path}")
                    raise HTTPException(status_code=500, detail="Failed to open comic")

                logger.info(f"[PAGE] Archive opened successfully: page_count={archive.page_count}, type={type(archive).__name__}")

                if page_num < 0 or page_num >= archive.page_count:
                    logger.error(f"[PAGE] Page number out of bounds: page_num={page_num}, page_count={archive.page_count}")
                    raise HTTPException(status_code=404, detail="Page not found")

                # Get page data
                logger.debug(f"[PAGE] Extracting page {page_num} from archive")
                page_data = archive.get_page(page_num)
                if page_data is None:
                    logger.error(f"[PAGE] Failed to read page {page_num} from archive")
                    raise HTTPException(status_code=404, detail="Failed to read page")

                logger.info(f"[PAGE] Page extracted successfully: size={len(page_data)} bytes")

                # Determine content type
                page = archive.pages[page_num]
                ext = Path(page.filename).suffix.lower()

                content_type_map = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp',
                    '.bmp': 'image/bmp',
                }

                content_type = content_type_map.get(ext, 'image/jpeg')
                logger.debug(f"[PAGE] Page info: filename={page.filename}, extension={ext}, content_type={content_type}")

                logger.info(f"[PAGE] Serving page: comic_id={comic_id}, page_num={page_num}, size={len(page_data)} bytes, type={content_type}")
                return Response(
                    content=page_data,
                    media_type=content_type,
                    headers={"Cache-Control": "public, max-age=86400"}
                )
        except Exception as e:
            logger.error(f"[PAGE] Exception while processing page: {type(e).__name__}: {e}", exc_info=True)
            raise


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

        # Return success response
        return JSONResponse({
            "success": True,
            "current_page": progress.current_page,
            "total_pages": progress.total_pages,
            "progress_percent": progress.progress_percent,
            "is_completed": progress.is_completed
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

    The cover_path is the hash.jpg filename
    Covers are stored in hierarchical structure: covers/ab/abc123.jpg

    Serves WebP format when available (better quality, smaller size),
    with JPEG fallback for compatibility.
    """
    logger.info(f"[COVER] Request: library_id={library_id}, cover_path={cover_path}")
    logger.debug(f"[COVER] Client: {request.client.host if request.client else 'unknown'}")

    db = request.app.state.db

    # Get library to determine covers directory
    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        library_name = library.name if library else None

    logger.debug(f"[COVER] Library: {library_name}")

    # Extract hash from path (e.g., "abc123.jpg" -> "abc123")
    hash_value = cover_path.replace('.jpg', '').replace('.jpeg', '').replace('.png', '').replace('.webp', '')
    logger.debug(f"[COVER] Extracted hash: {hash_value}")

    # Find cover file using utility (tries hierarchical and flat paths, WebP and JPEG)
    result = find_cover_file(hash_value, library_name, try_webp=True)

    if result:
        cover_file, media_type = result
        from ...error_handling import safe_file_stat
        file_stat = safe_file_stat(cover_file, "cover file")
        size_info = f", size={file_stat.st_size} bytes" if file_stat else ""
        logger.info(f"[COVER] Serving cover: {cover_file}{size_info}, type={media_type}")
        return FileResponse(
            cover_file,
            media_type=media_type,
            headers={
                "Cache-Control": "public, max-age=604800",  # 7 days
                "Vary": "Accept-Encoding"
            }
        )

    # Cover not found
    logger.error(f"[COVER] Cover not found: library_id={library_id}, cover_path={cover_path}, hash={hash_value}")
    raise HTTPException(status_code=404, detail="Cover not found")

"""
API v2 Router

Modern JSON-based API endpoints for YACReader mobile apps.
This is the v2 API that newer mobile app versions prefer.
"""

import logging
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, Request, Response, Cookie, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from ...database import (
    get_library_by_id,
    get_all_libraries,
    get_folders_in_library,
    get_comics_in_folder,
    get_comic_by_id,
    get_sibling_comics,
    get_covers_dir,
    get_user_by_username,
    get_user_by_id,
    get_reading_progress,
    get_continue_reading,
    update_reading_progress,
)
from ..middleware import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2")


# ============================================================================
# Pydantic Models for v2 API
# ============================================================================

class LibraryInfo(BaseModel):
    """Library information"""
    id: int
    name: str
    path: str


class VersionInfo(BaseModel):
    """Server version information"""
    version: str
    name: str
    api_version: str


# ============================================================================
# Version Endpoint
# ============================================================================

@router.get("/version")
async def get_version():
    """
    Get server version information

    This is one of the first endpoints the mobile app calls
    Returns plain text version number like YACReader does
    """
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("9.14.2")


# ============================================================================
# Libraries
# ============================================================================

@router.get("/libraries")
async def get_libraries(request: Request):
    """
    Get all libraries (v2 JSON format)

    Returns list of libraries as JSON
    """
    db = request.app.state.db

    with db.get_session() as session:
        libraries = get_all_libraries(session)

        result = []
        for lib in libraries:
            result.append({
                "name": lib.name,
                "id": lib.id,
                "uuid": lib.uuid
            })

        return JSONResponse(result)


# ============================================================================
# Folder Content
# ============================================================================

@router.get("/library/{library_id}/folder/{folder_id}")
async def get_folder_v2(
    library_id: int,
    folder_id: int,
    request: Request,
    sort: Optional[str] = "folders_first"
):
    """
    Get folder contents (v2 JSON format)

    This is what the mobile app calls when browsing folders
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Get library
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        logger.info(f"v2 API: Getting folder {folder_id} in library {library_id}")

        # Get folders
        folders = get_folders_in_library(session, library_id)
        logger.debug(f"v2 API: Found {len(folders)} total folders in library {library_id}")
        child_folders = []

        for folder in folders:
            # YACReader convention (from source code db_helper.cpp:1540):
            # - Folder ID=1 is typically a special root folder (never shown)
            # - parentId=1 or parentId=None means "top-level folder"
            # - Requesting folder_id=0 or folder_id=1 means "show library root"
            #
            # NOTE: Our scanner creates folders with parent_id=None for top-level
            # YACReader uses parent_id=1 for top-level and reserves folder id=1 as root
            # We support both conventions for compatibility

            # Skip root folder (marked with __ROOT__ name) - never show in listings
            if folder.name == "__ROOT__":
                continue

            is_root_request = (folder_id <= 1)  # 0 or 1 both mean root

            if is_root_request:
                # Root level request - show top-level folders (parent_id=None or parent_id != self)
                # After migration, top-level folders have parent_id pointing to __ROOT__ folder
                if folder.parent_id is not None and folder.parent_id != 1:
                    # Check if parent is a root folder
                    parent = next((f for f in folders if f.id == folder.parent_id), None)
                    if parent and parent.name != "__ROOT__":
                        # Parent is not root, skip this folder
                        continue
            else:
                # Specific folder request - show its children only
                if folder.parent_id != folder_id:
                    continue

            # Get first comic in this folder for the cover
            from ...database.models import Comic, Folder as FolderModel
            first_comic = session.query(Comic).filter_by(
                library_id=library_id,
                folder_id=folder.id
            ).order_by(Comic.filename).first()

            first_comic_hash = first_comic.hash if first_comic else ""

            # Count child folders and comics
            num_child_folders = session.query(FolderModel).filter_by(parent_id=folder.id).count()
            num_child_comics = session.query(Comic).filter_by(folder_id=folder.id).count()
            num_children = num_child_folders + num_child_comics

            try:
                relative_path = str(Path(folder.path).relative_to(library.path))
            except ValueError:
                relative_path = folder.name # Fallback

            api_path = f"/{relative_path}"

            child_folders.append({
                "type": "folder",
                "id": str(folder.id),
                "library_id": str(library_id),
                "library_uuid": library.uuid,
                "folder_name": folder.name,
                "num_children": num_children,
                "first_comic_hash": first_comic_hash,
                "finished": False,
                "completed": False,
                "custom_image": False,
                "file_type": 0,
                "added": folder.created_at,
                "updated": folder.updated_at,
                "parent_id": str(folder.parent_id) if folder.parent_id is not None else "0",
                "path": api_path
            })

        # Sort folders alphabetically
        child_folders.sort(key=lambda f: f['folder_name'].lower())
        logger.info(f"v2 API: Returning {len(child_folders)} folders for folder_id={folder_id}")

        # Get comics - need to handle root folder specially
        # folder_id <= 1 means root (0 or 1)
        from ...database.models import Comic
        is_root_request = (folder_id <= 1)

        if is_root_request:
            # Root folder request - get comics in the __ROOT__ folder for this library
            # Find the root folder ID (marked with __ROOT__ name)
            root_folder = next((f for f in folders if f.name == "__ROOT__"), None)
            if root_folder:
                # Get comics with folder_id pointing to root folder
                comics = session.query(Comic).filter(
                    Comic.library_id == library_id,
                    (Comic.folder_id == root_folder.id) | (Comic.folder_id == None)
                ).all()
            else:
                # Fallback: no root folder found, get comics with folder_id=None
                comics = session.query(Comic).filter(
                    Comic.library_id == library_id,
                    Comic.folder_id == None
                ).all()
        else:
            # Specific folder - get its comics (filter by library to avoid cross-library issues)
            comics = get_comics_in_folder(session, folder_id, library_id=library_id)

        # Get user for reading progress (from session or default to admin)
        user_id = get_current_user_id(request)
        if user_id:
            user = get_user_by_id(session, user_id)
        else:
            user = get_user_by_username(session, 'admin')

        comics_list = []
        for comic in comics:
            # Get reading progress for this comic
            current_page = 0
            is_read = False
            has_been_opened = False
            if user:
                progress = get_reading_progress(session, user.id, comic.id)
                if progress:
                    current_page = progress.current_page
                    is_read = progress.is_completed
                    has_been_opened = current_page > 0
            try:
                relative_path = str(Path(comic.path).relative_to(library.path))
            except ValueError:
                relative_path = comic.filename

            api_path = f"/{relative_path}"
            comics_list.append({
                "type": "comic",
                "id": str(comic.id),
                "comic_info_id": str(comic.id),  # Using comic id as comic_info_id
                "parent_id": str(comic.folder_id) if comic.folder_id is not None else "0",
                "library_id": str(library_id),
                "library_uuid": library.uuid,
                "file_name": comic.filename,
                "file_size": str(comic.file_size),
                "hash": comic.hash,
                "path": api_path, # <-- *** THIS IS FIX #1 ***
                "current_page": current_page,
                "num_pages": comic.num_pages,
                "read": is_read,
                "manga": (comic.reading_direction == 'rtl') if hasattr(comic, 'reading_direction') else False,
                "file_type": 1,  # 1 = comic (vs 0 = folder)
                "cover_size_ratio": 0.0,
                "number": 0,
                "has_been_opened": has_been_opened
            })

        # Sort comics
        if sort == "folders_first" or sort == "alphabetical":
            comics_list.sort(key=lambda c: c['file_name'].lower())
        elif sort == "date_added":
            comics_list.sort(key=lambda c: c.get('created_at', 0), reverse=True)

        total_items = len(child_folders) + len(comics_list)
        logger.info(f"v2 API: Returning {len(child_folders)} folders and {len(comics_list)} comics (total: {total_items} items)")

        # Return combined list (folders first)
        # Return as array - some apps expect this format
        result = child_folders + comics_list
        logger.debug(f"v2 API: Response contains {len(result)} items")
        return JSONResponse(result)


@router.get("/library/{library_id}/folder/{folder_id}/content")
async def get_folder_content_json(
    library_id: int,
    folder_id: int,
    request: Request,
    sort: Optional[str] = "folders_first"
):
    """
    Get folder contents as JSON (alternative endpoint)

    Some versions of the app might use this endpoint
    """
    # Just redirect to the main folder endpoint
    return await get_folder_v2(library_id, folder_id, request, sort)


# ============================================================================
# Comic Full Info (v2)
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
    db = request.app.state.db

    with db.get_session() as session:
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get reading progress
        current_page = 0
        is_read = False
        user_id = get_current_user_id(request)
        if user_id:
            user = get_user_by_id(session, user_id)
        else:
            user = get_user_by_username(session, 'admin')
        if user:
            progress = get_reading_progress(session, user.id, comic_id)
            if progress:
                current_page = progress.current_page
                is_read = progress.is_completed

        # --- START FIX 2 ---
        try:
            # Calculate the relative path from the library root
            relative_path = str(Path(comic.path).relative_to(library.path))
        except ValueError:
            relative_path = comic.filename  # Fallback
        
        # Prepend a slash as the API requires
        api_path = f"/{relative_path}"
        # --- END FIX 2 ---

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
            "path": api_path, # <-- *** THIS IS FIX #2 ***
            "current_page": current_page,
            "num_pages": comic.num_pages,
            "read": is_read,
            "manga": comic.reading_direction == 'rtl' if hasattr(comic, 'reading_direction') else False,
            "file_type": 1,
            "cover_size_ratio": 0.0,
            "number": 0,
            "has_been_opened": current_page > 0,
        }

        # Add optional metadata fields if available
        if comic.title:
            response["title"] = comic.title
        if comic.series:
            response["series"] = comic.series
        if comic.volume:
            response["volume"] = str(comic.volume)
        if comic.issue_number:
            response["universal_number"] = str(comic.issue_number)
        if hasattr(comic, 'synopsis') and comic.synopsis:
            response["synopsis"] = comic.synopsis
        if hasattr(comic, 'writer') and comic.writer:
            response["writer"] = comic.writer
        if hasattr(comic, 'publisher') and comic.publisher:
            response["publisher"] = comic.publisher

        return JSONResponse(response)


# ============================================================================
# Comic Remote Reading (v2)
# ============================================================================

@router.get("/library/{library_id}/comic/{comic_id}/remote")
async def open_comic_remote_v2(
    library_id: int,
    comic_id: int,
    request: Request,
    yacread_session: Optional[str] = Cookie(None)
):
    """
    Open comic for remote reading (v2 PLAIN TEXT format)

    Returns the same plain text format as v1 for compatibility
    """
    from fastapi.responses import PlainTextResponse

    db = request.app.state.db

    with db.get_session() as session:
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get reading progress
        current_page = 0
        is_read = 0
        user_id = get_current_user_id(request)
        if user_id:
            user = get_user_by_id(session, user_id)
        else:
            user = get_user_by_username(session, 'admin')
        if user:
            progress = get_reading_progress(session, user.id, comic_id)
            if progress:
                current_page = progress.current_page
                is_read = 1 if progress.is_completed else 0

        # Get previous/next comic for navigation
        prev_comic_id, next_comic_id = get_sibling_comics(session, comic_id)

        # --- START FIX 3 ---
        try:
            relative_path = str(Path(comic.path).relative_to(library.path))
        except ValueError:
            relative_path = comic.filename
        api_path = f"/{relative_path}"
        # --- END FIX 3 ---

        # Build plain text response in YACReader format
        lines = []
        lines.append(f"library:{library.name if library else 'Unknown'}")
        lines.append(f"libraryId:{library_id}")

        # Add navigation (previousComic/nextComic)
        if prev_comic_id is not None:
            lines.append(f"previousComic:{prev_comic_id}")
        if next_comic_id is not None:
            lines.append(f"nextComic:{next_comic_id}")

        # Comic info (matching comic.toTXT() format)
        lines.append(f"comicid:{comic_id}")
        lines.append(f"hash:{comic.hash}")
        lines.append(f"path:{api_path}") # <-- *** THIS IS FIX #3 ***
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
# Comic Page (v2)
# ============================================================================

@router.get("/library/{library_id}/comic/{comic_id}/page/{page_num}/remote")
async def get_comic_page_v2(
    library_id: int,
    comic_id: int,
    page_num: int,
    request: Request
):
    """
    Get comic page image (v2)

    Same as v1 but accessed via v2 path
    """
    db = request.app.state.db

    with db.get_session() as session:
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Import here to avoid circular imports
        from ...scanner import open_comic

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

            return Response(
                content=page_data,
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=86400"}
            )


# ============================================================================
# Comic Update (v2) - Save Reading Progress
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
    db = request.app.state.db

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

    with db.get_session() as session:
        # Get comic to verify it exists and get num_pages
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Use comic's num_pages as default (form data doesn't usually include this)
        total_pages = comic.num_pages

        # Get user from session
        user_id = get_current_user_id(request)
        if user_id:
            user = get_user_by_id(session, user_id)
        else:
            user = get_user_by_username(session, 'admin')

        if not user:
            raise HTTPException(status_code=500, detail="User not found")

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
# Cover Images (v2)
# ============================================================================

@router.get("/library/{library_id}/cover/{cover_path:path}")
async def get_cover_v2(
    library_id: int,
    cover_path: str,
    request: Request
):
    """
    Get cover image for a comic (v2)

    The cover_path is the hash.jpg filename
    Covers are stored in hierarchical structure: covers/ab/abc123.jpg
    """
    # Extract hash from path (e.g., "abc123.jpg" -> "abc123")
    hash_value = cover_path.replace('.jpg', '').replace('.jpeg', '').replace('.png', '')

    # Get covers directory - uses hierarchical storage (first 2 chars as subdirectory)
    covers_dir = get_covers_dir()

    # Try hierarchical path first (covers/ab/abc123.jpg)
    if len(hash_value) >= 2:
        subdir = hash_value[:2]
        cover_file = covers_dir / subdir / cover_path

        if cover_file.exists():
            return FileResponse(
                cover_file,
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=86400"}
            )

    # Try flat path as fallback (covers/abc123.jpg)
    cover_file = covers_dir / cover_path
    if cover_file.exists():
        return FileResponse(
            cover_file,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"}
        )

    # Cover not found
    raise HTTPException(status_code=404, detail="Cover not found")


# ============================================================================
# Search (Stub)
# ============================================================================

@router.get("/library/{library_id}/search")
async def search_comics_v2(
    library_id: int,
    q: str,
    request: Request
):
    """
    Search for comics (v2 JSON format)
    """
    # TODO: Implement search
    return JSONResponse({
        "results": []
    })


# ============================================================================
# Reading List / Favorites (Stubs)
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
        user_id = get_current_user_id(request)
        if user_id:
            user = get_user_by_id(session, user_id)
        else:
            user = get_user_by_username(session, 'admin')
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
                "manga": comic.reading_direction == 'rtl' if hasattr(comic, 'reading_direction') else False,
                "file_type": 1,
                "cover_size_ratio": 0.0,
                "number": 0,
                "count": 0,
                "date": "",
                "rating": 0,
                "synopsis": "",
                "title": comic.title or comic.filename,
                "has_been_opened": progress.current_page > 0,
                "last_time_opened": progress.last_read_at,
                "current_page_bookmarked": False,
                "cover_page": 0,
                "brightness": 0,
                "contrast": 0,
                "gamma": 1.0
            })

        return JSONResponse(comics_list)


@router.get("/library/{library_id}/favs")
async def get_favorites(library_id: int, request: Request):
    """Get favorites (stub)"""
    return JSONResponse([])


@router.get("/library/{library_id}/tags")
async def get_tags(library_id: int, request: Request):
    """Get tags (stub)"""
    return JSONResponse([])


# ============================================================================
# Session Management (Stubs)
# ============================================================================

@router.get("/recoverSession")
async def recover_session(request: Request):
    """Recover session (stub)"""
    return JSONResponse({"recovered": False})


@router.post("/sync")
async def sync_session(request: Request):
    """Sync session data (stub)"""
    return JSONResponse({"synced": True})
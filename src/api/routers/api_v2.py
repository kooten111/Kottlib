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
    get_reading_progress,
    get_continue_reading,
)

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
        child_folders = []
        for folder in folders:
            # Handle root folder (id=0 or id=1)
            if folder.parent_id == folder_id or (folder_id <= 1 and folder.parent_id is None):
                # Get first comic in this folder for the cover
                from ...database.models import Comic
                first_comic = session.query(Comic).filter_by(
                    library_id=library_id,
                    folder_id=folder.id
                ).order_by(Comic.filename).first()

                first_comic_hash = first_comic.hash if first_comic else ""

                child_folders.append({
                    "type": "folder",
                    "id": str(folder.id),
                    "library_id": str(library_id),
                    "folder_name": folder.name,
                    "num_children": 0,  # TODO: count children
                    "first_comic_hash": first_comic_hash,
                    "finished": False,
                    "completed": False,
                    "custom_image": False,
                    "file_type": 0,
                    "added": 0,
                    "updated": 0,
                    "parent_id": str(folder.parent_id) if folder.parent_id is not None else "0",
                    "path": folder.name
                })

        # Sort folders alphabetically
        child_folders.sort(key=lambda f: f['folder_name'].lower())

        # Get comics - need to handle root folder specially
        if folder_id > 1:
            # Normal folder
            comics = get_comics_in_folder(session, folder_id)
        else:
            # Root folder (0 or 1) - get comics with no folder_id
            from ...database.models import Comic
            comics = session.query(Comic).filter_by(
                library_id=library_id,
                folder_id=None
            ).all()

        comics_list = []
        for comic in comics:
            # Match YACReader's exact field names for v2 API
            comics_list.append({
                "type": "comic",
                "id": str(comic.id),
                "comic_info_id": str(comic.id),  # Using comic id as comic_info_id
                "parent_id": str(comic.folder_id) if comic.folder_id is not None else "0",
                "library_id": str(library_id),
                "file_name": comic.filename,
                "file_size": str(comic.size if hasattr(comic, 'size') else 0),
                "hash": comic.hash,
                "path": comic.path if hasattr(comic, 'path') else comic.filename,
                "current_page": 0,  # TODO: get from reading progress
                "num_pages": comic.num_pages,
                "read": False,  # TODO: get from reading progress
                "manga": (comic.reading_direction == 'rtl') if hasattr(comic, 'reading_direction') else False,
                "file_type": 1,  # 1 = comic (vs 0 = folder)
                "cover_size_ratio": 0.0,
                "number": 0,
                "has_been_opened": False
            })

        # Sort comics
        if sort == "folders_first" or sort == "alphabetical":
            comics_list.sort(key=lambda c: c['file_name'].lower())
        elif sort == "date_added":
            comics_list.sort(key=lambda c: c.get('created_at', 0), reverse=True)

        logger.info(f"v2 API: Returning {len(child_folders)} folders and {len(comics_list)} comics")

        # Return combined list (folders first)
        # Return as array - some apps expect this format
        return JSONResponse(child_folders + comics_list)


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

        # Get reading progress
        current_page = 0
        is_read = False
        user = get_user_by_username(session, 'admin')
        if user:
            progress = get_reading_progress(session, user.id, comic_id)
            if progress:
                current_page = progress.current_page
                is_read = progress.is_completed

        # Build full comic info response matching YACReader format
        response = {
            "type": "comic",
            "id": str(comic.id),
            "comic_info_id": str(comic.id),
            "parent_id": str(comic.folder_id) if comic.folder_id is not None else "0",
            "library_id": str(library_id),
            "library_uuid": library.uuid if library else "",
            "file_name": comic.filename,
            "file_size": str(0),  # TODO: get actual file size
            "hash": comic.hash,
            "path": comic.path or comic.filename,
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

        # Get reading progress
        current_page = 0
        is_read = 0
        user = get_user_by_username(session, 'admin')
        if user:
            progress = get_reading_progress(session, user.id, comic_id)
            if progress:
                current_page = progress.current_page
                is_read = 1 if progress.is_completed else 0

        # Get previous/next comic for navigation
        prev_comic_id, next_comic_id = get_sibling_comics(session, comic_id)

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
        lines.append(f"path:{comic.path or comic.filename}")
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
async def get_reading_list(library_id: int, request: Request):
    """
    Get reading list / continue reading (v2 JSON format)

    Returns recently read comics that are in progress
    """
    # Return empty array for now (stub implementation)
    # TODO: Implement full continue reading functionality
    return JSONResponse([])


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

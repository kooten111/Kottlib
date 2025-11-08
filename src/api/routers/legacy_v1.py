"""
Legacy API v1 Router

YACReader-compatible API endpoints.
Implements the original YACReaderLibrary Server protocol for mobile app compatibility.

The mobile app expects text-based responses (not JSON).
"""

import logging
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Request, Response, Cookie, HTTPException
from fastapi.responses import PlainTextResponse, FileResponse

from ...database import (
    get_library_by_id,
    get_comics_in_library,
    get_comics_in_folder,
    get_folders_in_library,
    get_comic_by_id,
    get_covers_dir
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Session Management
# ============================================================================

def get_or_create_session(request: Request, yacread_session: Optional[str] = None) -> str:
    """
    Get existing session or create new one
    YACReader mobile app uses a session cookie
    """
    if yacread_session:
        return yacread_session

    # Create new session ID (simple for now)
    import uuid
    return str(uuid.uuid4())


# ============================================================================
# Library Listing
# ============================================================================

@router.get("/")
async def list_libraries(request: Request):
    """
    List all libraries (root endpoint)

    YACReader format:
    type:libraries
    code:0

    library:Library Name
    id:1
    path:/path/to/library

    library:Another Library
    id:2
    path:/path/to/another
    """
    db = request.app.state.db

    with db.get_session() as session:
        libraries = []
        # For now, we'll use hardcoded library for testing
        # In production, this would query the database
        libraries_text = "type:libraries\ncode:0\n\n"

        # TODO: Get from database
        # libs = get_all_libraries(session)
        # for lib in libs:
        #     libraries_text += f"library:{lib.name}\n"
        #     libraries_text += f"id:{lib.id}\n"
        #     libraries_text += f"path:{lib.path}\n\n"

        # For now, return empty library list
        return PlainTextResponse(libraries_text)


# ============================================================================
# Folder/Comic Listing
# ============================================================================

@router.get("/{library_id}/folder/{folder_id}")
async def get_folder_content(
    library_id: int,
    folder_id: int,
    request: Request,
    yacread_session: Optional[str] = Cookie(None)
):
    """
    Get folder contents (folders and comics)

    YACReader format:
    type:folder
    code:0

    folder:Folder Name
    id:123

    comic:Comic Name.cbz
    id:456
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Get library
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Build response
        response_text = "type:folder\ncode:0\n\n"

        # Get folders
        folders = get_folders_in_library(session, library_id)
        for folder in folders:
            if folder.parent_id == folder_id or (folder_id == 0 and folder.parent_id is None):
                response_text += f"folder:{folder.name}\n"
                response_text += f"id:{folder.id}\n\n"

        # Get comics
        comics = get_comics_in_folder(session, folder_id) if folder_id > 0 else []
        for comic in comics:
            response_text += f"comic:{comic.filename}\n"
            response_text += f"id:{comic.id}\n\n"

        return PlainTextResponse(response_text)


# ============================================================================
# Comic Metadata
# ============================================================================

@router.get("/{library_id}/comic/{comic_id}")
async def get_comic_info(
    library_id: int,
    comic_id: int,
    request: Request
):
    """
    Get comic metadata

    YACReader format:
    library:Library Name
    libraryId:1
    comicid:123
    hash:abc123
    path:/path/to/comic.cbz
    numpages:24
    rating:0
    currentPage:1
    contrast:-1
    read:0
    coverPage:1
    manga:0
    added:1234567890
    type:0
    """
    db = request.app.state.db

    with db.get_session() as session:
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        library = get_library_by_id(session, library_id)

        response_text = f"library:{library.name if library else 'Unknown'}\n"
        response_text += f"libraryId:{library_id}\n"
        response_text += f"comicid:{comic_id}\n"
        response_text += f"hash:{comic.hash}\n"
        response_text += f"path:{comic.path}\n"
        response_text += f"numpages:{comic.num_pages}\n"
        response_text += f"rating:0\n"
        response_text += f"currentPage:1\n"
        response_text += f"contrast:-1\n"
        response_text += f"read:0\n"
        response_text += f"coverPage:1\n"
        response_text += f"manga:{1 if comic.reading_direction == 'rtl' else 0}\n"
        response_text += f"added:{comic.created_at}\n"
        response_text += f"type:0\n"

        return PlainTextResponse(response_text)


# ============================================================================
# Cover/Thumbnail
# ============================================================================

@router.get("/{library_id}/comic/{comic_id}/cover")
async def get_comic_cover(
    library_id: int,
    comic_id: int,
    request: Request
):
    """
    Get comic cover thumbnail

    Returns JPEG thumbnail for mobile app compatibility
    """
    db = request.app.state.db

    with db.get_session() as session:
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Get cover path
        covers_dir = get_covers_dir()
        cover_path = covers_dir / f"{comic.hash}.jpg"

        if not cover_path.exists():
            raise HTTPException(status_code=404, detail="Cover not found")

        return FileResponse(
            cover_path,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=31536000"}  # Cache for 1 year
        )


# ============================================================================
# Page Reading
# ============================================================================

@router.get("/{library_id}/comic/{comic_id}/page/{page_num}")
async def get_comic_page(
    library_id: int,
    comic_id: int,
    page_num: int,
    request: Request
):
    """
    Get a specific page from a comic

    This extracts the page from the comic archive and returns it
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
                headers={"Cache-Control": "public, max-age=86400"}  # Cache for 24 hours
            )


# ============================================================================
# Reading Progress Update
# ============================================================================

@router.post("/{library_id}/comic/{comic_id}/setCurrentPage")
async def set_current_page(
    library_id: int,
    comic_id: int,
    request: Request
):
    """
    Update reading progress (current page)

    YACReader mobile app sends this to track reading position
    """
    # Get form data
    form_data = await request.form()
    page_num = int(form_data.get('page', 0))

    logger.info(f"Set current page for comic {comic_id} to {page_num}")

    # TODO: Store reading progress in database
    # For now, just acknowledge
    return PlainTextResponse("OK")


# ============================================================================
# Search (Stub)
# ============================================================================

@router.get("/{library_id}/search")
async def search_comics(
    library_id: int,
    q: str,
    request: Request
):
    """
    Search for comics in library

    Returns results in same format as folder listing
    """
    # TODO: Implement search
    response_text = "type:search\ncode:0\n\n"
    return PlainTextResponse(response_text)

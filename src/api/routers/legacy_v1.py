"""
Legacy API v1 Router

YACReader-compatible API endpoints.
Implements the original YACReaderLibrary Server protocol for mobile app compatibility.

The mobile app expects text-based responses (not JSON).
"""

import logging
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Request, Response, Cookie, HTTPException, Body
from fastapi.responses import PlainTextResponse, FileResponse
from pydantic import BaseModel

from ...database import (
    get_library_by_id,
    get_comics_in_library,
    get_comics_in_folder,
    get_folders_in_library,
    get_comic_by_id,
    get_sibling_comics,
    get_covers_dir,
    get_user_by_username,
    get_user_by_id,
    update_reading_progress,
    get_reading_progress,
    get_continue_reading,
    create_cover,
    get_best_cover,
)
from ..middleware import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Helper Functions
# ============================================================================

def format_v1_response(text: str) -> str:
    """
    Format V1 API response with proper line endings.
    YACReader mobile apps expect CRLF (\\r\\n) line endings, not just LF (\\n).
    """
    return text.replace('\n', '\r\n')


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
        # Get all libraries
        from ...database import get_all_libraries
        libs = get_all_libraries(session)
        
        libraries_text = "type:libraries\ncode:0\n\n"
        
        for lib in libs:
            libraries_text += f"library:{lib.name}\n"
            libraries_text += f"id:{lib.id}\n"
            libraries_text += f"path:{lib.path}\n\n"

        return PlainTextResponse(format_v1_response(libraries_text))


# ============================================================================
# Folder/Comic Listing
# ============================================================================

@router.get("/{library_id}/folder/{folder_id}/info")
async def get_folder_info(
    library_id: int,
    folder_id: int,
    request: Request
):
    """
    Get folder information in custom text format (v1 API)

    Returns a list of comics and subfolders in custom delimited format:
    /library/{libId}/comic/{comicId}:{fileName}:{fileSize}

    This is used by YACReader mobile apps for efficient folder browsing.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Get library
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get folders and comics recursively
        folders = get_folders_in_library(session, library_id)

        # Determine if this is a root request
        is_root_request = (folder_id <= 1)

        # Build response with recursive folder traversal
        lines = []

        def add_folder_comics(fid: int, recursive: bool = True):
            """Recursively add comics from folder and subfolders"""
            # Get comics in this folder
            comics = get_comics_in_folder(session, fid, library_id=library_id)
            for comic in comics:
                line = f"/library/{library_id}/comic/{comic.id}:{comic.filename}:{comic.file_size}"
                lines.append(line)

            # If recursive, process subfolders
            if recursive:
                for folder in folders:
                    if folder.parent_id == fid and folder.name != "__ROOT__":
                        add_folder_comics(folder.id, recursive=True)

        if is_root_request:
            # Root request - get all comics recursively from root
            root_folder = next((f for f in folders if f.name == "__ROOT__"), None)
            if root_folder:
                add_folder_comics(root_folder.id, recursive=True)
            else:
                # Fallback: get all comics in library
                all_comics = get_comics_in_library(session, library_id)
                for comic in all_comics:
                    line = f"/library/{library_id}/comic/{comic.id}:{comic.filename}:{comic.file_size}"
                    lines.append(line)
        else:
            # Specific folder - get comics recursively from this folder
            add_folder_comics(folder_id, recursive=True)

        response_text = "\n".join(lines)
        return PlainTextResponse(format_v1_response(response_text))


@router.get("/{library_id}/folder/{folder_id}")
async def get_folder_content(
    library_id: int,
    folder_id: int,
    request: Request,
    sort: Optional[str] = "folders_first",
    yacread_session: Optional[str] = Cookie(None)
):
    """
    Get folder contents (folders and comics)

    Query parameters:
    - sort: Sorting mode (folders_first, alphabetical, date_added, recently_read)
            Default: folders_first

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

        # YACReader convention (from source code db_helper.cpp:1540):
        # - Folder ID=1 is typically a special root folder (never shown)
        # - parentId=1 or parentId=None means "top-level folder"
        # - Requesting folder_id=0 or folder_id=1 means "show library root"
        #
        # NOTE: Our scanner creates folders with parent_id=None for top-level
        # YACReader uses parent_id=1 for top-level and reserves folder id=1 as root
        # We support both conventions for compatibility

        is_root_request = (folder_id <= 1)  # 0 or 1 both mean root

        child_folders = []
        for folder in folders:
            # Skip root folder (marked with __ROOT__ name) - never show in listings
            if folder.name == "__ROOT__":
                continue

            if is_root_request:
                # Root level request - show top-level folders (parent_id=None or points to __ROOT__)
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
            child_folders.append(folder)

        # Sort folders alphabetically by name
        child_folders.sort(key=lambda f: f.name.lower())

        # Get comics (filter by library to avoid cross-library issues)
        if is_root_request:
            # Root level - get comics in the __ROOT__ folder for this library
            # Find the root folder ID (marked with __ROOT__ name)
            from ...database.models import Comic
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
            comics = get_comics_in_folder(session, folder_id, library_id=library_id)
        comics_list = list(comics)

        # Sort comics based on sort mode
        if sort == "folders_first" or sort == "alphabetical":
            # Alphabetical by filename
            comics_list.sort(key=lambda c: c.filename.lower())
        elif sort == "date_added":
            # Newest first
            comics_list.sort(key=lambda c: c.created_at, reverse=True)
        elif sort == "recently_read":
            # Sort by last_read_at from reading_progress
            user_id = get_current_user_id(request)
            if user_id:
                user = get_user_by_id(session, user_id)
            else:
                user = get_user_by_username(session, 'admin')
            
            if user:
                # Get reading progress for all comics in this folder
                comic_ids = [c.id for c in comics_list]
                from ...database.models import ReadingProgress
                progress_map = {}
                if comic_ids:
                    progress_records = session.query(ReadingProgress).filter(
                        ReadingProgress.user_id == user.id,
                        ReadingProgress.comic_id.in_(comic_ids)
                    ).all()
                    for p in progress_records:
                        progress_map[p.comic_id] = p.last_read_at
                
                # Sort by last_read_at (descending), then date_added
                comics_list.sort(key=lambda c: (progress_map.get(c.id, 0), c.created_at), reverse=True)
            else:
                # Fallback if no user
                comics_list.sort(key=lambda c: c.created_at, reverse=True)

        # Output folders first (always), then comics
        for folder in child_folders:
            response_text += f"folder:{folder.name}\n"
            response_text += f"id:{folder.id}\n\n"

        for comic in comics_list:
            response_text += f"comic:{comic.filename}\n"
            response_text += f"id:{comic.id}\n\n"

        return PlainTextResponse(format_v1_response(response_text))


# ============================================================================
# Comic Metadata
# ============================================================================

@router.get("/{library_id}/comic/{comic_id}/info")
async def get_comic_full_info(
    library_id: int,
    comic_id: int,
    request: Request,
    yacread_session: Optional[str] = Cookie(None)
):
    """
    Get full comic information in text format (v1 API)

    YACReader format:
    library:{libraryName}
    libraryId:{libraryId}
    {key}:{value}
    ...

    This returns all comic metadata fields in the key:value text format.
    """
    db = request.app.state.db

    with db.get_session() as session:
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        library = get_library_by_id(session, library_id)

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

        # Build response with all comic fields
        response_text = f"library:{library.name if library else 'Unknown'}\n"
        response_text += f"libraryId:{library_id}\n"
        response_text += f"comicid:{comic_id}\n"
        response_text += f"hash:{comic.hash}\n"
        response_text += f"path:{comic.path}\n"
        response_text += f"numpages:{comic.num_pages}\n"
        response_text += f"rating:{comic.rating or 0}\n"
        response_text += f"currentPage:{current_page}\n"
        response_text += f"contrast:-1\n"
        response_text += f"read:{is_read}\n"
        response_text += f"coverPage:{comic.cover_page or 1}\n"
        response_text += f"manga:{1 if comic.reading_direction == 'rtl' else 0}\n"
        response_text += f"added:{comic.created_at}\n"
        response_text += f"type:0\n"

        # Add optional metadata fields if present
        if comic.title:
            response_text += f"title:{comic.title}\n"
        if comic.series:
            response_text += f"series:{comic.series}\n"
        if comic.volume:
            response_text += f"volume:{comic.volume}\n"
        if comic.issue_number:
            response_text += f"number:{comic.issue_number}\n"
        if comic.year:
            response_text += f"year:{comic.year}\n"
        if comic.writer:
            response_text += f"writer:{comic.writer}\n"
        if comic.artist:
            response_text += f"artist:{comic.artist}\n"
        if comic.publisher:
            response_text += f"publisher:{comic.publisher}\n"
        if comic.description:
            response_text += f"synopsis:{comic.description}\n"
        if comic.genre:
            response_text += f"genre:{comic.genre}\n"

        return PlainTextResponse(format_v1_response(response_text))


@router.get("/{library_id}/comic/{comic_id}/remote")
async def get_comic_remote(
    library_id: int,
    comic_id: int,
    request: Request,
    yacread_session: Optional[str] = Cookie(None)
):
    """
    Get comic information for remote reading (v1 API)

    Similar to /info but includes previous/next comic navigation.
    """
    db = request.app.state.db

    with db.get_session() as session:
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        library = get_library_by_id(session, library_id)

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

        response_text = f"library:{library.name if library else 'Unknown'}\n"
        response_text += f"libraryId:{library_id}\n"
        if prev_comic_id is not None:
            response_text += f"previousComic:{prev_comic_id}\n"
        if next_comic_id is not None:
            response_text += f"nextComic:{next_comic_id}\n"
        response_text += f"comicid:{comic_id}\n"
        response_text += f"hash:{comic.hash}\n"
        response_text += f"path:{comic.path}\n"
        response_text += f"numpages:{comic.num_pages}\n"
        response_text += f"rating:{comic.rating or 0}\n"
        response_text += f"currentPage:{current_page}\n"
        response_text += f"contrast:-1\n"
        response_text += f"read:{is_read}\n"
        response_text += f"coverPage:{comic.cover_page or 1}\n"
        response_text += f"manga:{1 if comic.reading_direction == 'rtl' else 0}\n"
        response_text += f"added:{comic.created_at}\n"
        response_text += f"type:0\n"

        # Add optional metadata fields if present
        if comic.title:
            response_text += f"title:{comic.title}\n"
        if comic.series:
            response_text += f"series:{comic.series}\n"
        if comic.volume:
            response_text += f"volume:{comic.volume}\n"
        if comic.issue_number:
            response_text += f"number:{comic.issue_number}\n"

        return PlainTextResponse(format_v1_response(response_text))


@router.get("/{library_id}/comic/{comic_id}")
async def get_comic_info(
    library_id: int,
    comic_id: int,
    request: Request,
    yacread_session: Optional[str] = Cookie(None)
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

        response_text = f"library:{library.name if library else 'Unknown'}\n"
        response_text += f"libraryId:{library_id}\n"
        if prev_comic_id is not None:
            response_text += f"previousComic:{prev_comic_id}\n"
        if next_comic_id is not None:
            response_text += f"nextComic:{next_comic_id}\n"
        response_text += f"comicid:{comic_id}\n"
        response_text += f"hash:{comic.hash}\n"
        response_text += f"path:{comic.path}\n"
        response_text += f"numpages:{comic.num_pages}\n"
        response_text += f"rating:0\n"
        response_text += f"currentPage:{current_page}\n"
        response_text += f"contrast:-1\n"
        response_text += f"read:{is_read}\n"
        response_text += f"coverPage:1\n"
        response_text += f"manga:{1 if comic.reading_direction == 'rtl' else 0}\n"
        response_text += f"added:{comic.created_at}\n"
        response_text += f"type:0\n"

        return PlainTextResponse(format_v1_response(response_text))


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
    Uses custom cover if available, otherwise falls back to auto-generated cover
    """
    main_db = request.app.state.db

    # Get comic from main DB
    with main_db.get_session() as session:
        # Get library metadata
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")
        library_name = library.name

        # Get comic hash
        from ...database.models import Comic
        comic = session.query(Comic).filter(Comic.id == comic_id).first()

        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        comic_hash = comic.hash

        # Try to get best cover (custom or auto)
        cover = get_best_cover(session, comic_id)

    if cover and Path(cover.jpeg_path).exists():
        # Use cover from database
        return FileResponse(
            cover.jpeg_path,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=31536000"}  # Cache for 1 year
        )

    # Fall back to hash-based path (for backward compatibility)
    covers_dir = get_covers_dir(library_name)

    # Try hierarchical path first (covers/ab/abc123.jpg)
    if len(comic_hash) >= 2:
        subdir = comic_hash[:2]
        # Try WebP first
        webp_path = covers_dir / subdir / f"{comic_hash}.webp"
        if webp_path.exists():
            return FileResponse(
                webp_path,
                media_type="image/webp",
                headers={"Cache-Control": "public, max-age=31536000"}
            )
        # Try JPEG
        jpeg_path = covers_dir / subdir / f"{comic_hash}.jpg"
        if jpeg_path.exists():
            return FileResponse(
                jpeg_path,
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=31536000"}
            )

    # Try flat path as fallback
    cover_path = covers_dir / f"{comic_hash}.jpg"
    if cover_path.exists():
        return FileResponse(
            cover_path,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=31536000"}
        )

    raise HTTPException(status_code=404, detail="Cover not found")


@router.post("/{library_id}/comic/{comic_id}/setCustomCover")
async def set_custom_cover(
    library_id: int,
    comic_id: int,
    request: Request
):
    """
    Set a custom cover for a comic from a specific page

    Form data:
    - page: Page number to use as cover (0-indexed)
    """
    db = request.app.state.db

    # Get form data
    form_data = await request.form()
    page_num = int(form_data.get('page', 0))

    logger.info(f"Setting custom cover for comic {comic_id} from page {page_num}")

    with db.get_session() as session:
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Get library to determine covers directory
        library = get_library_by_id(session, library_id)
        library_name = library.name if library else None

        if page_num < 0 or page_num >= comic.num_pages:
            raise HTTPException(status_code=400, detail="Invalid page number")

        # Import scanner and thumbnail generator
        from ...scanner import open_comic
        from ...scanner.thumbnail_generator import generate_dual_thumbnails

        # Open comic and extract page
        comic_path = Path(comic.path)
        with open_comic(comic_path) as archive:
            if archive is None:
                raise HTTPException(status_code=500, detail="Failed to open comic")

            # Get page image
            page_data = archive.get_page(page_num)
            if page_data is None:
                raise HTTPException(status_code=500, detail="Failed to extract page")

            # Load as PIL Image
            from PIL import Image
            from io import BytesIO
            page_image = Image.open(BytesIO(page_data))

            # Generate custom cover thumbnails (library-specific directory)
            covers_dir = get_covers_dir(library_name)
            custom_hash = f"{comic.hash}_custom"

            jpeg_ok, webp_ok = generate_dual_thumbnails(
                page_image,
                covers_dir,
                custom_hash
            )

            if not jpeg_ok:
                raise HTTPException(status_code=500, detail="Failed to generate cover")

            # Create cover entry
            jpeg_path = str(covers_dir / f"{custom_hash}.jpg")
            webp_path = str(covers_dir / f"{custom_hash}.webp") if webp_ok else None

            create_cover(
                session,
                comic_id=comic_id,
                cover_type='custom',
                page_number=page_num,
                jpeg_path=jpeg_path,
                webp_path=webp_path
            )

    return PlainTextResponse("OK")


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
    request: Request,
    yacread_session: Optional[str] = Cookie(None)
):
    """
    Update reading progress (current page)

    YACReader mobile app sends this to track reading position
    """
    db = request.app.state.db

    # Get form data
    form_data = await request.form()
    page_num = int(form_data.get('page', 0))

    logger.info(f"Set current page for comic {comic_id} to {page_num}")

    with db.get_session() as session:
        # Get comic to verify it exists and get total pages
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Get user from session
        user_id = get_current_user_id(request)
        if user_id:
            user = get_user_by_id(session, user_id)
        else:
            user = get_user_by_username(session, 'admin')
        if not user:
            # If no admin user, just acknowledge without storing
            logger.warning("No admin user found, cannot store reading progress")
            return PlainTextResponse("OK")

        # Update reading progress
        update_reading_progress(
            session,
            user_id=user.id,
            comic_id=comic_id,
            current_page=page_num,
            total_pages=comic.num_pages
        )

    return PlainTextResponse("OK")


# ============================================================================
# Continue Reading
# ============================================================================

@router.get("/continue-reading")
async def continue_reading_list(
    request: Request,
    limit: int = 10,
    yacread_session: Optional[str] = Cookie(None)
):
    """
    Get "Continue Reading" list

    Returns recently read comics that are in progress

    Format is similar to folder listing but with progress information
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Get user from session
        user_id = get_current_user_id(request)
        if user_id:
            user = get_user_by_id(session, user_id)
        else:
            user = get_user_by_username(session, 'admin')
        if not user:
            # Return empty list if no user
            return PlainTextResponse(format_v1_response("type:continue-reading\ncode:0\n\n"))

        # Get continue reading list
        results = get_continue_reading(session, user.id, limit)

        response_text = "type:continue-reading\ncode:0\n\n"

        for progress, comic in results:
            library = get_library_by_id(session, comic.library_id)
            response_text += f"comic:{comic.filename}\n"
            response_text += f"id:{comic.id}\n"
            response_text += f"libraryId:{comic.library_id}\n"
            response_text += f"library:{library.name if library else 'Unknown'}\n"
            response_text += f"currentPage:{progress.current_page}\n"
            response_text += f"totalPages:{progress.total_pages}\n"
            response_text += f"progress:{progress.progress_percent:.1f}\n"
            response_text += f"lastRead:{progress.last_read_at}\n"
            response_text += f"hash:{comic.hash}\n\n"

        return PlainTextResponse(format_v1_response(response_text))


# ============================================================================
# Search (Stub)
# ============================================================================

@router.get("/{library_id}/search")
@router.post("/{library_id}/search")
async def search_comics(
    library_id: int,
    request: Request,
    q: Optional[str] = None
):
    """
    Search for comics in library

    Returns results in same format as folder listing

    Supports both GET and POST methods:
    - GET: query via ?q=search_term
    - POST: query via JSON body {"q": "search_term"} or form data

    Args:
        library_id: ID of the library to search in
        q: Search query string (GET parameter)

    Returns:
        Plain text response with matching comics in V1 format
    """
    # Get query from GET parameter or POST body
    query = q

    # If it's a POST request and no query param, try to get from body
    if request.method == "POST" and not query:
        try:
            # Try to parse JSON body
            body = await request.json()
            # Support both "query" and "q" field names
            query = body.get("query", body.get("q", ""))
        except:
            # If JSON parsing fails, try form data
            try:
                form = await request.form()
                query = form.get("query", form.get("q", ""))
            except:
                pass

    if not query or not query.strip():
        response_text = "type:search\ncode:0\n\n"
        return PlainTextResponse(format_v1_response(response_text))

    logger.info(f"v1 API: Search in library {library_id} for '{query}'")

    db = request.app.state.db

    with db.get_session() as session:
        # Get library
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Perform search
        from ...database.database import search_comics as db_search_comics
        comics = db_search_comics(session, library_id, query)

        logger.info(f"v1 API: Found {len(comics)} comics matching '{query}'")

        # Format results in V1 text format
        response_text = "type:search\ncode:0\n\n"

        for comic in comics:
            response_text += f"comic:{comic.filename}\n"
            response_text += f"id:{comic.id}\n\n"

        return PlainTextResponse(format_v1_response(response_text))


# ============================================================================
# Sync (v1)
# ============================================================================

@router.post("/sync")
async def sync_reading_progress_v1(
    request: Request,
    yacread_session: Optional[str] = Cookie(None)
):
    """
    Sync reading progress (v1 API)

    Accepts JSON body with reading progress data and syncs it to the server.
    Expected format:
    {
        "comics": [
            {"comicId": 123, "currentPage": 5, "totalPages": 20},
            ...
        ]
    }
    """
    db = request.app.state.db

    try:
        # Parse JSON body
        body = await request.json()
        comics = body.get("comics", [])

        # Get user from session
        user_id = get_current_user_id(request)
        if user_id:
            user = None
            with db.get_session() as session:
                user = get_user_by_id(session, user_id)
        else:
            user = None
            with db.get_session() as session:
                user = get_user_by_username(session, 'admin')

        if not user:
            return PlainTextResponse("ERROR: User not found", status_code=401)

        # Update reading progress for each comic
        synced_count = 0
        with db.get_session() as session:
            for comic_data in comics:
                comic_id = comic_data.get("comicId")
                current_page = comic_data.get("currentPage", 0)
                total_pages = comic_data.get("totalPages")

                if comic_id is not None:
                    update_reading_progress(
                        session,
                        user_id=user.id,
                        comic_id=comic_id,
                        current_page=current_page,
                        total_pages=total_pages
                    )
                    synced_count += 1

        logger.info(f"v1 Sync: Updated {synced_count} comics for user {user.username}")
        return PlainTextResponse(f"OK: Synced {synced_count} comics")

    except Exception as e:
        logger.error(f"v1 Sync error: {e}", exc_info=True)
        return PlainTextResponse(f"ERROR: {str(e)}", status_code=500)

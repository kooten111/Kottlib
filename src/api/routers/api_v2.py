"""
API v2 Router

Modern JSON-based API endpoints for YACReader mobile apps.
This is the v2 API that newer mobile app versions prefer.
"""

import logging
import re
from typing import Optional, List
from pathlib import Path
from functools import lru_cache

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
    get_first_comic_recursive,
)
from ...database.models import Comic, ReadingProgress
from ..middleware import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2")

# In-memory cache for parsed series trees (cache key: library_id + cache_timestamp)
_series_tree_cache = {}


# ============================================================================
# Helper Functions
# ============================================================================

def get_comic_display_name(comic) -> str:
    """
    Get the display name for a comic.
    
    Returns the comic title if available, otherwise the filename without extension.
    This ensures folders show their actual names and comics show clean filenames.
    
    Args:
        comic: Comic model instance
        
    Returns:
        Display name for the comic
    """
    if comic.title:
        return comic.title
    # Strip common comic extensions (.cbz, .cbr, .cb7, .cbt)
    return re.sub(r'\.(cbz|cbr|cb7|cbt)$', '', comic.filename, flags=re.IGNORECASE)


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
            # Count comics in library
            comic_count = session.query(Comic).filter(Comic.library_id == lib.id).count()

            result.append({
                "name": lib.name,
                "id": lib.id,
                "uuid": lib.uuid,
                "path": lib.path,
                "comicCount": comic_count
            })

        return JSONResponse(result)


@router.get("/library/{library_id}/info")
async def get_library_info(library_id: int, request: Request):
    """
    Get library information (v2 JSON format)

    Returns detailed library info
    """
    db = request.app.state.db

    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Count comics in library
        comic_count = session.query(Comic).filter(Comic.library_id == library.id).count()

        return JSONResponse({
            "name": library.name,
            "id": library.id,
            "uuid": library.uuid,
            "path": library.path,
            "comicCount": comic_count
        })


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

            # Get first comic in this folder for the cover (recursively search subfolders if needed)
            from ...database.models import Comic, Folder as FolderModel
            first_comic = get_first_comic_recursive(session, folder.id, library_id)

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
            last_read_at = 0
            if user:
                progress = get_reading_progress(session, user.id, comic.id)
                if progress:
                    current_page = progress.current_page
                    is_read = progress.is_completed
                    has_been_opened = current_page > 0
                    last_read_at = progress.last_read_at
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
                "has_been_opened": has_been_opened,
                "last_read": last_read_at,
                # Add metadata for proper sorting
                "issue_number": comic.issue_number,
                "volume": comic.volume
            })

        # Sort comics
        if sort == "folders_first" or sort == "alphabetical":
            # Sort by volume and issue_number first (numeric), then fallback to filename parsing
            def comic_sort_key(c):
                # Use volume and issue_number for numeric sorting if available
                volume = c.get('volume') or 0
                issue_number = c.get('issue_number')
                filename = c['file_name']

                # If no issue_number from metadata, try to extract from filename
                if issue_number is None or issue_number == 0:
                    # Try common patterns: c001, ch001, chapter 001, #001, etc.
                    patterns = [
                        r'c(?:h(?:apter)?)?[\s_\-#]*(\d+)',  # c001, ch001, chapter 001
                        r'#(\d+)',  # #001
                        r'(\d+)',  # Any number sequence (fallback)
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, filename, re.IGNORECASE)
                        if match:
                            try:
                                issue_number = float(match.group(1))
                                break
                            except ValueError:
                                pass

                    # If still no number found, use 0
                    if issue_number is None:
                        issue_number = 0

                # Sort by: (volume, issue_number, filename_lowercase)
                # This ensures comics with metadata sort numerically,
                # and comics without metadata also sort numerically by extracted chapter numbers
                return (volume, issue_number, filename.lower())

            comics_list.sort(key=comic_sort_key)
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

    Serves WebP format when available (better quality, smaller size),
    with JPEG fallback for compatibility.
    """
    # Extract hash from path (e.g., "abc123.jpg" -> "abc123")
    hash_value = cover_path.replace('.jpg', '').replace('.jpeg', '').replace('.png', '').replace('.webp', '')

    # Get covers directory - uses hierarchical storage (first 2 chars as subdirectory)
    covers_dir = get_covers_dir()

    # Try WebP first (better quality and smaller size)
    if len(hash_value) >= 2:
        subdir = hash_value[:2]

        # Try hierarchical WebP path (covers/ab/abc123.webp)
        webp_file = covers_dir / subdir / f"{hash_value}.webp"
        if webp_file.exists():
            return FileResponse(
                webp_file,
                media_type="image/webp",
                headers={"Cache-Control": "public, max-age=86400"}
            )

        # Try hierarchical JPEG path (covers/ab/abc123.jpg)
        cover_file = covers_dir / subdir / cover_path
        if cover_file.exists():
            return FileResponse(
                cover_file,
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=86400"}
            )

    # Try flat path as fallback
    # Try WebP first
    webp_file = covers_dir / f"{hash_value}.webp"
    if webp_file.exists():
        return FileResponse(
            webp_file,
            media_type="image/webp",
            headers={"Cache-Control": "public, max-age=86400"}
        )

    # Try JPEG
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
        from ...database.database import search_comics
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
                "manga": (comic.reading_direction == 'rtl') if hasattr(comic, 'reading_direction') else False,
                "file_type": 1,  # 1 = comic
                "cover_size_ratio": 0.0,
                "number": 0,
                "has_been_opened": has_been_opened
            })

        logger.debug(f"v2 API: Returning {len(results)} search results")
        return JSONResponse(results)


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


@router.get("/library/{library_id}/favs")
async def get_favorites(library_id: int, request: Request):
    """
    Get favorite comics for the current user

    Returns array of favorite comics in YACReader v2 format
    """
    from ...database import get_user_favorites, get_user_by_username, get_library_by_id
    from ..middleware import get_current_user_id

    db = request.app.state.db

    with db.get_session() as session:
        # Get library to verify it exists and get UUID
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get user from session
        user_id = get_current_user_id(request)
        if user_id:
            from ...database import get_user_by_id
            user = get_user_by_id(session, user_id)
        else:
            user = get_user_by_username(session, 'admin')

        if not user:
            raise HTTPException(status_code=500, detail="User not found")

        # Get user's favorites
        favorites = get_user_favorites(session, user.id, library_id)

        # Format comics in v2 format
        comics_list = []
        for comic in favorites:
            # Get reading progress
            progress = get_reading_progress(session, user.id, comic.id)
            current_page = progress.current_page if progress else 0
            is_read = progress.is_completed if progress else False

            comics_list.append({
                "type": "comic",
                "id": str(comic.id),
                "comic_info_id": str(comic.id),
                "parent_id": str(comic.folder_id) if comic.folder_id else "0",
                "library_id": str(library_id),
                "library_uuid": library.uuid,
                "file_name": comic.filename,
                "file_size": str(comic.file_size),
                "hash": comic.hash,
                "path": comic.path,
                "current_page": current_page,
                "num_pages": comic.num_pages,
                "read": is_read,
                "manga": comic.reading_direction == "rtl",
                "file_type": 1,
                "number": comic.issue_number or 0,
                "title": get_comic_display_name(comic),
                "added": comic.created_at
            })

        logger.debug(f"v2 API: Returning {len(comics_list)} favorite comics for user {user.id}")
        return JSONResponse(comics_list)


@router.post("/library/{library_id}/comic/{comic_id}/fav")
async def add_to_favorites(library_id: int, comic_id: int, request: Request):
    """
    Add a comic to favorites

    Returns success status
    """
    from ...database import add_favorite, get_user_by_username, get_comic_by_id
    from ..middleware import get_current_user_id

    db = request.app.state.db

    with db.get_session() as session:
        # Verify comic exists
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Get user from session
        user_id = get_current_user_id(request)
        if user_id:
            from ...database import get_user_by_id
            user = get_user_by_id(session, user_id)
        else:
            user = get_user_by_username(session, 'admin')

        if not user:
            raise HTTPException(status_code=500, detail="User not found")

        # Add to favorites
        add_favorite(session, user.id, library_id, comic_id)

        logger.debug(f"v2 API: Added comic {comic_id} to favorites for user {user.id}")
        return JSONResponse({"success": True})


@router.delete("/library/{library_id}/comic/{comic_id}/fav")
async def remove_from_favorites(library_id: int, comic_id: int, request: Request):
    """
    Remove a comic from favorites

    Returns success status
    """
    from ...database import remove_favorite, get_user_by_username
    from ..middleware import get_current_user_id

    db = request.app.state.db

    with db.get_session() as session:
        # Get user from session
        user_id = get_current_user_id(request)
        if user_id:
            from ...database import get_user_by_id
            user = get_user_by_id(session, user_id)
        else:
            user = get_user_by_username(session, 'admin')

        if not user:
            raise HTTPException(status_code=500, detail="User not found")

        # Remove from favorites
        success = remove_favorite(session, user.id, comic_id)

        logger.debug(f"v2 API: Removed comic {comic_id} from favorites for user {user.id}: {success}")
        return JSONResponse({"success": success})


@router.get("/library/{library_id}/tags")
async def get_tags(library_id: int, request: Request):
    """
    Get all tags/labels for a library

    Returns array of labels in YACReader v2 format
    """
    from ...database import get_labels_in_library, get_library_by_id

    db = request.app.state.db

    with db.get_session() as session:
        # Get library to verify it exists and get UUID
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get all labels in library
        labels = get_labels_in_library(session, library_id)

        # Format labels in v2 format
        labels_list = []
        for label in labels:
            labels_list.append({
                "type": "label",
                "id": str(label.id),
                "library_id": str(library_id),
                "library_uuid": library.uuid,
                "label_name": label.name,
                "color_id": label.color_id
            })

        logger.debug(f"v2 API: Returning {len(labels_list)} labels for library {library_id}")
        return JSONResponse(labels_list)


@router.get("/library/{library_id}/tag/{tag_id}/content")
async def get_tag_content(library_id: int, tag_id: int, request: Request):
    """
    Get all comics with a specific tag/label

    Returns array of comics in YACReader v2 format
    """
    from ...database import (
        get_comics_with_label,
        get_label_by_id,
        get_library_by_id,
        get_user_by_username
    )
    from ..middleware import get_current_user_id

    db = request.app.state.db

    with db.get_session() as session:
        # Get library to verify it exists and get UUID
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Verify label exists
        label = get_label_by_id(session, tag_id)
        if not label or label.library_id != library_id:
            raise HTTPException(status_code=404, detail="Label not found")

        # Get user from session
        user_id = get_current_user_id(request)
        if user_id:
            from ...database import get_user_by_id
            user = get_user_by_id(session, user_id)
        else:
            user = get_user_by_username(session, 'admin')

        if not user:
            raise HTTPException(status_code=500, detail="User not found")

        # Get comics with this label
        comics = get_comics_with_label(session, tag_id)

        # Format comics in v2 format
        comics_list = []
        for comic in comics:
            # Get reading progress
            progress = get_reading_progress(session, user.id, comic.id)
            current_page = progress.current_page if progress else 0
            is_read = progress.is_completed if progress else False

            comics_list.append({
                "type": "comic",
                "id": str(comic.id),
                "comic_info_id": str(comic.id),
                "parent_id": str(comic.folder_id) if comic.folder_id else "0",
                "library_id": str(library_id),
                "library_uuid": library.uuid,
                "file_name": comic.filename,
                "file_size": str(comic.file_size),
                "hash": comic.hash,
                "path": comic.path,
                "current_page": current_page,
                "num_pages": comic.num_pages,
                "read": is_read,
                "manga": comic.reading_direction == "rtl",
                "file_type": 1,
                "number": comic.issue_number or 0,
                "title": get_comic_display_name(comic),
                "added": comic.created_at
            })

        logger.debug(f"v2 API: Returning {len(comics_list)} comics for label {tag_id}")
        return JSONResponse(comics_list)


@router.get("/library/{library_id}/tag/{tag_id}/info")
async def get_tag_info(library_id: int, tag_id: int, request: Request):
    """
    Get information about a specific tag/label

    Returns label object in YACReader v2 format
    """
    from ...database import get_label_by_id, get_library_by_id

    db = request.app.state.db

    with db.get_session() as session:
        # Get library to verify it exists and get UUID
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get label
        label = get_label_by_id(session, tag_id)
        if not label or label.library_id != library_id:
            raise HTTPException(status_code=404, detail="Label not found")

        # Format label in v2 format
        label_info = {
            "type": "label",
            "id": str(label.id),
            "library_id": str(library_id),
            "library_uuid": library.uuid,
            "label_name": label.name,
            "color_id": label.color_id
        }

        logger.debug(f"v2 API: Returning info for label {tag_id}")
        return JSONResponse(label_info)


@router.post("/library/{library_id}/tag")
async def create_tag(library_id: int, request: Request):
    """
    Create a new tag/label

    Request body should contain:
    - name: Label name
    - color_id: Color identifier (optional, default 0)

    Returns created label object
    """
    from ...database import create_label, get_library_by_id

    db = request.app.state.db

    # Parse request body
    body = await request.body()
    body_text = body.decode('utf-8')

    # Parse name and color_id from body
    name = None
    color_id = 0

    for line in body_text.split('\n'):
        line = line.strip()
        if ':' in line:
            key, value = line.split(':', 1)
            if key == 'name':
                name = value.strip()
            elif key == 'color_id':
                try:
                    color_id = int(value.strip())
                except ValueError:
                    pass

    if not name:
        raise HTTPException(status_code=400, detail="Label name is required")

    with db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Create label
        label = create_label(session, library_id, name, color_id)

        # Format response
        label_info = {
            "type": "label",
            "id": str(label.id),
            "library_id": str(library_id),
            "library_uuid": library.uuid,
            "label_name": label.name,
            "color_id": label.color_id
        }

        logger.debug(f"v2 API: Created label {label.id} in library {library_id}")
        return JSONResponse(label_info)


@router.delete("/library/{library_id}/tag/{tag_id}")
async def delete_tag(library_id: int, tag_id: int, request: Request):
    """
    Delete a tag/label

    Returns success status
    """
    from ...database import delete_label, get_label_by_id

    db = request.app.state.db

    with db.get_session() as session:
        # Verify label exists and belongs to this library
        label = get_label_by_id(session, tag_id)
        if not label or label.library_id != library_id:
            raise HTTPException(status_code=404, detail="Label not found")

        # Delete label
        success = delete_label(session, tag_id)

        logger.debug(f"v2 API: Deleted label {tag_id}: {success}")
        return JSONResponse({"success": success})


@router.post("/library/{library_id}/comic/{comic_id}/tag/{tag_id}")
async def add_tag_to_comic(library_id: int, comic_id: int, tag_id: int, request: Request):
    """
    Add a tag/label to a comic

    Returns success status
    """
    from ...database import add_label_to_comic, get_comic_by_id, get_label_by_id

    db = request.app.state.db

    with db.get_session() as session:
        # Verify comic exists
        comic = get_comic_by_id(session, comic_id)
        if not comic or comic.library_id != library_id:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Verify label exists
        label = get_label_by_id(session, tag_id)
        if not label or label.library_id != library_id:
            raise HTTPException(status_code=404, detail="Label not found")

        # Add label to comic
        add_label_to_comic(session, comic_id, tag_id)

        logger.debug(f"v2 API: Added label {tag_id} to comic {comic_id}")
        return JSONResponse({"success": True})


@router.delete("/library/{library_id}/comic/{comic_id}/tag/{tag_id}")
async def remove_tag_from_comic(library_id: int, comic_id: int, tag_id: int, request: Request):
    """
    Remove a tag/label from a comic

    Returns success status
    """
    from ...database import remove_label_from_comic, get_comic_by_id, get_label_by_id

    db = request.app.state.db

    with db.get_session() as session:
        # Verify comic exists
        comic = get_comic_by_id(session, comic_id)
        if not comic or comic.library_id != library_id:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Verify label exists
        label = get_label_by_id(session, tag_id)
        if not label or label.library_id != library_id:
            raise HTTPException(status_code=404, detail="Label not found")

        # Remove label from comic
        success = remove_label_from_comic(session, comic_id, tag_id)

        logger.debug(f"v2 API: Removed label {tag_id} from comic {comic_id}: {success}")
        return JSONResponse({"success": success})


# ============================================================================
# Reading Lists
# ============================================================================

@router.get("/library/{library_id}/reading_lists")
async def get_reading_lists(library_id: int, request: Request):
    """
    Get all reading lists for a library

    Returns array of reading lists in YACReader v2 format
    """
    from ...database import get_reading_lists_in_library, get_library_by_id, get_user_by_username
    from ..middleware import get_current_user_id

    db = request.app.state.db

    with db.get_session() as session:
        # Get library to verify it exists and get UUID
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get user from session
        user_id = get_current_user_id(request)
        if user_id:
            from ...database import get_user_by_id
            user = get_user_by_id(session, user_id)
        else:
            user = get_user_by_username(session, 'admin')

        if not user:
            raise HTTPException(status_code=500, detail="User not found")

        # Get reading lists for this user (includes public lists)
        reading_lists = get_reading_lists_in_library(session, library_id, user.id)

        # Format reading lists in v2 format
        lists = []
        for reading_list in reading_lists:
            lists.append({
                "type": "reading_list",
                "id": str(reading_list.id),
                "library_id": str(library_id),
                "library_uuid": library.uuid,
                "reading_list_name": reading_list.name
            })

        logger.debug(f"v2 API: Returning {len(lists)} reading lists for library {library_id}")
        return JSONResponse(lists)


@router.get("/library/{library_id}/reading_list/{list_id}/content")
async def get_reading_list_content(library_id: int, list_id: int, request: Request):
    """
    Get all comics in a reading list

    Returns array of comics in YACReader v2 format (ordered by position)
    """
    from ...database import (
        get_reading_list_comics,
        get_reading_list_by_id,
        get_library_by_id,
        get_user_by_username
    )
    from ..middleware import get_current_user_id

    db = request.app.state.db

    with db.get_session() as session:
        # Get library to verify it exists and get UUID
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Verify reading list exists
        reading_list = get_reading_list_by_id(session, list_id)
        if not reading_list or reading_list.library_id != library_id:
            raise HTTPException(status_code=404, detail="Reading list not found")

        # Get user from session
        user_id = get_current_user_id(request)
        if user_id:
            from ...database import get_user_by_id
            user = get_user_by_id(session, user_id)
        else:
            user = get_user_by_username(session, 'admin')

        if not user:
            raise HTTPException(status_code=500, detail="User not found")

        # Get comics in this reading list (ordered by position)
        comics = get_reading_list_comics(session, list_id)

        # Format comics in v2 format
        comics_list = []
        for comic in comics:
            # Get reading progress
            progress = get_reading_progress(session, user.id, comic.id)
            current_page = progress.current_page if progress else 0
            is_read = progress.is_completed if progress else False

            comics_list.append({
                "type": "comic",
                "id": str(comic.id),
                "comic_info_id": str(comic.id),
                "parent_id": str(comic.folder_id) if comic.folder_id else "0",
                "library_id": str(library_id),
                "library_uuid": library.uuid,
                "file_name": comic.filename,
                "file_size": str(comic.file_size),
                "hash": comic.hash,
                "path": comic.path,
                "current_page": current_page,
                "num_pages": comic.num_pages,
                "read": is_read,
                "manga": comic.reading_direction == "rtl",
                "file_type": 1,
                "number": comic.issue_number or 0,
                "title": get_comic_display_name(comic),
                "added": comic.created_at
            })

        logger.debug(f"v2 API: Returning {len(comics_list)} comics for reading list {list_id}")
        return JSONResponse(comics_list)


@router.get("/library/{library_id}/reading_list/{list_id}/info")
async def get_reading_list_info(library_id: int, list_id: int, request: Request):
    """
    Get information about a specific reading list

    Returns reading list object in YACReader v2 format
    """
    from ...database import get_reading_list_by_id, get_library_by_id

    db = request.app.state.db

    with db.get_session() as session:
        # Get library to verify it exists and get UUID
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get reading list
        reading_list = get_reading_list_by_id(session, list_id)
        if not reading_list or reading_list.library_id != library_id:
            raise HTTPException(status_code=404, detail="Reading list not found")

        # Format reading list in v2 format
        list_info = {
            "type": "reading_list",
            "id": str(reading_list.id),
            "library_id": str(library_id),
            "library_uuid": library.uuid,
            "reading_list_name": reading_list.name,
            "description": reading_list.description or "",
            "is_public": reading_list.is_public
        }

        logger.debug(f"v2 API: Returning info for reading list {list_id}")
        return JSONResponse(list_info)


@router.post("/library/{library_id}/reading_list")
async def create_reading_list_endpoint(library_id: int, request: Request):
    """
    Create a new reading list

    Request body should contain:
    - name: Reading list name
    - description: Description (optional)
    - is_public: Whether list is public (optional, default false)

    Returns created reading list object
    """
    from ...database import create_reading_list, get_library_by_id, get_user_by_username
    from ..middleware import get_current_user_id

    db = request.app.state.db

    # Parse request body
    body = await request.body()
    body_text = body.decode('utf-8')

    # Parse fields from body
    name = None
    description = None
    is_public = False

    for line in body_text.split('\n'):
        line = line.strip()
        if ':' in line:
            key, value = line.split(':', 1)
            if key == 'name':
                name = value.strip()
            elif key == 'description':
                description = value.strip()
            elif key == 'is_public':
                is_public = value.strip().lower() in ('true', '1', 'yes')

    if not name:
        raise HTTPException(status_code=400, detail="Reading list name is required")

    with db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get user from session
        user_id = get_current_user_id(request)
        if user_id:
            from ...database import get_user_by_id
            user = get_user_by_id(session, user_id)
        else:
            user = get_user_by_username(session, 'admin')

        if not user:
            raise HTTPException(status_code=500, detail="User not found")

        # Create reading list
        reading_list = create_reading_list(
            session,
            library_id,
            name,
            user.id,
            description,
            is_public
        )

        # Format response
        list_info = {
            "type": "reading_list",
            "id": str(reading_list.id),
            "library_id": str(library_id),
            "library_uuid": library.uuid,
            "reading_list_name": reading_list.name,
            "description": reading_list.description or "",
            "is_public": reading_list.is_public
        }

        logger.debug(f"v2 API: Created reading list {reading_list.id} in library {library_id}")
        return JSONResponse(list_info)


@router.delete("/library/{library_id}/reading_list/{list_id}")
async def delete_reading_list_endpoint(library_id: int, list_id: int, request: Request):
    """
    Delete a reading list

    Returns success status
    """
    from ...database import delete_reading_list, get_reading_list_by_id

    db = request.app.state.db

    with db.get_session() as session:
        # Verify reading list exists and belongs to this library
        reading_list = get_reading_list_by_id(session, list_id)
        if not reading_list or reading_list.library_id != library_id:
            raise HTTPException(status_code=404, detail="Reading list not found")

        # Delete reading list
        success = delete_reading_list(session, list_id)

        logger.debug(f"v2 API: Deleted reading list {list_id}: {success}")
        return JSONResponse({"success": success})


@router.post("/library/{library_id}/reading_list/{list_id}/comic/{comic_id}")
async def add_comic_to_reading_list_endpoint(
    library_id: int,
    list_id: int,
    comic_id: int,
    request: Request
):
    """
    Add a comic to a reading list

    Returns success status
    """
    from ...database import add_comic_to_reading_list, get_comic_by_id, get_reading_list_by_id

    db = request.app.state.db

    with db.get_session() as session:
        # Verify comic exists
        comic = get_comic_by_id(session, comic_id)
        if not comic or comic.library_id != library_id:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Verify reading list exists
        reading_list = get_reading_list_by_id(session, list_id)
        if not reading_list or reading_list.library_id != library_id:
            raise HTTPException(status_code=404, detail="Reading list not found")

        # Add comic to reading list
        add_comic_to_reading_list(session, list_id, comic_id)

        logger.debug(f"v2 API: Added comic {comic_id} to reading list {list_id}")
        return JSONResponse({"success": True})


@router.delete("/library/{library_id}/reading_list/{list_id}/comic/{comic_id}")
async def remove_comic_from_reading_list_endpoint(
    library_id: int,
    list_id: int,
    comic_id: int,
    request: Request
):
    """
    Remove a comic from a reading list

    Returns success status
    """
    from ...database import remove_comic_from_reading_list, get_comic_by_id, get_reading_list_by_id

    db = request.app.state.db

    with db.get_session() as session:
        # Verify comic exists
        comic = get_comic_by_id(session, comic_id)
        if not comic or comic.library_id != library_id:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Verify reading list exists
        reading_list = get_reading_list_by_id(session, list_id)
        if not reading_list or reading_list.library_id != library_id:
            raise HTTPException(status_code=404, detail="Reading list not found")

        # Remove comic from reading list
        success = remove_comic_from_reading_list(session, list_id, comic_id)

        logger.debug(f"v2 API: Removed comic {comic_id} from reading list {list_id}: {success}")
        return JSONResponse({"success": success})


# ============================================================================
# Folder Tree (NEW)
# ============================================================================

@router.get("/library/{library_id}/tree")
async def get_folder_tree(
    library_id: int,
    request: Request,
    max_depth: int = 10
):
    """
    Get hierarchical folder tree for a library

    Returns nested folder structure with comic counts

    Format:
    {
        "id": library_id,
        "name": "Library Name",
        "type": "library",
        "children": [
            {
                "id": folder_id,
                "name": "Folder Name",
                "type": "folder",
                "parent_id": parent_folder_id,
                "comic_count": 10,
                "children": [...]
            }
        ]
    }
    """
    from ...database.models import Folder as FolderModel

    db = request.app.state.db

    with db.get_session() as session:
        # Get library
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get all folders in library
        all_folders = get_folders_in_library(session, library_id)

        # Build folder lookup dict
        folder_dict = {folder.id: folder for folder in all_folders}

        # Build tree structure recursively
        def build_tree_node(folder, depth=0):
            if depth > max_depth:
                return None

            # Skip root folder
            if folder.name == "__ROOT__":
                return None

            # Count comics in this folder
            comic_count = session.query(Comic).filter_by(
                library_id=library_id,
                folder_id=folder.id
            ).count()

            node = {
                "id": folder.id,
                "name": folder.name,
                "type": "folder",
                "parent_id": folder.parent_id,
                "comic_count": comic_count,
                "children": []
            }

            # Find and add children
            child_folders = [f for f in all_folders if f.parent_id == folder.id]
            for child in sorted(child_folders, key=lambda x: x.name):
                child_node = build_tree_node(child, depth + 1)
                if child_node:
                    node["children"].append(child_node)

            return node

        # Find root folders (parent_id is None or points to __ROOT__)
        root_folder = next((f for f in all_folders if f.name == "__ROOT__"), None)
        root_folder_id = root_folder.id if root_folder else None

        top_level_folders = [
            f for f in all_folders
            if f.parent_id == root_folder_id or
            (f.parent_id is None and f.name != "__ROOT__")
        ]

        # Count total comics in library
        total_comics = session.query(Comic).filter_by(library_id=library_id).count()

        # Build library root node
        tree = {
            "id": library.id,
            "name": library.name,
            "type": "library",
            "comic_count": total_comics,
            "children": []
        }

        # Add top-level folders
        for folder in sorted(top_level_folders, key=lambda x: x.name):
            node = build_tree_node(folder)
            if node:
                tree["children"].append(node)

        logger.debug(f"v2 API: Returning folder tree for library {library_id} with {len(tree['children'])} top-level folders")
        return JSONResponse(tree)


@router.get("/libraries/series-tree")
async def get_libraries_series_tree(request: Request, max_depth: int = 10):
    """
    Get hierarchical tree of all libraries with their folder structure and comics

    Returns a tree structure based on actual folder hierarchy:
    [
        {
            "id": library_id,
            "name": "Library Name",
            "type": "library",
            "children": [
                {
                    "id": folder_id,
                    "name": "Folder Name",
                    "type": "folder",
                    "libraryId": library_id,
                    "comicCount": 10,
                    "children": [...]
                }
            ]
        }
    ]

    NOTE: Now uses pre-built cache from library scanning for better performance.
    Reading progress is added dynamically per-user.
    """
    from ...database.models import Folder as FolderModel

    db = request.app.state.db

    with db.get_session() as session:
        # Get all libraries
        libraries = get_all_libraries(session)

        # Get user for reading progress
        user_id = get_current_user_id(request)
        if user_id:
            user = get_user_by_id(session, user_id)
        else:
            user = get_user_by_username(session, 'admin')

        # OPTIMIZATION: Fetch ALL reading progress for this user in ONE query
        # This eliminates N+1 queries when adding progress to tree nodes
        progress_by_comic = {}
        if user:
            all_progress = session.query(ReadingProgress).filter_by(user_id=user.id).all()
            progress_by_comic = {p.comic_id: p for p in all_progress}

        def add_reading_progress_to_tree(node, progress_lookup):
            """Recursively add reading progress to cached tree nodes (OPTIMIZED)"""
            if not progress_lookup or not node:
                return node

            # Add progress to comics (lookup from pre-fetched dict, NO database query)
            if node.get("type") == "comic":
                comic_id = node.get("id")
                if comic_id and comic_id in progress_lookup:
                    progress = progress_lookup[comic_id]
                    node["currentPage"] = progress.current_page
                    node["isCompleted"] = progress.is_completed
                    node["progressPercent"] = progress.progress_percent

            # Recursively process children
            if "children" in node:
                for child in node["children"]:
                    add_reading_progress_to_tree(child, progress_lookup)

            return node

        tree = []

        for library in libraries:
            # Try in-memory cache first (fastest)
            cache_key = f"{library.id}:{library.tree_cache_updated_at}"
            if cache_key in _series_tree_cache:
                library_node = _series_tree_cache[cache_key].copy()

                # Add reading progress dynamically (user-specific, no N+1!)
                if user:
                    add_reading_progress_to_tree(library_node, progress_by_comic)

                tree.append(library_node)
                logger.debug(f"v2 API: Using in-memory cache for library {library.id}")
                continue

            # Try database cached tree
            if library.cached_series_tree:
                try:
                    import json
                    cached_children = json.loads(library.cached_series_tree)

                    # Build library node with cached children
                    library_node = {
                        "id": library.id,
                        "name": library.name,
                        "type": "library",
                        "children": cached_children
                    }

                    # Store in memory cache for next time
                    _series_tree_cache[cache_key] = library_node.copy()

                    # Add reading progress dynamically (no N+1!)
                    if user:
                        add_reading_progress_to_tree(library_node, progress_by_comic)

                    tree.append(library_node)
                    logger.debug(f"v2 API: Using database cache for library {library.id}")
                    continue

                except Exception as e:
                    logger.warning(f"Failed to use cached tree for library {library.id}: {e}")
                    # Fall through to rebuild from database

            # Fallback: Build tree from database if cache doesn't exist
            logger.warning(f"No cache available for library {library.id}, building from database")

            # Get all folders in this library
            all_folders = session.query(FolderModel).filter_by(library_id=library.id).all()

            # Find root folder
            root_folder = next((f for f in all_folders if f.name == "__ROOT__"), None)

            library_node = {
                "id": library.id,
                "name": library.name,
                "type": "library",
                "children": []
            }

            # Simplified fallback - just add empty children
            # Recommend running library scan to build cache
            logger.warning(f"Library {library.id} needs to be rescanned to build cache")

            tree.append(library_node)

        logger.debug(f"v2 API: Returning series tree for {len(tree)} libraries")
        return JSONResponse(tree)


# ============================================================================
# Series Grouping
# ============================================================================

@router.get("/library/{library_id}/series")
async def get_series_list(
    library_id: int,
    request: Request,
    sort: Optional[str] = "name",
    include_metadata: Optional[bool] = True
):
    """
    Get all series in a library with metadata aggregation (OPTIMIZED)

    Uses SQL aggregation and eager loading to avoid N+1 queries.
    Series names are pre-computed in normalized_series_name field.

    Args:
        library_id: ID of the library
        sort: Sort order - 'name', 'recent', 'progress'
        include_metadata: Include series metadata (writer, artist, etc.) - default True

    Returns:
        Array of series objects with aggregated metadata
    """
    db = request.app.state.db

    with db.get_session() as session:
        from sqlalchemy.orm import selectinload
        from sqlalchemy import func

        # Get library
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get user for reading progress
        user_id = get_current_user_id(request)
        if user_id:
            user = get_user_by_id(session, user_id)
        else:
            user = get_user_by_username(session, 'admin')

        # OPTIMIZATION 1: Use SQL to group and aggregate series data
        # This replaces the Python loops with database aggregation
        from sqlalchemy import outerjoin
        from ...database.models import Series as SeriesModel

        # Build base query
        if include_metadata:
            # Join with Series table to get metadata
            series_aggregation = session.query(
                Comic.normalized_series_name.label('series_name'),
                func.count(Comic.id).label('total_issues'),
                func.min(Comic.id).label('first_comic_id'),
                func.max(Comic.id).label('last_comic_id'),
                func.min(Comic.hash).label('cover_hash'),
                func.max(Comic.publisher).label('publisher'),
                SeriesModel.writer.label('writer'),
                SeriesModel.artist.label('artist'),
                SeriesModel.genre.label('genre'),
                SeriesModel.year_start.label('year'),
                SeriesModel.description.label('synopsis')
            ).outerjoin(
                SeriesModel,
                (SeriesModel.library_id == Comic.library_id) &
                (SeriesModel.name == Comic.normalized_series_name)
            ).filter(
                Comic.library_id == library_id
            ).group_by(
                Comic.normalized_series_name,
                SeriesModel.writer,
                SeriesModel.artist,
                SeriesModel.genre,
                SeriesModel.year_start,
                SeriesModel.description
            ).all()
        else:
            # Minimal query without metadata join
            series_aggregation = session.query(
                Comic.normalized_series_name.label('series_name'),
                func.count(Comic.id).label('total_issues'),
                func.min(Comic.id).label('first_comic_id'),
                func.max(Comic.id).label('last_comic_id'),
                func.min(Comic.hash).label('cover_hash'),
                func.max(Comic.publisher).label('publisher')
            ).filter(
                Comic.library_id == library_id
            ).group_by(
                Comic.normalized_series_name
            ).all()

        # OPTIMIZATION 2: Fetch all comics with reading progress in ONE query (fixes N+1)
        if user:
            # Eager load reading progress for ALL comics at once
            comics_query = session.query(Comic).options(
                selectinload(Comic.reading_progress)
            ).filter(
                Comic.library_id == library_id
            ).all()

            # Build a lookup dict: series_name -> list of comics
            comics_by_series = {}
            for comic in comics_query:
                series_name = comic.normalized_series_name or "Unknown"
                if series_name not in comics_by_series:
                    comics_by_series[series_name] = []
                comics_by_series[series_name].append(comic)
        else:
            # No user, just fetch comics without progress
            comics_query = session.query(Comic).filter(
                Comic.library_id == library_id
            ).all()
            comics_by_series = {}
            for comic in comics_query:
                series_name = comic.normalized_series_name or "Unknown"
                if series_name not in comics_by_series:
                    comics_by_series[series_name] = []
                comics_by_series[series_name].append(comic)

        # Build series list from aggregated data
        series_list = []
        for series_data in series_aggregation:
            series_name = series_data.series_name or "Unknown"
            comics_in_series = comics_by_series.get(series_name, [])

            # Build volumes list
            volumes = []
            for comic in comics_in_series:
                volume_info = {
                    "id": comic.id,
                    "title": get_comic_display_name(comic),
                    "volume": comic.volume,
                    "issue_number": comic.issue_number,
                    "filename": comic.filename,
                    "hash": comic.hash,
                    "num_pages": comic.num_pages
                }

                # Add reading progress (already eager-loaded, no extra query!)
                if user:
                    # Find progress for this user (from the eager-loaded relationship)
                    progress = next(
                        (p for p in comic.reading_progress if p.user_id == user.id),
                        None
                    )
                    if progress:
                        volume_info["current_page"] = progress.current_page
                        volume_info["is_completed"] = progress.is_completed
                        volume_info["progress_percent"] = progress.progress_percent

                volumes.append(volume_info)

            # Determine if this is a standalone volume (single comic, not part of a series)
            is_standalone = series_data.total_issues == 1

            series_info = {
                "series_name": series_name,
                "volumes": volumes,
                "publisher": series_data.publisher,
                "total_issues": series_data.total_issues,
                "cover_hash": series_data.cover_hash,
                "first_comic_id": series_data.first_comic_id,
                "is_standalone": is_standalone  # Flag for single-volume series
            }

            # Add metadata fields if included
            if include_metadata:
                series_info["year"] = series_data.year
                series_info["writer"] = series_data.writer
                series_info["artist"] = series_data.artist
                series_info["genre"] = series_data.genre
                series_info["synopsis"] = series_data.synopsis
            else:
                series_info["year"] = None

            series_list.append(series_info)

        # Sort the results
        if sort == "name":
            series_list.sort(key=lambda s: s["series_name"].lower())
        elif sort == "recent":
            # Sort by most recent addition (first comic id descending)
            series_list.sort(key=lambda s: s["first_comic_id"], reverse=True)
        elif sort == "progress":
            # Sort by reading progress (series with unread volumes first)
            def get_progress_key(s):
                completed = sum(1 for v in s["volumes"] if v.get("is_completed", False))
                return (completed / s["total_issues"]) if s["total_issues"] > 0 else 0
            series_list.sort(key=get_progress_key)

        logger.debug(f"v2 API: Returning {len(series_list)} series for library {library_id} (OPTIMIZED)")
        return JSONResponse(series_list)


@router.get("/library/{library_id}/series/{series_name}")
async def get_series_detail(
    library_id: int,
    series_name: str,
    request: Request
):
    """
    Get detailed information about a specific series

    Returns all volumes in the series with full metadata and reading progress

    Args:
        library_id: ID of the library
        series_name: Name of the series (URL encoded)

    Returns:
        Series object with volumes array and aggregated metadata
    """
    from urllib.parse import unquote
    from ...database.models import Series as SeriesModel

    db = request.app.state.db

    with db.get_session() as session:
        # Get library
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Decode series name from URL
        decoded_series_name = unquote(series_name)

        # Try to find the Series record first
        series_record = session.query(SeriesModel).filter(
            SeriesModel.library_id == library_id,
            SeriesModel.name == decoded_series_name
        ).first()

        # Try to find comics by normalized_series_name first (pre-computed during scan)
        comics = session.query(Comic).filter(
            Comic.library_id == library_id,
            Comic.normalized_series_name == decoded_series_name
        ).all()

        # Fallback: Try to find by series field if normalized_series_name is not set
        if not comics:
            comics = session.query(Comic).filter(
                Comic.library_id == library_id,
                Comic.series == decoded_series_name
            ).all()

        # Fallback 2: Try to find by folder name
        if not comics:
            from ...database.models import Folder as FolderModel
            folder = session.query(FolderModel).filter(
                FolderModel.library_id == library_id,
                FolderModel.name == decoded_series_name
            ).first()
            
            if folder:
                comics = session.query(Comic).filter(
                    Comic.library_id == library_id,
                    Comic.folder_id == folder.id
                ).all()

        if not comics:
            raise HTTPException(status_code=404, detail=f"Series not found: {decoded_series_name}")

        # Get user for reading progress
        user_id = get_current_user_id(request)
        if user_id:
            user = get_user_by_id(session, user_id)
        else:
            user = get_user_by_username(session, 'admin')

        # Build volumes list with full details
        volumes = []
        for comic in comics:
            # Get reading progress
            current_page = 0
            is_completed = False
            progress_percent = 0
            last_read_at = None

            if user:
                progress = get_reading_progress(session, user.id, comic.id)
                if progress:
                    current_page = progress.current_page
                    is_completed = progress.is_completed
                    progress_percent = progress.progress_percent
                    last_read_at = progress.last_read_at

            # Build relative path
            try:
                relative_path = str(Path(comic.path).relative_to(library.path))
            except ValueError:
                relative_path = comic.filename

            api_path = f"/{relative_path}"

            volume = {
                "type": "comic",
                "id": str(comic.id),
                "title": get_comic_display_name(comic),
                "series": comic.series,
                "volume": comic.volume,
                "issue_number": comic.issue_number,
                "filename": comic.filename,
                "file_size": comic.file_size,
                "hash": comic.hash,
                "path": api_path,
                "num_pages": comic.num_pages,
                "current_page": current_page,
                "is_completed": is_completed,
                "progress_percent": progress_percent,
                "last_read_at": last_read_at,
                "library_id": str(library_id),
                "library_uuid": library.uuid,
                "created_at": comic.created_at
            }

            # Add optional metadata fields
            if hasattr(comic, 'synopsis') and comic.synopsis:
                volume["synopsis"] = comic.synopsis
            if hasattr(comic, 'writer') and comic.writer:
                volume["writer"] = comic.writer
            if hasattr(comic, 'publisher') and comic.publisher:
                volume["publisher"] = comic.publisher
            if hasattr(comic, 'genre') and comic.genre:
                volume["genre"] = comic.genre
            if hasattr(comic, 'year') and comic.year:
                volume["year"] = comic.year

            volumes.append(volume)

        # Sort volumes by volume number first (volumes before chapters), then by issue number
        # Volumes have a volume number (>0), chapters have issue_number but volume=0/null
        # We want volumes to appear before chapters
        # When metadata is missing, detect from filename patterns
        def sort_key(v):
            vol = v.get("volume") or 0
            issue = v.get("issue_number") or 0
            title = v.get("title", "").lower()

            # If metadata exists, use it
            if vol > 0:
                # Has volume metadata - it's a volume
                return (0, vol, issue)
            elif issue > 0:
                # Has issue metadata but no volume - likely a chapter
                # But check title for volume patterns first (in case metadata is incomplete)
                if re.search(r'\bv(?:ol)?\.?\s*\d+', title) or re.search(r'\bvolume\s+\d+', title):
                    # Title suggests it's a volume, extract number
                    match = re.search(r'\bv(?:ol)?\.?\s*(\d+)', title) or re.search(r'\bvolume\s+(\d+)', title)
                    if match:
                        vol_num = int(match.group(1))
                        return (0, vol_num, 0)
                # It's a chapter
                return (1, issue, 0)
            else:
                # No metadata - rely on filename patterns
                # Check for volume patterns: v01, vol01, volume 1, etc.
                if re.search(r'\bv(?:ol)?\.?\s*\d+', title) or re.search(r'\bvolume\s+\d+', title):
                    match = re.search(r'\bv(?:ol)?\.?\s*(\d+)', title) or re.search(r'\bvolume\s+(\d+)', title)
                    if match:
                        vol_num = int(match.group(1))
                        return (0, vol_num, 0)
                # Check for chapter patterns: c001, ch01, chapter 1, etc.
                elif re.search(r'\bc(?:h|hapter)?\.?\s*\d+', title) or re.search(r'\bchapter\s+\d+', title):
                    match = re.search(r'\bc(?:h|hapter)?\.?\s*(\d+)', title) or re.search(r'\bchapter\s+(\d+)', title)
                    if match:
                        ch_num = int(match.group(1))
                        return (1, ch_num, 0)
                # Fallback: sort by title
                return (2, 0, 0)

        volumes.sort(key=sort_key)

        # Aggregate series metadata from first comic
        first_comic = comics[0]
        series_detail = {
            "series_name": decoded_series_name,
            "total_issues": len(volumes),
            "cover_hash": first_comic.hash,
            "volumes": volumes
        }

        # Prefer Series table metadata over comic metadata (series scanners take priority)
        if series_record:
            # Use series-level metadata if available
            if series_record.display_name:
                series_detail["display_name"] = series_record.display_name
            if series_record.description:
                series_detail["synopsis"] = series_record.description
            if series_record.writer:
                series_detail["writer"] = series_record.writer
            if series_record.artist:
                series_detail["artist"] = series_record.artist
            if series_record.genre:
                series_detail["genre"] = series_record.genre
            if series_record.publisher:
                series_detail["publisher"] = series_record.publisher
            if series_record.year_start:
                series_detail["year"] = series_record.year_start
            if series_record.status:
                series_detail["status"] = series_record.status
            if series_record.format:
                series_detail["format"] = series_record.format
            if series_record.tags:
                series_detail["tags"] = series_record.tags
            if series_record.scanner_source_url:
                series_detail["scanner_source_url"] = series_record.scanner_source_url
            if series_record.scanner_source:
                series_detail["scanner_source"] = series_record.scanner_source
            if series_record.scan_confidence is not None:
                series_detail["scan_confidence"] = series_record.scan_confidence
        else:
            # Fallback to comic-level metadata (aggregated from first comic)
            if hasattr(first_comic, 'publisher') and first_comic.publisher:
                series_detail["publisher"] = first_comic.publisher
            if hasattr(first_comic, 'year') and first_comic.year:
                series_detail["year"] = first_comic.year
            if hasattr(first_comic, 'genre') and first_comic.genre:
                series_detail["genre"] = first_comic.genre
            if hasattr(first_comic, 'synopsis') and first_comic.synopsis:
                series_detail["synopsis"] = first_comic.synopsis

        # Calculate overall reading progress
        completed_volumes = sum(1 for v in volumes if v["is_completed"])
        series_detail["completed_volumes"] = completed_volumes
        series_detail["overall_progress"] = (completed_volumes / len(volumes) * 100) if volumes else 0

        logger.debug(f"v2 API: Returning series detail for '{decoded_series_name}' with {len(volumes)} volumes")
        return JSONResponse(series_detail)


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
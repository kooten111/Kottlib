"""
API v2 Router - Folders

Endpoints for folder navigation and browsing.
"""

import re
import logging
from typing import Optional
from pathlib import Path
from collections import namedtuple

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text

from ....database import (
    get_library_by_id,
    get_user_by_username,
    get_user_by_id,
    get_reading_progress,
)
from ....database.models import Comic, Folder
from ...middleware import get_current_user_id, get_request_user

logger = logging.getLogger(__name__)

router = APIRouter()


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
    # Use main database for everything
    db = request.app.state.db

    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")
        library_name = library.name
        library_path = library.path
        library_uuid = library.uuid

        logger.info(f"v2 API: Getting folder {folder_id} in library {library_id}")

        # Get folders using ORM
        folder_result = session.query(Folder).filter(Folder.library_id == library_id).all()

        # Convert to list for processing
        folders = folder_result

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
            # We can use ORM now
            first_comic = session.query(Comic).filter(
                Comic.folder_id == folder.id,
                Comic.library_id == library_id
            ).order_by(Comic.filename).first()

            first_comic_hash = first_comic.hash if first_comic else ""

            # If no comics, check subfolders recursively (simplified for performance)
            if not first_comic_hash and folder.first_child_hash:
                 first_comic_hash = folder.first_child_hash

            # Count children
            num_child_folders = session.query(Folder).filter(Folder.parent_id == folder.id).count()
            num_child_comics = session.query(Comic).filter(
                Comic.folder_id == folder.id,
                Comic.library_id == library_id
            ).count()
            num_children = num_child_folders + num_child_comics

            try:
                relative_path = str(Path(folder.path).relative_to(library_path))
            except ValueError:
                relative_path = folder.name # Fallback

            api_path = f"/{relative_path}"

            child_folders.append({
                "type": "folder",
                "id": str(folder.id),
                "library_id": str(library_id),
                "library_uuid": library_uuid,
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

        if is_root_request:
            # Root folder request - get comics in the __ROOT__ folder for this library
            root_folder = next((f for f in folders if f.name == "__ROOT__"), None)
            if root_folder:
                comics_result = session.query(Comic).filter(
                    (Comic.folder_id == root_folder.id) | (Comic.folder_id == None),
                    Comic.library_id == library_id
                ).all()
            else:
                comics_result = session.query(Comic).filter(
                    Comic.folder_id == None,
                    Comic.library_id == library_id
                ).all()
        else:
            # Specific folder - get its comics
            comics_result = session.query(Comic).filter(
                Comic.folder_id == folder_id,
                Comic.library_id == library_id
            ).all()

        comics = comics_result

        # Get user for reading progress (already have session)
        user = get_request_user(request, session)
        # Get the user ID for use in reading progress queries
        user_id_for_progress = user.id if user else None

        comics_list = []
        for comic in comics:
            # Get reading progress for this comic (from library-specific DB)
            current_page = 0
            is_read = False
            has_been_opened = False
            last_read_at = 0
            if user_id_for_progress:
                progress = get_reading_progress(session, user_id_for_progress, comic.id)
                if progress:
                    current_page = progress.current_page
                    is_read = progress.is_completed
                    has_been_opened = current_page > 0
                    last_read_at = progress.last_read_at
            try:
                relative_path = str(Path(comic.path).relative_to(library_path))
            except ValueError:
                relative_path = comic.filename

            api_path = f"/{relative_path}"
            comics_list.append({
                "type": "comic",
                "id": str(comic.id),
                "comic_info_id": str(comic.id),  # Using comic id as comic_info_id
                "parent_id": str(comic.folder_id) if comic.folder_id is not None else "0",
                "library_id": str(library_id),
                "library_uuid": library_uuid,
                "file_name": comic.filename,
                "file_size": str(comic.file_size),
                "hash": comic.hash,
                "path": api_path,
                "current_page": current_page,
                "num_pages": comic.num_pages,
                "read": is_read,
                "manga": (comic.reading_direction == 'rtl') if comic.reading_direction else False,
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


@router.get("/library/{library_id}/folder/{folder_id}/info")
async def get_folder_info_v2(
    library_id: int,
    folder_id: int,
    request: Request
):
    """
    Get folder information in custom text format (v2 API)

    Returns recursive listing of comics in custom delimited format:
    /v2/library/{libId}/comic/{comicId}:{fileName}:{fileSize}:{readStatus}:{hash}

    This is the v2 version which includes read status and hash.
    """
    # Get main database for library metadata
    db = request.app.state.db

    # First, get library info from main database
    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")
        library_name = library.name

        # Get user for reading progress
        user = get_request_user(request, session)
        user_id_for_progress = user.id if user else None

        # Get all folders
        folder_result = session.execute(text(
            "SELECT id, parent_id, name FROM folders WHERE library_id = :library_id"
        ), {"library_id": library_id}).fetchall()

        FolderData = namedtuple('FolderData', ['id', 'parent_id', 'name'])
        folders = [FolderData(*row) for row in folder_result]

        # Determine if this is a root request
        is_root_request = (folder_id <= 1)

        # Build response with recursive folder traversal
        lines = []

        def add_folder_comics(fid: int, recursive: bool = True):
            """Recursively add comics from folder and subfolders"""
            # Get comics in this folder
            comics_result = session.execute(text(
                """SELECT id, filename, file_size, hash
                   FROM comics WHERE folder_id = :folder_id"""
            ), {"folder_id": fid}).fetchall()

            for comic_row in comics_result:
                comic_id, filename, file_size, comic_hash = comic_row

                # Get reading status
                read_status = 0
                if user_id_for_progress:
                    progress = get_reading_progress(session, user_id_for_progress, comic_id)
                    if progress and progress.is_completed:
                        read_status = 1

                line = f"/v2/library/{library_id}/comic/{comic_id}:{filename}:{file_size}:{read_status}:{comic_hash}"
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
                # Fallback: get all comics
                all_comics = session.execute(text(
                    "SELECT id, filename, file_size, hash FROM comics WHERE library_id = :library_id"
                ), {"library_id": library_id}).fetchall()
                for comic_row in all_comics:
                    comic_id, filename, file_size, comic_hash = comic_row
                    read_status = 0
                    if user_id_for_progress:
                        progress = get_reading_progress(session, user_id_for_progress, comic_id)
                        if progress and progress.is_completed:
                            read_status = 1
                    line = f"/v2/library/{library_id}/comic/{comic_id}:{filename}:{file_size}:{read_status}:{comic_hash}"
                    lines.append(line)
        else:
            # Specific folder - get comics recursively from this folder
            add_folder_comics(folder_id, recursive=True)

        response_text = "\r\n".join(lines)
        return PlainTextResponse(response_text, media_type="text/plain; charset=utf-8")


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


@router.get("/library/{library_id}/folders")
async def get_library_folders(
    library_id: int,
    request: Request,
    folder_id: Optional[int] = None
):
    """
    Get folders in a library as a flat list (for card/grid display)

    If folder_id is provided, returns children of that folder.
    If folder_id is None, returns top-level folders.

    This is similar to /tree but returns a flat list instead of nested structure,
    making it easier to display as cards in the UI.

    Returns:
        Array of folder objects with comic counts and cover images
    """
    # Get main DB
    db = request.app.state.db

    with db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get all folders for this library
        all_folders = session.query(Folder).filter(
            Folder.library_id == library_id
        ).all()

        # Find root folder
        root_folder = next((f for f in all_folders if f.name == "__ROOT__"), None)
        root_folder_id = root_folder.id if root_folder else None

        # Get target folders
        if folder_id is None:
            # Get top-level folders (children of root)
            target_folders = [
                f for f in all_folders
                if f.parent_id == root_folder_id or
                (f.parent_id is None and f.name != "__ROOT__")
            ]
        else:
            # Get children of specified folder
            target_folders = [f for f in all_folders if f.parent_id == folder_id]

        # Build folder list with metadata
        folders_list = []

        # OPTIMIZATION: Pre-fetch all comics to avoid N+1 queries
        # We only need id, folder_id, and hash
        all_comics = session.execute(
            text("SELECT id, folder_id, hash, filename, title, volume, issue_number FROM comics WHERE library_id = :library_id"),
            {"library_id": library_id}
        ).fetchall()

        # Build maps for O(1) access
        comics_by_folder = {}
        for comic in all_comics:
            fid = comic.folder_id
            if fid not in comics_by_folder:
                comics_by_folder[fid] = []
            comics_by_folder[fid].append(comic)

        # Build folder tree map (parent_id -> list of children)
        folders_by_parent = {}
        for f in all_folders:
            pid = f.parent_id
            if pid not in folders_by_parent:
                folders_by_parent[pid] = []
            folders_by_parent[pid].append(f)

        # Helper to recursively calculate stats
        # Returns (total_count, cover_hash)
        def get_folder_stats(folder_id):
            # Direct comics
            direct_comics = comics_by_folder.get(folder_id, [])
            count = len(direct_comics)

            # Find cover from direct comics
            cover = None
            if direct_comics:
                # Sort to find best cover (same logic as scanner)
                # Sort by volume, issue, then filename
                sorted_comics = sorted(direct_comics, key=lambda c: c.filename or "")
                cover = sorted_comics[0].hash

            # Recursively check children
            children = folders_by_parent.get(folder_id, [])
            for child in children:
                child_count, child_cover = get_folder_stats(child.id)
                count += child_count

                # If we don't have a cover yet, use child's cover
                if not cover and child_cover:
                    cover = child_cover

            return count, cover

        for folder in sorted(target_folders, key=lambda x: x.name):
            # Calculate recursive stats
            comic_count, cover_hash = get_folder_stats(folder.id)

            # Check if folder has subfolders (direct children)
            has_children = folder.id in folders_by_parent and len(folders_by_parent[folder.id]) > 0

            # Determine if this is a series (has comics but no subfolders)
            is_series = comic_count > 0

            folder_data = {
                "id": folder.id,
                "name": folder.name,
                "title": folder.name,
                "series": folder.name,
                "series_name": folder.name,
                "type": "folder",
                "parent_id": folder.parent_id,
                "comic_count": comic_count,
                "has_children": has_children,
                "is_series": is_series
            }

            if cover_hash:
                folder_data["cover_hash"] = cover_hash

            folders_list.append(folder_data)

        # Add loose files (comics without folder_id or folder_id = 0)
        if folder_id is None:
            # Get loose comics (no folder or in root folder)
            loose_comics = session.execute(
                text("""
                    SELECT id, filename, hash, series, title
                    FROM comics
                    WHERE library_id = :library_id AND (folder_id IS NULL OR folder_id = 0 OR folder_id = :root_id)
                    ORDER BY filename
                """),
                {"library_id": library_id, "root_id": root_folder_id if root_folder_id else 0}
            ).fetchall()

            # Add each loose comic as a standalone item
            for comic_row in loose_comics:
                comic_id, filename, hash_val, series, title = comic_row
                # Use series name if available, otherwise use filename without extension
                display_name = series or title or filename.rsplit('.', 1)[0]

                folders_list.append({
                    "id": comic_id,
                    "name": display_name,
                    "type": "comic",
                    "parent_id": root_folder_id,
                    "comic_count": 1,
                    "has_children": False,
                    "cover_hash": hash_val,
                    "first_comic_id": comic_id,
                    "filename": filename
                })

        return JSONResponse(folders_list)

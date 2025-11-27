"""
API v2 Router - Series

Endpoints for series management and browsing:
- GET /tree - Get hierarchical folder tree for a library
- GET /series-tree - Get hierarchical tree of all libraries with folder structure
- GET /series - Get all series in a library
- GET /series/{name} - Get detailed information about a specific series
"""

import logging
import re
import json
from typing import Optional
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func

from ....database import (
    get_library_by_id,
    get_all_libraries,
    get_folders_in_library,
    get_comic_by_id,
    get_user_by_username,
    get_user_by_id,
    get_reading_progress,
)
from ....database.models import Comic, ReadingProgress
from ...middleware import get_current_user_id, get_request_user
from ._shared import get_comic_display_name, series_tree_cache, get_comic_sort_key

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Folder Tree Navigation
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
    from ....database.models import Folder as FolderModel

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
    from ....database.models import Folder as FolderModel

    db = request.app.state.db

    with db.get_session() as session:
        # Get all libraries
        libraries = get_all_libraries(session)

        # Get user for reading progress
        user = get_request_user(request, session)

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
            if cache_key in series_tree_cache:
                library_node = series_tree_cache[cache_key].copy()

                # Add reading progress dynamically (user-specific, no N+1!)
                if user:
                    add_reading_progress_to_tree(library_node, progress_by_comic)

                tree.append(library_node)
                logger.debug(f"v2 API: Using in-memory cache for library {library.id}")
                continue

            # Try database cached tree
            if library.cached_series_tree:
                try:
                    cached_children = json.loads(library.cached_series_tree)

                    # Build library node with cached children
                    library_node = {
                        "id": library.id,
                        "name": library.name,
                        "type": "library",
                        "children": cached_children
                    }

                    # Store in memory cache for next time
                    series_tree_cache[cache_key] = library_node.copy()

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
# Series Browsing
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
    # Get main database for library and user info
    # Get main database
    main_db = request.app.state.db

    with main_db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get user for reading progress
        user = get_request_user(request, session)
        user_id_for_progress = user.id if user else None

        from sqlalchemy.orm import selectinload
        from ....database.models import Series as SeriesModel

        # OPTIMIZATION 1: Use SQL to group and aggregate series data
        if include_metadata:
            # Join with Series table to get metadata
            series_aggregation = session.query(
                Comic.series.label('series_name'),
                SeriesModel.id.label('series_id'),
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
            ).filter(
                Comic.library_id == library_id
            ).outerjoin(
                SeriesModel,
                (SeriesModel.name == Comic.series) & (SeriesModel.library_id == library_id)
            ).group_by(
                Comic.series,
                SeriesModel.id,
                SeriesModel.writer,
                SeriesModel.artist,
                SeriesModel.genre,
                SeriesModel.year_start,
                SeriesModel.description
            ).all()
        else:
            # Minimal query without metadata join
            from sqlalchemy import literal
            series_aggregation = session.query(
                Comic.series.label('series_name'),
                literal(None).label('series_id'),
                func.count(Comic.id).label('total_issues'),
                func.min(Comic.id).label('first_comic_id'),
                func.max(Comic.id).label('last_comic_id'),
                func.min(Comic.hash).label('cover_hash'),
                func.max(Comic.publisher).label('publisher')
            ).filter(
                Comic.library_id == library_id
            ).group_by(
                Comic.series
            ).all()

        # OPTIMIZATION 2: Fetch all comics with reading progress in ONE query (fixes N+1)
        if user_id_for_progress:
            # Eager load reading progress for ALL comics at once
            comics_query = session.query(Comic).filter(
                Comic.library_id == library_id
            ).options(
                selectinload(Comic.reading_progress)
            ).all()

            # Build a lookup dict: series_name -> list of comics
            comics_by_series = {}
            for comic in comics_query:
                series_name = comic.series or "Unknown"
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
                series_name = comic.series or "Unknown"
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

            # Sort volumes to find the first one (for cover selection)
            volumes.sort(key=get_comic_sort_key)

            # Determine if this is a standalone volume (single comic, not part of a series)
            is_standalone = series_data.total_issues == 1

            # Generate a stable ID for the series (use SeriesModel ID if available, else hash)
            series_id = series_data.series_id or abs(hash(series_name))

            # Use first volume's hash for cover if available, otherwise fallback to aggregated min hash
            cover_hash = series_data.cover_hash
            if volumes and volumes[0].get("hash"):
                cover_hash = volumes[0]["hash"]

            series_info = {
                "id": series_id,
                "name": series_name,
                "title": series_name,  # Alias for name
                "series": series_name, # Alias for name
                "series_name": series_name, # Legacy alias required by frontend
                "volumes": volumes,
                "publisher": series_data.publisher,
                "total_issues": series_data.total_issues,
                "cover_hash": cover_hash,
                "first_comic_id": series_data.first_comic_id,
                "is_standalone": is_standalone
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
            series_list.sort(key=lambda s: s["name"].lower())
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
    from ....database.models import Series as SeriesModel
    from ....database.models import Folder as FolderModel

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

        # Find comics by series field
        comics = session.query(Comic).filter(
            Comic.library_id == library_id,
            Comic.series == decoded_series_name
        ).all()

        # Fallback 2: Try to find by folder name
        if not comics:
            folder = session.query(FolderModel).filter(
                FolderModel.library_id == library_id,
                FolderModel.name == decoded_series_name
            ).first()

            if folder:
                # 1. Get comics directly in this folder
                comics = session.query(Comic).filter(
                    Comic.library_id == library_id,
                    Comic.folder_id == folder.id
                ).all()

                # 2. Get immediate subfolders
                subfolders = session.query(FolderModel).filter(
                    FolderModel.parent_id == folder.id
                ).all()

                # If we have either comics or subfolders (or both), build the response
                if comics or subfolders:
                    volumes = []

                    # Add subfolders as items
                    for subfolder in subfolders:
                        # Get cover hash from first comic in subfolder (recursive check could be better but expensive)
                        first_comic = session.query(Comic).filter(
                            Comic.folder_id == subfolder.id
                        ).order_by(Comic.filename).first()

                        cover_hash = first_comic.hash if first_comic else None

                        # Get comic count
                        count = session.query(func.count(Comic.id)).filter(
                            Comic.folder_id == subfolder.id
                        ).scalar()

                        volumes.append({
                            "id": subfolder.id,
                            "title": subfolder.name,
                            "series": subfolder.name,
                            "volume": None,
                            "issue_number": None,
                            "hash": cover_hash,
                            "type": "folder",
                            "item_count": count,
                            "is_completed": False,
                            "current_page": 0,
                            "num_pages": 0
                        })

                    # Add comics as items
                    for comic in comics:
                        volumes.append({
                            "id": comic.id,
                            "title": comic.title or comic.filename,
                            "series": comic.series,
                            "volume": comic.volume,
                            "issue_number": comic.issue_number,
                            "hash": comic.hash,
                            "type": "comic",
                            "item_count": 1,
                            "is_completed": False, # populated later
                            "current_page": 0,     # populated later
                            "num_pages": comic.num_pages,
                            "file_size": comic.file_size
                        })

                    # Return the series object with mixed content
                    # Note: We return early here, bypassing the default "comics only" logic below
                    # We need to populate reading progress manually for these items since we are returning early

                    # Get user for reading progress
                    user = get_request_user(request, session)

                    if user:
                        # Fetch progress for all comics in this view
                        comic_ids = [v["id"] for v in volumes if v["type"] == "comic"]
                        if comic_ids:
                            progress_records = session.query(ReadingProgress).filter(
                                ReadingProgress.user_id == user.id,
                                ReadingProgress.comic_id.in_(comic_ids)
                            ).all()
                            progress_map = {p.comic_id: p for p in progress_records}

                            for v in volumes:
                                if v["type"] == "comic" and v["id"] in progress_map:
                                    p = progress_map[v["id"]]
                                    v["current_page"] = p.current_page
                                    v["is_completed"] = p.is_completed

                    # Find a cover for the series group (use first volume with a hash)
                    series_cover_hash = None
                    for v in volumes:
                        if v.get("hash"):
                            series_cover_hash = v["hash"]
                            break

                    return {
                        "series_name": decoded_series_name,
                        "display_name": decoded_series_name,
                        "total_issues": len(volumes),
                        "completed_volumes": 0, # todo
                        "overall_progress": 0, # todo
                        "cover_hash": series_cover_hash,
                        "volumes": volumes
                    }



        if not comics:
            raise HTTPException(status_code=404, detail=f"Series not found: {decoded_series_name}")

        # Get user for reading progress
        user = get_request_user(request, session)

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
            if hasattr(comic, 'description') and comic.description:
                volume["synopsis"] = comic.description
            if hasattr(comic, 'writer') and comic.writer:
                volume["writer"] = comic.writer
            if hasattr(comic, 'publisher') and comic.publisher:
                volume["publisher"] = comic.publisher
            if hasattr(comic, 'genre') and comic.genre:
                volume["genre"] = comic.genre
            if hasattr(comic, 'year') and comic.year:
                volume["year"] = comic.year

            volumes.append(volume)

        volumes.sort(key=get_comic_sort_key)

        # Aggregate series metadata from first comic
        first_comic = comics[0]

        # Generate a stable ID for the series (use SeriesModel ID if available, else hash)
        series_id = series_record.id if series_record else abs(hash(decoded_series_name))

        series_detail = {
            "id": series_id,
            "name": decoded_series_name,
            "title": decoded_series_name, # Alias for name
            "series": decoded_series_name, # Alias for name
            "series_name": decoded_series_name, # Legacy
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

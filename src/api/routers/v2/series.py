"""
API v2 Router - Series

Endpoints for series management and browsing:
- GET /browse - Browse folder contents
- GET /series - Get all series in a library
- GET /series/{name} - Get detailed information about a specific series
- GET /libraries/browse-content - Browse all libraries

Note: Tree navigation endpoints moved to tree.py
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

from ....constants import ROOT_FOLDER_MARKER, COMIC_PATH_PREFIX
from ....database import (
    get_library_by_id,
    get_folders_in_library,
    get_comic_by_id,
    get_user_by_username,
    get_user_by_id,
    get_reading_progress,
)
from ....database.models import Comic, ReadingProgress, Folder as FolderModel
from ...middleware import get_current_user_id, get_request_user
from ._shared import get_comic_display_name, series_tree_cache, get_comic_sort_key
from ._item_builders import build_folder_item, build_comic_item
from ._browse_helpers import (
    parse_browse_path,
    apply_random_sort,
    batch_fetch_folder_metadata,
    batch_fetch_comic_progress,
    get_cover_hash_fallback,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Unified Folder Browsing
# ============================================================================

@router.get("/library/{library_id}/browse")
async def browse_folder(
    library_id: int,
    request: Request,
    path: Optional[str] = None,
    sort: Optional[str] = "name",
    offset: int = 0,
    limit: int = 50,
    seed: Optional[int] = None
):
    """
    Unified endpoint with Pagination.
    Returns mixed list of items (Folders and Comics).
    """
    from sqlalchemy import func, desc, case
    from ....services.library_cache import get_library_cache
    from ....database.models import Series
    import random

    # --------------------------------------------------------------------------
    # CACHE CHECK
    # --------------------------------------------------------------------------
    # Note: We check scanner config first to determine per_volume_metadata,
    # so we need to fetch library before checking cache to ensure cache key
    # includes per_volume_metadata state. For now, skip cache check here
    # and handle caching after we know the scanner config.
    cache_service = get_library_cache(library_id)
    cache_key = f"browse/{path}?sort={sort}&o={offset}&l={limit}" if path else f"browse/root?sort={sort}&o={offset}&l={limit}"
    
    # Skip cache for now - we'll check it after determining per_volume_metadata
    # This ensures cache includes the correct per_volume_metadata flag

    db = request.app.state.db

    with db.get_session() as session:
        # Get library - query directly to ensure fresh data
        from ....database.models import Library
        library = session.query(Library).filter(Library.id == library_id).first()
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Check if library uses a FILE-level scanner (per-volume metadata mode)
        # Use the exact same logic as the scanner config endpoint
        per_volume_metadata = False
        
        # Get settings - handle both dict and JSON string
        settings = library.settings
        if settings is None:
            settings = {}
        elif isinstance(settings, str):
            # If settings is a string, try to parse it as JSON
            try:
                import json
                settings = json.loads(settings)
            except:
                settings = {}
        
        scanner_config = settings.get('scanner', {}) if isinstance(settings, dict) else {}
        primary_scanner = scanner_config.get('primary_scanner') if isinstance(scanner_config, dict) else None
        
        # Debug logging
        logger.info(f"Browse: Library {library_id} - settings type={type(settings)}, settings={settings}, scanner_config={scanner_config}, primary_scanner={primary_scanner}")
        
        if primary_scanner:
            from ..scanners.manager import get_scanner_manager
            try:
                manager = get_scanner_manager()
                scanner_class = manager._available_scanners.get(primary_scanner)
                logger.info(f"Per-volume check: scanner={primary_scanner}, class_found={scanner_class is not None}")
                if scanner_class:
                    temp_scanner = scanner_class()
                    per_volume_metadata = temp_scanner.scan_level.value == 'file'
                    logger.info(f"Per-volume check: scan_level={temp_scanner.scan_level.value}, enabled={per_volume_metadata}")
            except Exception as e:
                logger.warning(f"Per-volume metadata check failed: {e}")

        # Find root folder
        root_folder = session.query(FolderModel).filter(
            FolderModel.library_id == library_id,
            FolderModel.name == ROOT_FOLDER_MARKER
        ).first()

        if not root_folder:
            raise HTTPException(status_code=404, detail="Library root not found")

        # Determine target folder
        current_folder = root_folder
        breadcrumbs = []
        
        # Check for comic path pattern: /_comic/ID
        if path and COMIC_PATH_PREFIX in path:
            decoded_path = unquote(path).strip('/')
            # Extract comic ID from path
            parts = decoded_path.split(COMIC_PATH_PREFIX)
            comic_id_str = parts[-1].split('/')[0] if parts else None
            
            # Build breadcrumbs from folder part (before _comic)
            folder_path = parts[0].rstrip('/') if len(parts) > 1 else ''
            if folder_path:
                folder_parts = folder_path.split('/')
                for part in folder_parts:
                    if not part: continue
                    child = session.query(FolderModel).filter(
                        FolderModel.parent_id == current_folder.id,
                        FolderModel.name == part
                    ).first()
                    if child:
                        current_folder = child
                        breadcrumbs.append({
                            "name": part,
                            "path": '/'.join(p["name"] for p in breadcrumbs) + ('/' if breadcrumbs else '') + part
                        })
            
            if comic_id_str and comic_id_str.isdigit():
                comic_id = int(comic_id_str)
                comic = get_comic_by_id(session, comic_id)
                
                if comic and comic.library_id == library_id:
                    # Get user progress
                    user = get_request_user(request, session)
                    progress = None
                    if user:
                        progress = get_reading_progress(session, user.id, comic_id)
                    
                    # Build comic item
                    comic_item = {
                        "id": comic.id,
                        "type": "comic",
                        "name": get_comic_display_name(comic),
                        "title": get_comic_display_name(comic),
                        "cover_hash": comic.hash,
                        "progress_percent": progress.progress_percent if progress else 0,
                        "is_completed": progress.is_completed if progress else False,
                        "current_page": progress.current_page if progress else 0,
                        "num_pages": comic.num_pages,
                        "size": comic.file_size,
                        # Full comic metadata
                        "series": comic.series,
                        "volume": comic.volume,
                        "issue_number": comic.issue_number,
                        "writer": comic.writer,
                        "artist": comic.penciller,
                        "publisher": comic.publisher,
                        "year": comic.year,
                        "genre": comic.genre,
                        "synopsis": comic.description,
                        "file_name": comic.filename,
                        "hash": comic.hash,
                    }
                    
                    # Return comic as single-item browse response
                    return JSONResponse({
                        "library": {"id": library.id, "name": library.name},
                        "folder": None,
                        "comic": comic_item,
                        "is_comic_view": True,
                        "breadcrumbs": breadcrumbs,
                        "items": [comic_item],
                        "total": 1,
                        "offset": 0,
                        "limit": 1
                    })
                else:
                    raise HTTPException(status_code=404, detail="Comic not found")
        
        if path:
            decoded_path = unquote(path).strip('/')
            path_parts = decoded_path.split('/') if decoded_path else []
            
            for i, part in enumerate(path_parts):
                if not part: continue
                child = session.query(FolderModel).filter(
                    FolderModel.parent_id == current_folder.id,
                    FolderModel.name == part
                ).first()
                if not child:
                    # Check if this is a comic file (by title or filename without extension)
                    # Only valid as the last path segment
                    if i == len(path_parts) - 1:
                        # Try to find comic by title first
                        comic = session.query(Comic).filter(
                            Comic.library_id == library_id,
                            Comic.folder_id == current_folder.id,
                            Comic.title == part
                        ).first()
                        
                        # If not found by title, try by filename (with various extensions)
                        if not comic:
                            # SQLite doesn't have regexp_replace, so use OR with LIKE patterns
                            from sqlalchemy import or_
                            comic = session.query(Comic).filter(
                                Comic.library_id == library_id,
                                Comic.folder_id == current_folder.id,
                                or_(
                                    Comic.filename == part,  # Exact match (already without extension)
                                    Comic.filename == part + '.cbz',
                                    Comic.filename == part + '.cbr',
                                    Comic.filename == part + '.cb7',
                                    Comic.filename == part + '.cbt',
                                    Comic.filename == part + '.CBZ',
                                    Comic.filename == part + '.CBR',
                                    Comic.filename == part + '.CB7',
                                    Comic.filename == part + '.CBT',
                                )
                            ).first()
                        
                        if comic:
                            # Get user progress
                            user = get_request_user(request, session)
                            progress = None
                            if user:
                                progress = get_reading_progress(session, user.id, comic.id)
                            
                            # Build comic item for the items list
                            comic_item = build_comic_item(
                                comic=comic,
                                progress=progress,
                                include_size=True,
                                include_metadata=per_volume_metadata
                            )
                            
                            # Treat single comic as "a series with one volume"
                            # Build folder-like metadata from the comic's info
                            folder_metadata = {
                                "id": comic.id,  # Use comic ID since there's no real folder
                                "name": get_comic_display_name(comic),
                                "total_issues": 1,
                                "cover_hash": comic.hash,
                                # Comic metadata for the info panel
                                "synopsis": comic.description,
                                "writer": comic.writer,
                                "artist": comic.penciller,
                                "publisher": comic.publisher,
                                "year": comic.year,
                                "genre": comic.genre,
                            }
                            
                            # Return as series-style browse response (unified view)
                            # Include per_volume_metadata and first_comic_metadata for FILE-level scanners
                            return JSONResponse({
                                "library": {"id": library.id, "name": library.name},
                                "folder": folder_metadata,
                                "comic": None,
                                "is_comic_view": False,
                                "per_volume_metadata": per_volume_metadata,
                                "first_comic_metadata": comic_item if per_volume_metadata else None,
                                "breadcrumbs": breadcrumbs,
                                "items": [comic_item],
                                "total": 1,
                                "offset": 0,
                                "limit": 1
                            })
                    
                    raise HTTPException(status_code=404, detail=f"Folder not found: {part}")
                current_folder = child
                breadcrumbs.append({
                    "name": part,
                    "path": '/'.join(p["name"] for p in breadcrumbs) + ('/' if breadcrumbs else '') + part
                })

        # -------------------
        # SORTING STRATEGY
        # -------------------
        user = get_request_user(request, session)
        
        items = []
        total_items = 0

        # Special Handling for Random Sort
        if sort == 'random':
             # 1. Fetch ALL IDs for this view
             all_folders = session.query(FolderModel.id).filter(
                 FolderModel.parent_id == current_folder.id
             ).all()
             folder_ids = [f.id for f in all_folders]

             all_comics = session.query(Comic.id).filter(
                 Comic.library_id == library_id,
                 Comic.folder_id == current_folder.id
             ).all()
             comic_ids = [c.id for c in all_comics]

             # Combine into a list of (id, type) tuples
             combined_items = [('folder', fid) for fid in folder_ids] + [('comic', cid) for cid in comic_ids]
             total_items = len(combined_items)

             # 2. Shuffle
             # Use provided seed or default
             rng = random.Random(seed) if seed is not None else random.Random()
             rng.shuffle(combined_items)

             # 3. Slice for pagination
             paged_items = combined_items[offset : offset + limit]

             # 4. Fetch details for sliced items
             # Split back into folders and comics
             paged_folder_ids = [i[1] for i in paged_items if i[0] == 'folder']
             paged_comic_ids = [i[1] for i in paged_items if i[0] == 'comic']

             # Batch fetch folders
             fetched_folders = []
             if paged_folder_ids:
                 fetched_folders = session.query(FolderModel).filter(
                     FolderModel.id.in_(paged_folder_ids)
                 ).all()
                 # Sort them back to match the shuffled order? No, we iterate paged_items
             
             # Batch fetch comics
             fetched_comics = []
             if paged_comic_ids:
                 fetched_comics = session.query(Comic).filter(
                     Comic.id.in_(paged_comic_ids)
                 ).all()

             # Map for O(1) retrieval
             folder_map = {f.id: f for f in fetched_folders}
             comic_map = {c.id: c for c in fetched_comics}

             # Batch fetch metadata for folders
             series_map = {}
             if fetched_folders:
                 sub_folder_names = [f.name for f in fetched_folders]
                 series_records = session.query(Series).filter(
                     Series.library_id == library_id,
                     Series.name.in_(sub_folder_names)
                 ).all()
                 series_map = {s.name: s for s in series_records}
             
             # Batch fetch children info for folders
             folders_with_children = set()
             if paged_folder_ids:
                 parents = session.query(FolderModel.parent_id).filter(
                     FolderModel.parent_id.in_(paged_folder_ids)
                 ).distinct().all()
                 folders_with_children = {p[0] for p in parents}

             # Batch fetch progress for comics
             progress_map = {}
             if user and fetched_comics:
                 progs = session.query(ReadingProgress).filter(
                     ReadingProgress.user_id == user.id, 
                     ReadingProgress.comic_id.in_(paged_comic_ids)
                 ).all()
                 progress_map = {p.comic_id: p for p in progs}

             # Reconstruct ordered list
             for item_type, item_id in paged_items:
                 if item_type == 'folder':
                     folder = folder_map.get(item_id)
                     if not folder: continue
                     
                     series_record = series_map.get(folder.name)
                     has_children = folder.id in folders_with_children
                     
                     cover_hash = folder.first_child_hash
                     
                     if not cover_hash:
                         cover_comic = session.query(Comic.hash).filter(
                            Comic.library_id == library_id,
                            Comic.path.startswith(folder.path + "/")
                         ).order_by(Comic.path).first()
                         if cover_comic: cover_hash = cover_comic[0]

                     item_data = build_folder_item(
                         folder=folder,
                         series_record=series_record,
                         has_children=has_children,
                         breadcrumbs=breadcrumbs,
                         cover_hash=cover_hash
                     )
                     items.append(item_data)
                 
                 elif item_type == 'comic':
                     comic = comic_map.get(item_id)
                     if not comic: continue
                     
                     p = progress_map.get(comic.id)
                     item_data = build_comic_item(
                         comic=comic,
                         progress=p,
                         include_size=True,
                         include_metadata=per_volume_metadata
                     )
                     items.append(item_data)

        else:
            # Standard Sorting Logic (Base queries + Sort + Limits)
            base_folders_query = session.query(FolderModel).filter(
                FolderModel.parent_id == current_folder.id
            )
            base_comics_query = session.query(Comic).filter(
                Comic.library_id == library_id,
                Comic.folder_id == current_folder.id
            )

            # Apply Sort
            folders_query = base_folders_query
            comics_query = base_comics_query

            if sort == 'created' or sort == 'recent':
                folders_query = folders_query.order_by(desc(FolderModel.created_at), FolderModel.name)
                comics_query = comics_query.order_by(desc(Comic.created_at), Comic.path)
            elif sort == 'updated':
                folders_query = folders_query.order_by(desc(FolderModel.updated_at), FolderModel.name)
                comics_query = comics_query.order_by(desc(Comic.file_modified_at), Comic.path)
            elif sort == 'progress' and user:
                # Sort comics by progress
                comics_query = comics_query.outerjoin(
                    ReadingProgress, 
                    (ReadingProgress.comic_id == Comic.id) & (ReadingProgress.user_id == user.id)
                ).order_by(
                    ReadingProgress.last_read_at.desc().nulls_last(),
                    ReadingProgress.progress_percent.desc().nulls_last(),
                    Comic.path
                )
                folders_query = folders_query.order_by(FolderModel.name)
            else:
                # Default: Name
                folders_query = folders_query.order_by(FolderModel.name)
                comics_query = comics_query.order_by(Comic.path)

            # PAGINATION LOGIC (Standard: Folders First)
            num_folders = session.query(func.count(FolderModel.id)).filter(
                FolderModel.parent_id == current_folder.id
            ).scalar()
            
            num_comics = session.query(func.count(Comic.id)).filter(
                Comic.library_id == library_id,
                Comic.folder_id == current_folder.id
            ).scalar()
            
            total_items = num_folders + num_comics
            
            # Fetch Folders
            if offset < num_folders:
                folder_limit = limit
                fetched_folders = folders_query.offset(offset).limit(folder_limit).all()
                
                # Fetch metadata
                sub_folder_names = [f.name for f in fetched_folders]
                series_map = {}
                if sub_folder_names:
                    series_records = session.query(Series).filter(
                        Series.library_id == library_id,
                        Series.name.in_(sub_folder_names)
                    ).all()
                    series_map = {s.name: s for s in series_records}
                    
                # Check children
                sub_folder_ids = [f.id for f in fetched_folders]
                folders_with_children = set()
                if sub_folder_ids:
                    parents = session.query(FolderModel.parent_id).filter(
                        FolderModel.parent_id.in_(sub_folder_ids)
                    ).distinct().all()
                    folders_with_children = {p[0] for p in parents}

                for folder in fetched_folders:
                    series_record = series_map.get(folder.name)
                    has_children = folder.id in folders_with_children
                    
                    cover_hash = folder.first_child_hash
                    
                    if not cover_hash:
                         cover_hash = get_cover_hash_fallback(session, library_id, folder)

                    item_data = build_folder_item(
                        folder=folder,
                        series_record=series_record,
                        has_children=has_children,
                        breadcrumbs=breadcrumbs,
                        cover_hash=cover_hash
                    )
                    items.append(item_data)
            
            # Fetch Comics
            folders_fetched = len(items)
            remaining_limit = limit - folders_fetched
            
            if remaining_limit > 0:
                comic_offset = max(0, offset - num_folders)
                fetched_comics = comics_query.offset(comic_offset).limit(remaining_limit).all()
                
                progress_map = {}
                if user and fetched_comics:
                    c_ids = [c.id for c in fetched_comics]
                    progs = session.query(ReadingProgress).filter(
                        ReadingProgress.user_id == user.id, 
                        ReadingProgress.comic_id.in_(c_ids)
                    ).all()
                    progress_map = {p.comic_id: p for p in progs}
                
                for comic in fetched_comics:
                    p = progress_map.get(comic.id)
                    item_data = build_comic_item(
                        comic=comic,
                        progress=p,
                        include_size=True,
                        include_metadata=per_volume_metadata
                    )
                    items.append(item_data)

        # Header metadata (only for non-root)
        folder_metadata = None
        if current_folder.id != root_folder.id:
             folder_metadata = {
                 "id": current_folder.id,
                 "name": current_folder.name,
                 "total_issues": total_items,
                 "cover_hash": current_folder.first_child_hash
             }
             
             # Fallback if no hash pre-calculated
             if not folder_metadata["cover_hash"]:
                 first_comic = session.query(Comic).filter(
                    Comic.library_id == library_id,
                    Comic.path.startswith(current_folder.path)
                 ).order_by(Comic.path).first()
                 
                 if first_comic:
                     folder_metadata["cover_hash"] = first_comic.hash
             
             # Look up Series record for this folder to include series metadata
             from ....database.models import Series as SeriesModel
             series_record = session.query(SeriesModel).filter(
                 SeriesModel.library_id == library_id,
                 SeriesModel.name == current_folder.name
             ).first()
             
             if series_record:
                 # Add series metadata fields for display
                 if series_record.display_name:
                     folder_metadata["display_name"] = series_record.display_name
                 if series_record.description:
                     folder_metadata["synopsis"] = series_record.description
                 if series_record.writer:
                     folder_metadata["writer"] = series_record.writer
                 if series_record.artist:
                     folder_metadata["artist"] = series_record.artist
                 if series_record.genre:
                     folder_metadata["genre"] = series_record.genre
                 if series_record.tags:
                     folder_metadata["tags"] = series_record.tags
                 if series_record.publisher:
                     folder_metadata["publisher"] = series_record.publisher
                 if series_record.year_start:
                     folder_metadata["year"] = series_record.year_start
                 if series_record.status:
                     folder_metadata["status"] = series_record.status
                 if series_record.format:
                     folder_metadata["format"] = series_record.format
                 if series_record.chapters:
                     folder_metadata["chapters"] = series_record.chapters
                 if series_record.volumes:
                     folder_metadata["volumes_count"] = series_record.volumes
                 
                 # Add scanner metadata
                 if series_record.scanner_source:
                     folder_metadata["scanner_source"] = series_record.scanner_source
                 if series_record.scanner_source_id:
                     folder_metadata["scanner_source_id"] = series_record.scanner_source_id
                 if series_record.scanner_source_url:
                     folder_metadata["scanner_source_url"] = series_record.scanner_source_url
                 if series_record.scan_confidence is not None:
                     folder_metadata["scan_confidence"] = series_record.scan_confidence
                 if series_record.scanned_at:
                     folder_metadata["scanned_at"] = series_record.scanned_at

        # Build first comic metadata for per-volume mode
        first_comic_metadata = None
        if per_volume_metadata and items:
            # Find first comic item
            for item in items:
                if item.get("type") == "comic":
                    # Use the item data that already has all metadata (since include_metadata=True was passed)
                    first_comic_metadata = item
                    break

        result = {
            "library": {"id": library.id, "name": library.name},
            "folder": folder_metadata,
            "breadcrumbs": breadcrumbs,
            "items": items,
            "total": total_items,
            "offset": offset,
            "limit": limit,
            "per_volume_metadata": per_volume_metadata,
            "first_comic_metadata": first_comic_metadata
        }

        # Cache (unless sorting by progress which is per-user, or random)
        if sort != 'random' and sort != 'progress':
            cache_service = get_library_cache(library_id)
            cache_path = path or "root"
            cache_params = {"sort": sort, "offset": offset, "limit": limit}
            cache_service.cache_response(cache_path, result, cache_params)
        
        return JSONResponse(result)

# ============================================================================
# Series Browsing
# ============================================================================

@router.get("/library/{library_id}/series")
async def get_series_list(
    library_id: int,
    request: Request,
    sort: Optional[str] = "name",
    include_metadata: Optional[bool] = True,
    offset: int = 0,
    limit: int = 50
):
    """
    Get top-level folders and comics for a library (Folder-Based View) with Pagination.

    Replaces old metadata-based series grouping with a direct Folder Browse view.
    This ensures the structure matches the Sidebar/File System exactly.
    """
    from sqlalchemy import func
    from ....services.library_cache import get_library_cache
    from ....database.models import Series

    # --------------------------------------------------------------------------
    # CACHE CHECK
    # --------------------------------------------------------------------------
    cache_service = get_library_cache(library_id)
    # Include sort/offset/limit in cache key
    cache_key = f"series/root?sort={sort}&o={offset}&l={limit}"
    
    # Random sort should NOT be cached
    if sort != 'random':
        cached_data = cache_service.get_cached_response(cache_key)
        if cached_data:
            return JSONResponse(cached_data)

    db = request.app.state.db

    with db.get_session() as session:
        # Get library
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Find root folder
        root_folder = session.query(FolderModel).filter(
            FolderModel.library_id == library_id,
            FolderModel.name == ROOT_FOLDER_MARKER
        ).first()

        if not root_folder:
            raise HTTPException(status_code=404, detail="Library root not found")
            
        current_folder = root_folder

        # -------------------
        # PAGINATION LOGIC
        # -------------------
        
        items = []
        total_items = 0
        
        if sort == 'random':
            # Complex random logic omitted for brevity/performance in pagination.
            # Just fallback to standard or implement simplified random later.
            # For now, treat same as Name sort but strictly for this structure
            pass

        # 1. Count totals
        num_folders = session.query(func.count(FolderModel.id)).filter(
            FolderModel.parent_id == current_folder.id
        ).scalar()
        
        num_comics = session.query(func.count(Comic.id)).filter(
            Comic.library_id == library_id,
            Comic.folder_id == current_folder.id
        ).scalar()
        
        total_items = num_folders + num_comics
        
        # 2. Fetch Folders
        if offset < num_folders:
            folder_limit = limit
            folders_query = session.query(FolderModel).filter(
                FolderModel.parent_id == current_folder.id
            ).order_by(FolderModel.name).offset(offset).limit(folder_limit).all()
            
            # Metadata Batch Fetch
            sub_folder_names = [f.name for f in folders_query]
            series_map = {}
            if sub_folder_names:
                series_records = session.query(Series).filter(
                    Series.library_id == library_id,
                    Series.name.in_(sub_folder_names)
                ).all()
                series_map = {s.name: s for s in series_records}
                
            sub_folder_ids = [f.id for f in folders_query]
            folders_with_children = set()
            if sub_folder_ids:
                parents = session.query(FolderModel.parent_id).filter(FolderModel.parent_id.in_(sub_folder_ids)).distinct().all()
                folders_with_children = {p[0] for p in parents}

            for folder in folders_query:
                series_record = series_map.get(folder.name)
                has_children = folder.id in folders_with_children
                cover_hash = folder.first_child_hash

                if not cover_hash:
                     cover_comic = session.query(Comic.hash).filter(
                        Comic.library_id == library_id,
                        Comic.path.startswith(folder.path + "/")
                     ).order_by(Comic.path).first()
                     if cover_comic: cover_hash = cover_comic[0]

                item_data = build_folder_item(
                    folder=folder,
                    series_record=series_record,
                    has_children=has_children,
                    cover_hash=cover_hash,
                    include_path=False,
                    minimal=True
                )
                items.append(item_data)

        # 3. Fetch Comics
        folders_fetched = len(items)
        remaining_limit = limit - folders_fetched
        
        if remaining_limit > 0:
            comic_offset = max(0, offset - num_folders)
            comics_query = session.query(Comic).filter(
                Comic.library_id == library_id,
                Comic.folder_id == current_folder.id
            ).order_by(Comic.path).offset(comic_offset).limit(remaining_limit).all()
            
            # Progress
            user = get_request_user(request, session)
            progress_map = {}
            if user and comics_query:
                c_ids = [c.id for c in comics_query]
                progs = session.query(ReadingProgress).filter(
                    ReadingProgress.user_id == user.id, 
                    ReadingProgress.comic_id.in_(c_ids)
                ).all()
                progress_map = {p.comic_id: p for p in progs}
            
            for comic in comics_query:
                p = progress_map.get(comic.id)
                item_data = build_comic_item(
                    comic=comic,
                    progress=p
                )
                items.append(item_data)

        result = {
            "library": {"id": library.id, "name": library.name},
            "items": items,
            "total": total_items,
            "offset": offset,
            "limit": limit
        }

        # Cache (if not random)
        if sort != 'random':
            cache_service.cache_response(cache_key, result)


@router.get("/libraries/browse-content")
async def browse_all_content(
    request: Request,
    sort: Optional[str] = "name",
    offset: int = 0,
    limit: int = 50,
    seed: Optional[int] = None
):
    """
    Unified endpoint to browse content from ALL libraries simultaneously.
    Returns mixed list of items (Folders and Comics) from the root of all libraries.
    """
    from sqlalchemy import func, desc, or_
    from ....database.models import Series, Library

    db = request.app.state.db

    with db.get_session() as session:
        # 1. Get all libraries and their root folders
        # We need mapping of root_folder_id -> library_id
        
        # Get all root folders
        root_folders = session.query(FolderModel).filter(
            FolderModel.name == ROOT_FOLDER_MARKER
        ).all()
        
        if not root_folders:
            return JSONResponse({
                "items": [],
                "total": 0,
                "offset": offset,
                "limit": limit
            })
            
        root_ids = [f.id for f in root_folders]
        
        # Map root folder ID to library for easy access later if needed
        # (Though FolderModel has library_id column, so we might not need explicit map)

        # -------------------
        # SORTING STRATEGY
        # -------------------
        # -------------------
        # SORTING STRATEGY
        # -------------------
        user = get_request_user(request, session)
        items = []
        
        if sort == 'random':
             import random
             logger.info(f"[BROWSE-CONTENT] Random sort requested with seed={seed}")
             
             # 1. Fetch ALL IDs for this view
             all_folders = session.query(FolderModel.id).filter(
                 FolderModel.parent_id.in_(root_ids)
             ).all()
             folder_ids = [f.id for f in all_folders]

             all_comics = session.query(Comic.id).filter(
                 Comic.folder_id.in_(root_ids)
             ).all()
             comic_ids = [c.id for c in all_comics]

             # Combine into a list of (type, id) tuples
             combined_items = [('folder', fid) for fid in folder_ids] + [('comic', cid) for cid in comic_ids]
             total_items = len(combined_items)
             logger.info(f"[BROWSE-CONTENT] Total items for shuffle: {total_items} (folders: {len(folder_ids)}, comics: {len(comic_ids)})")

             # 2. Shuffle
             rng = random.Random(seed) if seed is not None else random.Random()
             rng.shuffle(combined_items)

             # 3. Slice for pagination
             paged_items = combined_items[offset : offset + limit]

             # 4. Fetch details
             paged_folder_ids = [i[1] for i in paged_items if i[0] == 'folder']
             paged_comic_ids = [i[1] for i in paged_items if i[0] == 'comic']

             # Batch fetch folders
             fetched_folders = []
             if paged_folder_ids:
                 fetched_folders = session.query(FolderModel).filter(
                     FolderModel.id.in_(paged_folder_ids)
                 ).all()

             # Batch fetch comics
             fetched_comics = []
             if paged_comic_ids:
                 fetched_comics = session.query(Comic).filter(
                     Comic.id.in_(paged_comic_ids)
                 ).all()

             folder_map = {f.id: f for f in fetched_folders}
             comic_map = {c.id: c for c in fetched_comics}

             # Batch Metadata for Folders
             series_map = {}
             if fetched_folders:
                 sub_folder_names = [f.name for f in fetched_folders]
                 series_records = session.query(Series).filter(
                     Series.name.in_(sub_folder_names)
                 ).all()
                 # Map by (library_id, name) since names can be duplicated across libraries
                 series_map = {(s.library_id, s.name): s for s in series_records}

             # Batch Children Info
             folders_with_children = set()
             if paged_folder_ids:
                 parents = session.query(FolderModel.parent_id).filter(
                     FolderModel.parent_id.in_(paged_folder_ids)
                 ).distinct().all()
                 folders_with_children = {p[0] for p in parents}

             # Batch Progress for Comics
             progress_map = {}
             if user and fetched_comics:
                 c_ids = [c.id for c in fetched_comics]
                 progs = session.query(ReadingProgress).filter(
                     ReadingProgress.user_id == user.id,
                     ReadingProgress.comic_id.in_(c_ids)
                 ).all()
                 progress_map = {p.comic_id: p for p in progs}

             # Reconstruct ordered list
             for item_type, item_id in paged_items:
                 if item_type == 'folder':
                     folder = folder_map.get(item_id)
                     if not folder: continue
                     
                     series_record = series_map.get((folder.library_id, folder.name))
                     has_children = folder.id in folders_with_children
                     
                     cover_hash = folder.first_child_hash
                     if not cover_hash:
                          cover_comic = session.query(Comic.hash).filter(
                             Comic.library_id == folder.library_id,
                             Comic.path.startswith(folder.path + "/")
                          ).order_by(Comic.path).first()
                          if cover_comic: cover_hash = cover_comic[0]

                     item_data = build_folder_item(
                         folder=folder,
                         series_record=series_record,
                         has_children=has_children,
                         library_id=folder.library_id,
                         cover_hash=cover_hash
                     )
                     items.append(item_data)
                 
                 elif item_type == 'comic':
                     comic = comic_map.get(item_id)
                     if not comic: continue
                     
                     p = progress_map.get(comic.id)
                     item_data = build_comic_item(
                         comic=comic,
                         progress=p,
                         include_size=True,
                         include_library_id=True
                     )
                     items.append(item_data)

        else:
             # Base queries - looking for items whose parent is one of the root folders
             folders_query = session.query(FolderModel).filter(
                 FolderModel.parent_id.in_(root_ids)
             )
             
             # Comics at root of libraries (unlikely but possible)
             # Note: Comics don't have parent_id pointing to folder, they have folder_id
             comics_query = session.query(Comic).filter(
                 Comic.folder_id.in_(root_ids)
             )

             # Apply Sort
             if sort == 'created' or sort == 'recent':
                 folders_query = folders_query.order_by(desc(FolderModel.created_at), FolderModel.name)
                 comics_query = comics_query.order_by(desc(Comic.created_at), Comic.path)
             elif sort == 'updated':
                 folders_query = folders_query.order_by(desc(FolderModel.updated_at), FolderModel.name)
                 comics_query = comics_query.order_by(desc(Comic.file_modified_at), Comic.path)
             elif sort == 'progress' and user:
                 # Sort comics by progress
                 comics_query = comics_query.outerjoin(
                     ReadingProgress, 
                     (ReadingProgress.comic_id == Comic.id) & (ReadingProgress.user_id == user.id)
                 ).order_by(
                     desc(ReadingProgress.last_read_at.nullslast()),
                     desc(ReadingProgress.progress_percent.nullslast()),
                     Comic.path
                 )
                 # Folders sort by name for now
                 folders_query = folders_query.order_by(FolderModel.name)
             else:
                 # Default: Name
                 folders_query = folders_query.order_by(FolderModel.name)
                 comics_query = comics_query.order_by(Comic.path)

             # -------------------
             # PAGINATION LOGIC
             # -------------------
             
             # 1. Count totals
             num_folders = session.query(func.count(FolderModel.id)).filter(
                 FolderModel.parent_id.in_(root_ids)
             ).scalar()
             
             num_comics = session.query(func.count(Comic.id)).filter(
                 Comic.folder_id.in_(root_ids)
             ).scalar()
             
             total_items = num_folders + num_comics
             
             # 2. Fetch Folders
             if offset < num_folders:
                 folder_limit = limit
                 fetched_folders = folders_query.offset(offset).limit(folder_limit).all()
                 
                 # Batch fetch metadata
                 sub_folder_names = [f.name for f in fetched_folders]
                 series_map = {}
                 if sub_folder_names:
                     # Need to be careful about strict name matching across libraries if names duplicate
                     # Use name + library_id tuple? Or just simple map for now.
                     # Ideally we fetch Series where name IN names AND library_id IN library_ids
                     series_records = session.query(Series).filter(
                        Series.name.in_(sub_folder_names)
                     ).all()
                     # Map by (library_id, name)
                     series_map = {(s.library_id, s.name): s for s in series_records}
                     
                 # Check children
                 sub_folder_ids = [f.id for f in fetched_folders]
                 folders_with_children = set()
                 if sub_folder_ids:
                     parents = session.query(FolderModel.parent_id).filter(
                         FolderModel.parent_id.in_(sub_folder_ids)
                     ).distinct().all()
                     folders_with_children = {p[0] for p in parents}

                 for folder in fetched_folders:
                     series_record = series_map.get((folder.library_id, folder.name))
                     has_children = folder.id in folders_with_children
                     
                     cover_hash = folder.first_child_hash
                     
                     # Fallback cover query
                     if not cover_hash:
                          cover_comic = session.query(Comic.hash).filter(
                             Comic.library_id == folder.library_id,
                             Comic.path.startswith(folder.path + "/")
                          ).order_by(Comic.path).first()
                          if cover_comic: cover_hash = cover_comic[0]

                     item_data = build_folder_item(
                         folder=folder,
                         series_record=series_record,
                         has_children=has_children,
                         library_id=folder.library_id,
                         cover_hash=cover_hash
                     )
                     items.append(item_data)
             
             # 3. Fetch Comics
             folders_fetched = len(items)
             remaining_limit = limit - folders_fetched
             
             if remaining_limit > 0:
                 comic_offset = max(0, offset - num_folders)
                 
                 fetched_comics = comics_query.offset(comic_offset).limit(remaining_limit).all()
                 
                 # User progress (batch fetch)
                 progress_map = {}
                 if user and fetched_comics:
                     c_ids = [c.id for c in fetched_comics]
                     progs = session.query(ReadingProgress).filter(
                         ReadingProgress.user_id == user.id, 
                         ReadingProgress.comic_id.in_(c_ids)
                     ).all()
                     progress_map = {p.comic_id: p for p in progs}
                 
                 for comic in fetched_comics:
                     p = progress_map.get(comic.id)
                     item_data = build_comic_item(
                         comic=comic,
                         progress=p,
                         include_size=True,
                         include_library_id=True
                     )
                     items.append(item_data)

        return JSONResponse({
            "items": items,
            "total": total_items,
            "offset": offset,
            "limit": limit
        })



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

        # =========================================================================
        # IMPORTANT: BROWSING MUST USE FOLDER STRUCTURE ONLY
        # =========================================================================
        # DO NOT use Comic.series or any other metadata field for navigation/browsing.
        # The folder hierarchy is the ONLY source of truth for the browse structure.
        # Metadata (series, writer, publisher, etc.) is for DISPLAY purposes only,
        # NOT for determining what content appears where.
        # =========================================================================

        # Find folder by name - this is the ONLY way to browse
        folder = session.query(FolderModel).filter(
            FolderModel.library_id == library_id,
            FolderModel.name == decoded_series_name
        ).first()

        if not folder:
            raise HTTPException(status_code=404, detail=f"Folder not found: {decoded_series_name}")

        # Get comics directly in this folder
        folder_comics = session.query(Comic).filter(
            Comic.library_id == library_id,
            Comic.folder_id == folder.id
        ).all()

        # Get immediate subfolders
        subfolders = session.query(FolderModel).filter(
            FolderModel.parent_id == folder.id
        ).all()

        # Build volumes list from folder contents
        if subfolders or folder_comics:
            volumes = []

            # Add subfolders as items
            for subfolder in subfolders:
                # Get cover hash from first comic in subfolder (recursive)
                first_comic = session.query(Comic).filter(
                    Comic.library_id == library_id,
                    Comic.path.startswith(subfolder.path)
                ).order_by(Comic.path).first()

                cover_hash = first_comic.hash if first_comic else None

                # Get comic count (recursive)
                count = session.query(func.count(Comic.id)).filter(
                    Comic.library_id == library_id,
                    Comic.path.startswith(subfolder.path + "/")
                ).scalar() or 0

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

                # Add loose comics in this folder as items
                for comic in folder_comics:
                    volumes.append({
                        "id": comic.id,
                        "title": comic.title or comic.filename,
                        "series": comic.series,
                        "volume": comic.volume,
                        "issue_number": comic.issue_number,
                        "hash": comic.hash,
                        "type": "comic",
                        "item_count": 1,
                        "is_completed": False,
                        "current_page": 0,
                        "num_pages": comic.num_pages,
                        "file_size": comic.file_size
                    })

                # Get user for reading progress
                user = get_request_user(request, session)

                if user:
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

                # Find cover
                series_cover_hash = None
                for v in volumes:
                    if v.get("hash"):
                        series_cover_hash = v["hash"]
                        break

                return {
                    "series_name": decoded_series_name,
                    "display_name": decoded_series_name,
                    "total_issues": len(volumes),
                    "completed_volumes": 0,
                    "overall_progress": 0,
                    "cover_hash": series_cover_hash,
                    "volumes": volumes
                }

            # No subfolders - just comics in this folder
            else:
                # Get user for reading progress
                user = get_request_user(request, session)

                # Build volumes list from comics in this folder
                volumes = []
                for comic in folder_comics:
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

                    volume = {
                        "type": "comic",
                        "id": comic.id,
                        "title": get_comic_display_name(comic),
                        "series": comic.series,
                        "volume": comic.volume,
                        "issue_number": comic.issue_number,
                        "filename": comic.filename,
                        "file_size": comic.file_size,
                        "hash": comic.hash,
                        "num_pages": comic.num_pages,
                        "current_page": current_page,
                        "is_completed": is_completed,
                        "progress_percent": progress_percent,
                        "last_read_at": last_read_at,
                        "library_id": library_id,
                        "created_at": comic.created_at
                    }

                    # Add optional metadata fields (for DISPLAY only)
                    if comic.description:
                        volume["synopsis"] = comic.description
                    if comic.writer:
                        volume["writer"] = comic.writer
                    if comic.publisher:
                        volume["publisher"] = comic.publisher
                    if comic.genre:
                        volume["genre"] = comic.genre
                    if comic.year:
                        volume["year"] = comic.year

                    volumes.append(volume)

                volumes.sort(key=get_comic_sort_key)

                # Get cover from first comic
                first_comic = folder_comics[0] if folder_comics else None
                series_cover_hash = first_comic.hash if first_comic else None

                # Try to get Series metadata for display (NOT for browsing)
                from ....database.models import Series as SeriesModel
                series_record = session.query(SeriesModel).filter(
                    SeriesModel.library_id == library_id,
                    SeriesModel.name == decoded_series_name
                ).first()

                series_detail = {
                    "series_name": decoded_series_name,
                    "display_name": decoded_series_name,
                    "total_issues": len(volumes),
                    "cover_hash": series_cover_hash,
                    "volumes": volumes
                }

                # Add Series metadata for DISPLAY (if available)
                if series_record:
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
                    if series_record.tags:
                        series_detail["tags"] = series_record.tags
                elif first_comic:
                    # Fallback to comic-level metadata
                    if first_comic.publisher:
                        series_detail["publisher"] = first_comic.publisher
                    if first_comic.year:
                        series_detail["year"] = first_comic.year
                    if first_comic.genre:
                        series_detail["genre"] = first_comic.genre

                # Calculate overall reading progress
                completed_volumes = sum(1 for v in volumes if v["is_completed"])
                series_detail["completed_volumes"] = completed_volumes
                series_detail["overall_progress"] = (completed_volumes / len(volumes) * 100) if volumes else 0

                logger.debug(f"v2 API: Returning series detail for '{decoded_series_name}' with {len(volumes)} volumes")
                return JSONResponse(series_detail)

        # Empty folder
        return JSONResponse({
            "series_name": decoded_series_name,
            "display_name": decoded_series_name,
            "total_issues": 0,
            "cover_hash": None,
            "volumes": []
        })


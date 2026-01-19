"""
Helper functions for browse_folder endpoint.

These functions extract complex logic from the browse_folder endpoint in series.py
to improve readability and maintainability.
"""

from typing import Optional, List, Dict, Tuple
from urllib.parse import unquote
import random

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ....database.models import (
    Folder as FolderModel,
    Comic,
    Series,
    ReadingProgress
)
from ....database.operations import get_comic_by_id
from ._shared import get_comic_display_name


def parse_browse_path(
    path: Optional[str],
    library_id: int,
    root_folder: FolderModel,
    session: Session
) -> Tuple[FolderModel, List[dict], Optional[dict]]:
    """
    Parse browse path and build breadcrumbs.
    
    Handles both regular folder paths and special comic view paths (/_comic/ID).
    
    Args:
        path: URL path to parse (may be None for root)
        library_id: Library ID for validation
        root_folder: Root folder of the library
        session: Database session
    
    Returns:
        Tuple of (current_folder, breadcrumbs, comic_item_or_none)
        - current_folder: The folder to browse
        - breadcrumbs: List of breadcrumb dicts with "name" and "path" keys
        - comic_item_or_none: If comic view path, returns comic data dict, else None
    """
    current_folder = root_folder
    breadcrumbs = []
    
    if not path:
        return current_folder, breadcrumbs, None
    
    # Check for comic path pattern: /_comic/ID
    if '_comic/' in path:
        decoded_path = unquote(path).strip('/')
        # Extract comic ID from path
        parts = decoded_path.split('_comic/')
        comic_id_str = parts[-1].split('/')[0] if parts else None
        
        # Build breadcrumbs from folder part (before _comic)
        folder_path = parts[0].rstrip('/') if len(parts) > 1 else ''
        if folder_path:
            folder_parts = folder_path.split('/')
            for part in folder_parts:
                if not part:
                    continue
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
            
            if not comic or comic.library_id != library_id:
                raise HTTPException(status_code=404, detail="Comic not found")
            
            # Note: Comic item returned here should have progress fetched by caller
            # This function returns the base comic dict without progress
            return current_folder, breadcrumbs, comic
    
    # Regular folder path
    decoded_path = unquote(path).strip('/')
    path_parts = decoded_path.split('/') if decoded_path else []
    
    for part in path_parts:
        if not part:
            continue
        child = session.query(FolderModel).filter(
            FolderModel.parent_id == current_folder.id,
            FolderModel.name == part
        ).first()
        if not child:
            raise HTTPException(status_code=404, detail=f"Folder not found: {part}")
        current_folder = child
        breadcrumbs.append({
            "name": part,
            "path": '/'.join(p["name"] for p in breadcrumbs) + ('/' if breadcrumbs else '') + part
        })
    
    return current_folder, breadcrumbs, None


def apply_random_sort(
    session: Session,
    folder_id: int,
    library_id: int,
    offset: int,
    limit: int,
    seed: Optional[int] = None
) -> Tuple[List[Tuple[str, int]], int]:
    """
    Apply random sorting to folders and comics.
    
    Fetches all folder and comic IDs, shuffles them using the provided seed,
    then returns the paginated slice.
    
    Args:
        session: Database session
        folder_id: Parent folder ID
        library_id: Library ID
        offset: Pagination offset
        limit: Pagination limit
        seed: Random seed for reproducible shuffling
    
    Returns:
        Tuple of (paged_items, total_count)
        - paged_items: List of (type, id) tuples where type is 'folder' or 'comic'
        - total_count: Total number of items before pagination
    """
    # Fetch ALL IDs for this view
    all_folders = session.query(FolderModel.id).filter(
        FolderModel.parent_id == folder_id
    ).all()
    folder_ids = [f.id for f in all_folders]
    
    all_comics = session.query(Comic.id).filter(
        Comic.library_id == library_id,
        Comic.folder_id == folder_id
    ).all()
    comic_ids = [c.id for c in all_comics]
    
    # Combine into a list of (type, id) tuples
    combined_items = [('folder', fid) for fid in folder_ids] + [('comic', cid) for cid in comic_ids]
    total_count = len(combined_items)
    
    # Shuffle using provided seed or default random
    rng = random.Random(seed) if seed is not None else random.Random()
    rng.shuffle(combined_items)
    
    # Slice for pagination
    paged_items = combined_items[offset : offset + limit]
    
    return paged_items, total_count


def batch_fetch_folder_metadata(
    session: Session,
    folders: List[FolderModel],
    library_id: int
) -> Tuple[Dict[str, Series], Dict[int, bool]]:
    """
    Batch load Series records and children info for folders.
    
    Args:
        session: Database session
        folders: List of Folder instances
        library_id: Library ID
    
    Returns:
        Tuple of (series_map, folders_with_children_set)
        - series_map: Dict mapping folder name to Series record
        - folders_with_children_set: Set of folder IDs that have children
    """
    if not folders:
        return {}, set()
    
    # Fetch Series metadata
    sub_folder_names = [f.name for f in folders]
    series_records = session.query(Series).filter(
        Series.library_id == library_id,
        Series.name.in_(sub_folder_names)
    ).all()
    series_map = {s.name: s for s in series_records}
    
    # Check which folders have children
    sub_folder_ids = [f.id for f in folders]
    parents = session.query(FolderModel.parent_id).filter(
        FolderModel.parent_id.in_(sub_folder_ids)
    ).distinct().all()
    folders_with_children = {p[0] for p in parents}
    
    return series_map, folders_with_children


def batch_fetch_comic_progress(
    session: Session,
    comic_ids: List[int],
    user_id: int
) -> Dict[int, ReadingProgress]:
    """
    Batch load ReadingProgress records for comics.
    
    Args:
        session: Database session
        comic_ids: List of comic IDs
        user_id: User ID
    
    Returns:
        Dict mapping comic ID to ReadingProgress record
    """
    if not comic_ids or not user_id:
        return {}
    
    progs = session.query(ReadingProgress).filter(
        ReadingProgress.user_id == user_id,
        ReadingProgress.comic_id.in_(comic_ids)
    ).all()
    
    return {p.comic_id: p for p in progs}


def get_cover_hash_fallback(
    session: Session,
    library_id: int,
    folder: FolderModel
) -> Optional[str]:
    """
    Get fallback cover hash for a folder.
    
    Searches for the first comic in the folder path when the folder
    doesn't have a pre-calculated cover hash.
    
    Args:
        session: Database session
        library_id: Library ID
        folder: Folder instance
    
    Returns:
        Cover hash string or None if no comics found
    """
    cover_comic = session.query(Comic.hash).filter(
        Comic.library_id == library_id,
        Comic.path.startswith(folder.path + "/")
    ).order_by(Comic.path).first()
    
    if cover_comic:
        return cover_comic[0]
    
    return None

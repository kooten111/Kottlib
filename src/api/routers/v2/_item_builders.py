"""
Helper functions for building standardized item responses.

These functions consolidate duplicated item-building patterns across
browse endpoints in series.py.
"""

from typing import Optional, List, Dict, Any
from ....database.models import Folder as FolderModel, Comic, ReadingProgress, Series
from ._shared import get_comic_display_name


def build_folder_item(
    folder: FolderModel,
    series_record: Optional[Series],
    has_children: bool,
    breadcrumbs: Optional[List[dict]] = None,
    library_id: Optional[int] = None,
    include_path: bool = True,
    minimal: bool = False,
    cover_hash: Optional[str] = None
) -> dict:
    """
    Build standardized folder item for browse responses.
    
    Args:
        folder: Folder model instance
        series_record: Optional Series record associated with this folder
        has_children: Whether this folder has child folders
        breadcrumbs: Optional list of breadcrumb dictionaries with "name" keys
        library_id: Optional library ID (included in response if provided)
        include_path: Whether to include the path field
        minimal: If True, include only minimal metadata
        cover_hash: Optional explicit cover hash (if None, uses folder.first_child_hash or series cover)
    
    Returns:
        Dictionary representing the folder item
    """
    # Determine cover hash
    if cover_hash is None:
        cover_hash = folder.first_child_hash
    
    item_data = {
        "id": folder.id,
        "type": "collection" if has_children else "series",
        "name": folder.name,
        "title": folder.name,
        "cover_hash": cover_hash,
        "total_issues": series_record.total_issues if series_record else 0,
    }
    
    # Add path if requested
    if include_path and breadcrumbs is not None:
        item_data["path"] = '/'.join([b["name"] for b in breadcrumbs] + [folder.name]) if breadcrumbs else folder.name
    elif include_path:
        item_data["path"] = folder.name
    
    # Add library_id if provided
    if library_id is not None:
        item_data["library_id"] = library_id
    
    # Add series metadata if available
    if series_record and not minimal:
        item_data.update({
            "writer": series_record.writer,
            "description": series_record.description,
            "status": series_record.status
        })
    elif series_record and minimal:
        # Minimal metadata - only status
        item_data.update({"status": series_record.status})
    
    return item_data


def build_comic_item(
    comic: Comic,
    progress: Optional[ReadingProgress],
    include_library_id: bool = False,
    include_size: bool = False,
    include_metadata: bool = False
) -> dict:
    """
    Build standardized comic item for browse responses.
    
    Args:
        comic: Comic model instance
        progress: Optional ReadingProgress record for this comic and user
        include_library_id: Whether to include library_id in response
        include_size: Whether to include file size in response
        include_metadata: Whether to include full metadata fields (for per-volume mode)
    
    Returns:
        Dictionary representing the comic item
    """
    item_data = {
        "id": comic.id,
        "type": "comic",
        "name": get_comic_display_name(comic),
        "title": get_comic_display_name(comic),
        "cover_hash": comic.hash,
        "progress_percent": progress.progress_percent if progress else 0,
        "is_completed": progress.is_completed if progress else False,
        "current_page": progress.current_page if progress else 0,
        "num_pages": comic.num_pages,
    }
    
    # Add optional fields
    if include_size:
        item_data["size"] = comic.file_size
    
    if include_library_id:
        item_data["library_id"] = comic.library_id
    
    # Add metadata fields when requested (for per-volume metadata mode)
    if include_metadata:
        item_data.update({
            "synopsis": comic.description,
            "description": comic.description,  # Alias for compatibility
            "writer": comic.writer,
            "artist": comic.penciller,
            "penciller": comic.penciller,  # Alias for compatibility
            "publisher": comic.publisher,
            "year": comic.year,
            "genre": comic.genre,
            "tags": comic.tags,
            "scanner_source": comic.scanner_source,
            "scanner_source_id": comic.scanner_source_id,
            "scanner_source_url": comic.scanner_source_url,
            "scan_confidence": comic.scan_confidence,
        })
    
    return item_data

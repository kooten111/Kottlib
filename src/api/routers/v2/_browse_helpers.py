"""
Helper functions for browse_folder endpoint.

These functions extract complex logic from the browse_folder endpoint in series.py
to improve readability and maintainability.
"""

from typing import Optional, List, Dict, Tuple
import random

from sqlalchemy import case, func, desc, or_
from sqlalchemy.orm import Session, Query
from sqlalchemy.sql.elements import ColumnElement

from ....database.models import (
    Folder as FolderModel,
    Comic,
    Series,
    ReadingProgress,
)
from ._item_builders import build_folder_item, build_comic_item


def volume_progress_expr() -> ColumnElement:
    """Per-volume progress score: 100 if completed, else progress_percent (0 if unset)."""
    return case(
        (ReadingProgress.is_completed.is_(True), 100.0),
        else_=func.coalesce(ReadingProgress.progress_percent, 0.0),
    )


def folder_progress_subquery(
    session: Session,
    user_id: int,
    library_id: Optional[int] = None,
):
    """
    Subquery of folder_id -> avg volume progress for a user.

    Averages direct child comics (Comic.folder_id). Completed volumes count as 100%.
    """
    query = (
        session.query(
            Comic.folder_id.label("folder_id"),
            func.avg(volume_progress_expr()).label("avg_progress"),
        )
        .outerjoin(
            ReadingProgress,
            (ReadingProgress.comic_id == Comic.id)
            & (ReadingProgress.user_id == user_id),
        )
        .filter(Comic.folder_id.isnot(None))
    )
    if library_id is not None:
        query = query.filter(Comic.library_id == library_id)
    return query.group_by(Comic.folder_id).subquery()


def apply_progress_order_to_queries(
    session: Session,
    folders_query: Query,
    comics_query: Query,
    user_id: int,
    library_id: Optional[int] = None,
) -> Tuple[Query, Query]:
    """Order folder/comic queries by reading progress (highest first)."""
    progress_subq = folder_progress_subquery(session, user_id, library_id)
    folders_query = folders_query.outerjoin(
        progress_subq,
        progress_subq.c.folder_id == FolderModel.id,
    ).order_by(
        progress_subq.c.avg_progress.desc().nulls_last(),
        FolderModel.name,
    )

    volume_progress = volume_progress_expr()
    comics_query = comics_query.outerjoin(
        ReadingProgress,
        (ReadingProgress.comic_id == Comic.id) & (ReadingProgress.user_id == user_id),
    ).order_by(
        volume_progress.desc(),
        Comic.path,
    )
    return folders_query, comics_query


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


def count_folder_children(
    session: Session,
    folder_id: int,
    library_id: int,
) -> Tuple[int, int]:
    """Return (folder_count, comic_count) for direct children of a folder."""
    num_folders = session.query(func.count(FolderModel.id)).filter(
        FolderModel.parent_id == folder_id
    ).scalar()
    num_comics = session.query(func.count(Comic.id)).filter(
        Comic.library_id == library_id,
        Comic.folder_id == folder_id,
    ).scalar()
    return num_folders, num_comics


def apply_browse_sort_queries(
    session: Session,
    library_id: int,
    current_folder: FolderModel,
    normalized_sort: str,
    user,
) -> Tuple[Query, Query]:
    """Build sorted folder and comic queries for standard browse pagination."""
    folders_query = session.query(FolderModel).filter(
        FolderModel.parent_id == current_folder.id
    )
    comics_query = session.query(Comic).filter(
        Comic.library_id == library_id,
        Comic.folder_id == current_folder.id,
    )

    if normalized_sort in ("created", "recent"):
        folders_query = folders_query.order_by(desc(FolderModel.created_at), FolderModel.name)
        comics_query = comics_query.order_by(desc(Comic.created_at), Comic.path)
    elif normalized_sort == "updated":
        folders_query = folders_query.order_by(
            desc(func.coalesce(FolderModel.last_content_at, FolderModel.created_at)),
            FolderModel.name,
        )
        comics_query = comics_query.order_by(desc(Comic.created_at), Comic.path)
    elif normalized_sort == "progress" and user:
        folders_query, comics_query = apply_progress_order_to_queries(
            session,
            folders_query,
            comics_query,
            user_id=user.id,
            library_id=library_id,
        )
    else:
        folders_query = folders_query.order_by(FolderModel.name)
        comics_query = comics_query.order_by(Comic.path)

    return folders_query, comics_query


def _folder_items_for_folders(
    session: Session,
    library_id: int,
    folders: List[FolderModel],
    breadcrumbs: List[dict],
) -> List[dict]:
    if not folders:
        return []

    series_map, folders_with_children = batch_fetch_folder_metadata(
        session, folders, library_id
    )

    cover_by_folder_id: Dict[int, Optional[str]] = {
        folder.id: folder.first_child_hash for folder in folders if folder.first_child_hash
    }
    needing_fallback = [f for f in folders if not f.first_child_hash]
    if needing_fallback:
        prefixes = [(f.id, f.path + "/") for f in needing_fallback if f.path]
        if prefixes:
            or_filters = [Comic.path.startswith(prefix) for _, prefix in prefixes]
            path_filter = or_(*or_filters) if len(or_filters) > 1 else or_filters[0]
            rows = session.query(Comic.hash, Comic.path).filter(
                Comic.library_id == library_id,
                path_filter,
            ).order_by(Comic.path).all()
            for folder_id, prefix in prefixes:
                for comic_hash, comic_path in rows:
                    if comic_path.startswith(prefix):
                        cover_by_folder_id[folder_id] = comic_hash
                        break

    items: List[dict] = []
    for folder in folders:
        cover_hash = folder.first_child_hash or cover_by_folder_id.get(folder.id)
        items.append(
            build_folder_item(
                folder=folder,
                series_record=series_map.get(folder.name),
                has_children=folder.id in folders_with_children,
                breadcrumbs=breadcrumbs,
                cover_hash=cover_hash,
            )
        )
    return items


def _comic_items_for_comics(
    session: Session,
    comics: List[Comic],
    user,
    per_volume_metadata: bool,
) -> List[dict]:
    if not comics:
        return []

    progress_map: Dict[int, ReadingProgress] = {}
    if user:
        progress_map = batch_fetch_comic_progress(
            session, [comic.id for comic in comics], user.id
        )

    return [
        build_comic_item(
            comic=comic,
            progress=progress_map.get(comic.id),
            include_size=True,
            include_metadata=per_volume_metadata,
        )
        for comic in comics
    ]


def fetch_random_browse_items(
    session: Session,
    library_id: int,
    current_folder: FolderModel,
    breadcrumbs: List[dict],
    user,
    offset: int,
    limit: int,
    seed: Optional[int],
    per_volume_metadata: bool,
) -> Tuple[List[dict], int]:
    """Fetch a shuffled, paginated browse page."""
    paged_items, total_items = apply_random_sort(
        session,
        current_folder.id,
        library_id,
        offset,
        limit,
        seed,
    )

    paged_folder_ids = [item_id for item_type, item_id in paged_items if item_type == "folder"]
    paged_comic_ids = [item_id for item_type, item_id in paged_items if item_type == "comic"]

    folder_map: Dict[int, FolderModel] = {}
    if paged_folder_ids:
        fetched_folders = session.query(FolderModel).filter(
            FolderModel.id.in_(paged_folder_ids)
        ).all()
        folder_map = {folder.id: folder for folder in fetched_folders}

    comic_map: Dict[int, Comic] = {}
    if paged_comic_ids:
        fetched_comics = session.query(Comic).filter(Comic.id.in_(paged_comic_ids)).all()
        comic_map = {comic.id: comic for comic in fetched_comics}

    series_map: Dict[str, Series] = {}
    folders_with_children: set = set()
    if folder_map:
        series_map, folders_with_children = batch_fetch_folder_metadata(
            session, list(folder_map.values()), library_id
        )

    progress_map: Dict[int, ReadingProgress] = {}
    if user and paged_comic_ids:
        progress_map = batch_fetch_comic_progress(session, paged_comic_ids, user.id)

    items: List[dict] = []
    for item_type, item_id in paged_items:
        if item_type == "folder":
            folder = folder_map.get(item_id)
            if not folder:
                continue
            cover_hash = folder.first_child_hash or get_cover_hash_fallback(
                session, library_id, folder
            )
            items.append(
                build_folder_item(
                    folder=folder,
                    series_record=series_map.get(folder.name),
                    has_children=folder.id in folders_with_children,
                    breadcrumbs=breadcrumbs,
                    cover_hash=cover_hash,
                )
            )
        elif item_type == "comic":
            comic = comic_map.get(item_id)
            if not comic:
                continue
            items.append(
                build_comic_item(
                    comic=comic,
                    progress=progress_map.get(comic.id),
                    include_size=True,
                    include_metadata=per_volume_metadata,
                )
            )

    return items, total_items


def fetch_sorted_browse_items(
    session: Session,
    library_id: int,
    current_folder: FolderModel,
    breadcrumbs: List[dict],
    user,
    normalized_sort: str,
    offset: int,
    limit: int,
    per_volume_metadata: bool,
) -> Tuple[List[dict], int]:
    """Fetch a sorted, paginated browse page (folders first, then comics)."""
    folders_query, comics_query = apply_browse_sort_queries(
        session, library_id, current_folder, normalized_sort, user
    )

    num_folders, num_comics = count_folder_children(
        session, current_folder.id, library_id
    )
    total_items = num_folders + num_comics
    items: List[dict] = []

    if offset < num_folders:
        fetched_folders = folders_query.offset(offset).limit(limit).all()
        items.extend(
            _folder_items_for_folders(session, library_id, fetched_folders, breadcrumbs)
        )

    remaining_limit = limit - len(items)
    if remaining_limit > 0:
        comic_offset = max(0, offset - num_folders)
        fetched_comics = comics_query.offset(comic_offset).limit(remaining_limit).all()
        items.extend(
            _comic_items_for_comics(session, fetched_comics, user, per_volume_metadata)
        )

    return items, total_items


def find_first_comic_metadata(items: List[dict]) -> Optional[dict]:
    """Return the first comic item dict from a browse items list."""
    for item in items:
        if item.get("type") == "comic":
            return item
    return None

"""
API v2 Router - Collections

Endpoints for user collections:
- Favorites
- Tags (Labels)
- Reading Lists
"""

import logging
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, Response

from ....database import (
    get_library_by_id,
    get_comic_by_id,
    get_comics_in_library,
    get_reading_progress,
    get_user_by_id,
    add_favorite,
    remove_favorite,
    get_user_favorites,
    is_favorite,
    create_label,
    get_label_by_id,
    get_labels_in_library,
    add_label_to_comic,
    get_comics_with_label,
    get_comic_labels,
    create_reading_list,
    get_reading_list_by_id,
    get_reading_lists_in_library,
    update_reading_list,
    delete_reading_list,
    add_comic_to_reading_list,
    remove_comic_from_reading_list,
    get_reading_list_comics,
)
from ....database.models import Comic, Label, ReadingListItem, Series
from ...middleware import get_current_user_id, get_request_user
from ._shared import get_comic_display_name

logger = logging.getLogger(__name__)

router = APIRouter()


def _legacy_json_response(payload) -> Response:
    """Return JSON payload with YACReader-compatible text/plain content-type."""
    return Response(
        content=json.dumps(payload, ensure_ascii=True, separators=(",", ":")),
        media_type="text/plain; charset=utf-8",
    )


def _split_comic_tags(raw_tags: Optional[str]) -> list[str]:
    """Split stored metadata tags into normalized tag names."""
    if not raw_tags:
        return []

    parts = [part.strip() for part in raw_tags.split(",")]
    return [part for part in parts if part]


def _sync_labels_from_comic_tags(session, library_id: int) -> int:
    """Backfill labels from comic metadata tags for compatibility clients.

    Returns the number of label links that were created.
    """
    comics = get_comics_in_library(session, library_id)
    if not comics:
        return 0

    # Build a lookup for series-level tags so scanner metadata is included.
    series_tag_lookup: dict[str, list[str]] = {}
    series_rows = session.query(Series).filter(Series.library_id == library_id).all()
    for series in series_rows:
        merged_tags = _split_comic_tags(getattr(series, "tags", None))
        if not merged_tags:
            continue

        for candidate in (getattr(series, "name", None), getattr(series, "display_name", None)):
            if candidate:
                series_tag_lookup[candidate.strip().lower()] = merged_tags

    labels_by_name = {label.name.lower(): label for label in get_labels_in_library(session, library_id)}
    created_links = 0

    for comic in comics:
        tag_names = _split_comic_tags(getattr(comic, "tags", None))
        if getattr(comic, "series", None):
            tag_names.extend(series_tag_lookup.get(comic.series.strip().lower(), []))
        if not tag_names:
            continue

        existing_label_ids = {label.id for label in get_comic_labels(session, comic.id)}

        for tag_name in tag_names:
            key = tag_name.lower()
            label = labels_by_name.get(key)
            if label is None:
                label = create_label(session, library_id, tag_name)
                labels_by_name[key] = label

            if label.id in existing_label_ids:
                continue

            add_label_to_comic(session, comic.id, label.id)
            existing_label_ids.add(label.id)
            created_links += 1

    return created_links


# ============================================================================
# Favorites
# ============================================================================

@router.get("/library/{library_id}/favs")
async def get_favorites(request: Request, library_id: Optional[int] = None):
    """
    Get user's favorite comics (v2 API)

    Returns list of favorite comics with metadata
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Get current user or fallback to admin
        user = get_request_user(request, session)

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        library = None
        if library_id is not None:
            library = get_library_by_id(session, library_id)
            if not library:
                raise HTTPException(status_code=404, detail="Library not found")

        # Get favorites for current user
        favorites = get_user_favorites(session, user.id)

        library_uuid = ""
        if library is not None and getattr(library, "uuid", None):
            library_uuid = f"{{{str(library.uuid).strip('{}')}}}"

        result = []
        for fav in favorites:
            comic = get_comic_by_id(session, fav.comic_id)
            if not comic:
                continue
            if library_id is not None and comic.library_id != library_id:
                continue

            # Keep progress fields aligned with other v2 comic list endpoints.
            progress = get_reading_progress(session, user.id, comic.id)
            current_page = progress.current_page if progress else 0
            is_read = progress.is_completed if progress else False

            result.append({
                "type": "comic",
                "id": str(fav.id),
                "comic_info_id": str(comic.id),
                "parent_id": str(comic.folder_id) if comic.folder_id is not None else "0",
                "library_id": str(fav.library_id),
                "library_uuid": library_uuid,
                "file_name": comic.filename,
                "file_size": str(comic.file_size),
                "hash": comic.hash,
                "path": "",
                "current_page": current_page,
                "num_pages": comic.num_pages or 0,
                "read": is_read,
                "manga": getattr(comic, "reading_direction", "ltr") == "rtl",
                "file_type": 0,
                "cover_size_ratio": comic.cover_size_ratio if comic.cover_size_ratio > 0 else 0.67,
                "number": 0,
                "title": comic.title or "",
                "has_been_opened": bool(comic.has_been_opened),
            })

        return _legacy_json_response(result)


@router.post("/library/{library_id}/comic/{comic_id}/fav")
async def add_to_favorites(library_id: int, comic_id: int, request: Request):
    """
    Add a comic to favorites (v2 API)

    Adds the specified comic to the current user's favorites.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Get current user or fallback to admin
        user = get_request_user(request, session)

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get comic and verify it exists in the target library
        comic = get_comic_by_id(session, comic_id)
        if not comic or comic.library_id != library_id:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Check if already favorite
        if is_favorite(session, user.id, comic_id):
            return JSONResponse({
                "success": True,
                "message": "Already in favorites"
            })

        # Add to favorites
        add_favorite(session, user.id, comic.library_id, comic_id)

        return JSONResponse({
            "success": True,
            "comic_id": comic_id
        })


@router.delete("/library/{library_id}/comic/{comic_id}/fav")
async def remove_from_favorites(library_id: int, comic_id: int, request: Request):
    """
    Remove a comic from favorites (v2 API)

    Removes the specified comic from the current user's favorites.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Get current user or fallback to admin
        user = get_request_user(request, session)

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Remove from favorites regardless of current state (idempotent)
        remove_favorite(session, user.id, comic_id)

        return JSONResponse({
            "success": True,
            "comic_id": comic_id
        })


async def check_is_favorite(comic_id: int, request: Request):
    """
    Check if a comic is in the user's favorites (v2 API)

    Returns whether the specified comic is in the current user's favorites.
    Called by app_api bridge (not route-registered directly).
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Get current user or fallback to admin
        user = get_request_user(request, session)

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        favorited = is_favorite(session, user.id, comic_id)

        return JSONResponse({
            "isFavorite": favorited,
            "comic_id": comic_id
        })


# ============================================================================
# Tags (Labels)
# ============================================================================

@router.get("/library/{library_id}/tags")
async def get_tags(library_id: int, request: Request):
    """
    Get all tags for a library (v2 API)

    Returns list of all tags/labels in the specified library.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get all labels in library. If none exist, derive them from comic metadata tags.
        labels = get_labels_in_library(session, library_id)
        if not labels:
            created_links = _sync_labels_from_comic_tags(session, library_id)
            if created_links:
                session.commit()
                logger.info(
                    "Backfilled %s tag links from comic metadata for library %s",
                    created_links,
                    library_id,
                )
            labels = get_labels_in_library(session, library_id)

        result = []
        for label in labels:
            result.append({
                "id": label.id,
                "name": label.name,
                "colorId": label.color_id if hasattr(label, 'color_id') else 0,
                "libraryId": library_id
            })

        return JSONResponse(result)


@router.get("/library/{library_id}/tag/{tag_id}/content")
async def get_tag_content(library_id: int, tag_id: int, request: Request):
    """
    Get comics with a specific tag (v2 API)

    Returns list of comics that have the specified tag.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Verify tag exists
        tag = get_label_by_id(session, tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")

        # Get comics with this label
        comics = get_comics_with_label(session, tag_id)

        result = []
        for comic in comics:
            result.append({
                "id": comic.id,
                "name": get_comic_display_name(comic),
                "fileName": comic.filename,
                "path": comic.path,
                "libraryId": library_id,
                "folderId": comic.folder_id if comic.folder_id else 0
            })

        return JSONResponse(result)


@router.get("/library/{library_id}/tag/{tag_id}/info")
async def get_tag_info(library_id: int, tag_id: int, request: Request):
    """
    Get tag information (v2 API)

    Returns metadata for the specified tag.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get tag info
        tag = get_label_by_id(session, tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")

        # Count comics with this tag
        comics = get_comics_with_label(session, tag_id)
        comic_count = len(comics) if comics else 0

        return JSONResponse({
            "id": tag.id,
            "name": tag.name,
            "colorId": tag.color_id if hasattr(tag, 'color_id') else 0,
            "libraryId": library_id,
            "comicCount": comic_count
        })


# ============================================================================
# Reading Lists
# ============================================================================

@router.get("/library/{library_id}/reading_lists")
async def get_reading_lists(library_id: int, request: Request):
    """
    Get all reading lists for a library (v2 API)

    Returns list of all reading lists in the specified library.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get reading lists for current user (includes their private + public lists)
        user = get_request_user(request, session)
        reading_lists = get_reading_lists_in_library(session, library_id, user_id=user.id if user else None)

        result = []
        for reading_list in reading_lists:
            comics = get_reading_list_comics(session, reading_list.id)
            comic_count = len(comics) if comics else 0
            result.append({
                "type": "reading_list",
                "id": str(reading_list.id),
                "library_id": str(library_id),
                "library_uuid": library.uuid,
                "reading_list_name": reading_list.name,
                # Extra fields are ignored by YACReader but used by /api normalization.
                "description": reading_list.description if hasattr(reading_list, 'description') else "",
                "is_public": reading_list.is_public if hasattr(reading_list, 'is_public') else False,
                "comic_count": comic_count,
            })

        return _legacy_json_response(result)


@router.get("/library/{library_id}/reading_list/{list_id}/content")
async def get_reading_list_content(
    library_id: int,
    list_id: int,
    request: Request
):
    """
    Get comics in a reading list (v2 API)

    Returns list of comics in the specified reading list.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Verify reading list exists
        reading_list = get_reading_list_by_id(session, list_id)
        if not reading_list:
            raise HTTPException(status_code=404, detail="Reading list not found")

        # Get comics in this reading list
        comics = get_reading_list_comics(session, list_id)

        result = []
        for item in comics:
            if isinstance(item, ReadingListItem):
                comic = item.comic
            else:
                comic = item

            if comic:
                try:
                    relative_path = str(Path(comic.path).relative_to(library.path))
                except ValueError:
                    relative_path = comic.filename

                result.append({
                    "type": "comic",
                    "id": str(comic.id),
                    "comic_info_id": str(comic.id),
                    "parent_id": str(comic.folder_id) if comic.folder_id is not None else "0",
                    "library_id": str(library_id),
                    "library_uuid": library.uuid,
                    "file_name": comic.filename,
                    "file_size": str(comic.file_size),
                    "hash": comic.hash,
                    "path": f"/{relative_path}",
                    "current_page": 0,
                    "num_pages": comic.num_pages or 0,
                    "read": False,
                    "manga": getattr(comic, 'reading_direction', 'ltr') == 'rtl',
                    "file_type": 1,
                    "cover_size_ratio": comic.cover_size_ratio if comic.cover_size_ratio > 0 else 0.67,
                    "number": 0,
                    "count": 0,
                    "date": "",
                    "rating": 0,
                    "synopsis": "",
                    "title": get_comic_display_name(comic),
                    "has_been_opened": False,
                    "last_time_opened": 0,
                    "current_page_bookmarked": False,
                    "cover_page": 0,
                    "brightness": 0,
                    "contrast": 0,
                    "gamma": 1.0,
                })

        return _legacy_json_response(result)


@router.get("/library/{library_id}/reading_list/{list_id}/info")
async def get_reading_list_info(
    library_id: int,
    list_id: int,
    request: Request
):
    """
    Get reading list information (v2 API)

    Returns metadata for the specified reading list.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Get reading list info
        reading_list = get_reading_list_by_id(session, list_id)
        if not reading_list:
            raise HTTPException(status_code=404, detail="Reading list not found")

        comics = get_reading_list_comics(session, list_id)
        comic_count = len(comics) if comics else 0

        return _legacy_json_response({
            "type": "reading_list",
            "id": str(reading_list.id),
            "library_id": str(library_id),
            "library_uuid": library.uuid,
            "reading_list_name": reading_list.name,
            # Extra fields are ignored by YACReader but used by /api normalization.
            "description": reading_list.description if hasattr(reading_list, 'description') else "",
            "is_public": reading_list.is_public if hasattr(reading_list, 'is_public') else False,
            "comic_count": comic_count,
        })


async def create_reading_list_endpoint(
    library_id: int,
    request: Request,
    name: str = None,
    description: str = "",
    is_public: bool = False
):
    """
    Create a new reading list (v2 API)

    Creates a new reading list in the specified library.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        if not name:
            raise HTTPException(status_code=400, detail="Reading list name is required")

        # Get current user for list ownership
        user = get_request_user(request, session)

        # Create reading list
        reading_list = create_reading_list(
            session,
            library_id,
            name,
            user_id=user.id if user else None,
            description=description,
            is_public=is_public,
        )

        return JSONResponse({
            "success": True,
            "id": reading_list.id,
            "name": reading_list.name,
            "description": description
        })


async def delete_reading_list_endpoint(
    library_id: int,
    list_id: int,
    request: Request
):
    """
    Delete a reading list (v2 API)

    Deletes the specified reading list from the library.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Verify reading list exists
        reading_list = get_reading_list_by_id(session, list_id)
        if not reading_list:
            raise HTTPException(status_code=404, detail="Reading list not found")

        # Delete reading list
        delete_reading_list(session, list_id)

        return JSONResponse({
            "success": True,
            "list_id": list_id
        })


async def update_reading_list_endpoint(
    library_id: int,
    list_id: int,
    request: Request
):
    """
    Update a reading list (v2 API)

    Updates name, description, and/or public status for the specified reading list.
    Accepts a JSON body with optional fields: name, description, is_public.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Verify reading list exists
        reading_list = get_reading_list_by_id(session, list_id)
        if not reading_list:
            raise HTTPException(status_code=404, detail="Reading list not found")

        # Parse JSON body
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")

        name = body.get("name")
        description = body.get("description")
        is_public = body.get("is_public", body.get("isPublic"))

        if name is not None and not name.strip():
            raise HTTPException(status_code=400, detail="Name cannot be empty")

        updated = update_reading_list(
            session,
            list_id,
            name=name.strip() if name else None,
            description=description,
            is_public=is_public,
        )

        return JSONResponse({
            "success": True,
            "id": updated.id,
            "name": updated.name,
            "description": updated.description or "",
            "isPublic": updated.is_public if hasattr(updated, 'is_public') else False,
        })


async def add_comic_to_reading_list_endpoint(
    library_id: int,
    list_id: int,
    comic_id: int,
    request: Request
):
    """
    Add a comic to a reading list (v2 API)

    Adds the specified comic to the given reading list.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Verify comic exists
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Verify reading list exists
        reading_list = get_reading_list_by_id(session, list_id)
        if not reading_list:
            raise HTTPException(status_code=404, detail="Reading list not found")

        # Add comic to reading list
        add_comic_to_reading_list(session, list_id, comic_id)

        return JSONResponse({
            "success": True,
            "list_id": list_id,
            "comic_id": comic_id
        })


async def remove_comic_from_reading_list_endpoint(
    library_id: int,
    list_id: int,
    comic_id: int,
    request: Request
):
    """
    Remove a comic from a reading list (v2 API)

    Removes the specified comic from the given reading list.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Verify comic exists
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")

        # Verify reading list exists
        reading_list = get_reading_list_by_id(session, list_id)
        if not reading_list:
            raise HTTPException(status_code=404, detail="Reading list not found")

        # Remove comic from reading list
        remove_comic_from_reading_list(session, list_id, comic_id)

        return JSONResponse({
            "success": True,
            "list_id": list_id,
            "comic_id": comic_id
        })

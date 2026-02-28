"""
API v2 Router - Collections

Endpoints for user collections:
- Favorites
- Tags (Labels)
- Reading Lists
"""

import logging
import time
from typing import List, Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from ....database import (
    get_library_by_id,
    get_comic_by_id,
    get_user_by_id,
    get_user_by_username,
    add_favorite,
    remove_favorite,
    get_user_favorites,
    is_favorite,
    create_label,
    get_label_by_id,
    get_labels_in_library,
    delete_label,
    add_label_to_comic,
    remove_label_from_comic,
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
from ....database.models import Comic, Label, ReadingListItem
from ...middleware import get_current_user_id, get_request_user
from ._shared import get_comic_display_name

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Favorites
# ============================================================================

@router.get("/favs")
async def get_favorites(request: Request):
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

        # Get favorites
        favorites = get_user_favorites(session, user.id)

        result = []
        for fav in favorites:
            comic = get_comic_by_id(session, fav.comic_id)
            if comic:
                result.append({
                    "id": comic.id,
                    "type": "comic",
                    "library_id": fav.library_id,
                    "libraryId": fav.library_id,
                    "title": get_comic_display_name(comic),
                    "name": get_comic_display_name(comic),
                    "file_name": comic.filename,
                    "fileName": comic.filename,
                    "hash": comic.hash,
                    "cover_hash": comic.hash,
                    "coverHash": comic.hash,
                    "num_pages": comic.num_pages or 0,
                    "current_page": 0,
                    "series": comic.series,
                    "year": comic.year,
                    "createdAt": fav.created_at if hasattr(fav, "created_at") else int(time.time()),
                    "favoriteDate": fav.created_at if hasattr(fav, "created_at") else int(time.time()),
                })

        return JSONResponse(result)


@router.post("/fav/{comic_id}")
async def add_to_favorites(comic_id: int, request: Request):
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

        # Get comic and verify it exists
        comic = get_comic_by_id(session, comic_id)
        if not comic:
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


@router.delete("/fav/{comic_id}")
async def remove_from_favorites(comic_id: int, request: Request):
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

        # Remove from favorites
        remove_favorite(session, user.id, comic_id)

        return JSONResponse({
            "success": True,
            "comic_id": comic_id
        })


@router.get("/fav/{comic_id}/check")
async def check_is_favorite(comic_id: int, request: Request):
    """
    Check if a comic is in the user's favorites (v2 API)

    Returns whether the specified comic is in the current user's favorites.
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

        # Get all labels in library
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


@router.post("/library/{library_id}/tag")
async def create_tag(
    library_id: int,
    request: Request,
    name: str = None,
    color_id: int = 0
):
    """
    Create a new tag (v2 API)

    Creates a new label/tag in the specified library.
    """
    db = request.app.state.db

    with db.get_session() as session:
        # Verify library exists
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        if not name:
            raise HTTPException(status_code=400, detail="Tag name is required")

        # Create label
        label = create_label(session, library_id, name, color_id)

        return JSONResponse({
            "success": True,
            "id": label.id,
            "name": label.name,
            "colorId": label.color_id if hasattr(label, 'color_id') else 0
        })


@router.delete("/library/{library_id}/tag/{tag_id}")
async def delete_tag(library_id: int, tag_id: int, request: Request):
    """
    Delete a tag (v2 API)

    Deletes the specified tag from the library.
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

        # Delete tag
        delete_label(session, tag_id)

        return JSONResponse({
            "success": True,
            "tag_id": tag_id
        })


@router.post("/library/{library_id}/comic/{comic_id}/tag/{tag_id}")
async def add_tag_to_comic(
    library_id: int,
    comic_id: int,
    tag_id: int,
    request: Request
):
    """
    Add a tag to a comic (v2 API)

    Associates the specified tag with the given comic.
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

        # Verify tag exists
        tag = get_label_by_id(session, tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")

        # Add label to comic
        add_label_to_comic(session, comic_id, tag_id)

        return JSONResponse({
            "success": True,
            "comic_id": comic_id,
            "tag_id": tag_id
        })


@router.delete("/library/{library_id}/comic/{comic_id}/tag/{tag_id}")
async def remove_tag_from_comic(
    library_id: int,
    comic_id: int,
    tag_id: int,
    request: Request
):
    """
    Remove a tag from a comic (v2 API)

    Removes the association between the specified tag and comic.
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

        # Verify tag exists
        tag = get_label_by_id(session, tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")

        # Remove label from comic
        remove_label_from_comic(session, comic_id, tag_id)

        return JSONResponse({
            "success": True,
            "comic_id": comic_id,
            "tag_id": tag_id
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
            # Count comics in this reading list
            comics = get_reading_list_comics(session, reading_list.id)
            comic_count = len(comics) if comics else 0

            result.append({
                "id": reading_list.id,
                "name": reading_list.name,
                "description": reading_list.description if hasattr(reading_list, 'description') else "",
                "isPublic": reading_list.is_public if hasattr(reading_list, 'is_public') else False,
                "libraryId": library_id,
                "comicCount": comic_count
            })

        return JSONResponse(result)


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
                result.append({
                    "id": comic.id,
                    "name": get_comic_display_name(comic),
                    "title": get_comic_display_name(comic),
                    "fileName": comic.filename,
                    "file_name": comic.filename,
                    "path": comic.path,
                    "hash": comic.hash,
                    "cover_hash": comic.hash,
                    "coverHash": comic.hash,
                    "series": comic.series,
                    "year": comic.year,
                    "num_pages": comic.num_pages or 0,
                    "libraryId": library_id,
                    "library_id": library_id,
                    "folderId": comic.folder_id if comic.folder_id else 0
                })

        return JSONResponse(result)


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

        # Count comics in this reading list
        comics = get_reading_list_comics(session, list_id)
        comic_count = len(comics) if comics else 0

        return JSONResponse({
            "id": reading_list.id,
            "name": reading_list.name,
            "description": reading_list.description if hasattr(reading_list, 'description') else "",
            "isPublic": reading_list.is_public if hasattr(reading_list, 'is_public') else False,
            "libraryId": library_id,
            "comicCount": comic_count
        })


@router.post("/library/{library_id}/reading_list")
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


@router.delete("/library/{library_id}/reading_list/{list_id}")
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


@router.patch("/library/{library_id}/reading_list/{list_id}")
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
        is_public = body.get("is_public")

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


@router.post("/library/{library_id}/reading_list/{list_id}/comic/{comic_id}")
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


@router.delete("/library/{library_id}/reading_list/{list_id}/comic/{comic_id}")
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

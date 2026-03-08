"""
Kottlib-native favorites and reading list endpoints.
"""

import json

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from ....database import get_comic_by_id
from ..v2 import collections as v2_collections

router = APIRouter()


def _read_json_response(response):
    if hasattr(response, "body") and isinstance(response.body, (bytes, bytearray)):
        try:
            return json.loads(response.body.decode("utf-8"))
        except Exception:
            return response
    return response


def _to_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def _to_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_reading_list(item: dict, fallback_library_id: int | None = None) -> dict:
    library_id = _to_int(item.get("libraryId", item.get("library_id", fallback_library_id)))
    comic_count = _to_int(item.get("comicCount", item.get("comic_count", 0)))
    is_public = item.get("isPublic", item.get("is_public", False))
    name = item.get("name", item.get("reading_list_name", ""))

    return {
        **item,
        "name": name,
        "libraryId": library_id,
        "library_id": library_id,
        "comicCount": comic_count,
        "comic_count": comic_count,
        "isPublic": is_public,
        "is_public": is_public,
        "description": item.get("description") or "",
    }


def _normalize_reading_list_item(item: dict, fallback_library_id: int | None = None) -> dict:
    library_id = _to_int(item.get("libraryId", item.get("library_id", fallback_library_id)))
    file_name = item.get("fileName", item.get("file_name", ""))
    title = item.get("title", item.get("name", file_name))
    hash_value = item.get("hash", item.get("coverHash", item.get("cover_hash")))
    folder_id = item.get("folderId")
    if folder_id is None:
        parent_id = item.get("parent_id")
        try:
            folder_id = int(parent_id) if parent_id is not None else 0
        except (TypeError, ValueError):
            folder_id = 0

    return {
        **item,
        "id": _to_int(item.get("id"), default=item.get("id")),
        "name": item.get("name", title),
        "title": title,
        "fileName": file_name,
        "file_name": file_name,
        "coverHash": item.get("coverHash", hash_value),
        "cover_hash": item.get("cover_hash", hash_value),
        "libraryId": library_id,
        "library_id": library_id,
        "folderId": folder_id,
    }


def _normalize_favorite_item(item: dict) -> dict:
    library_id = _to_int(item.get("libraryId", item.get("library_id", 0)))
    comic_info_id = _to_int(item.get("comic_info_id", item.get("comicId", item.get("id", 0))))
    favorite_id = _to_int(item.get("id", comic_info_id), default=comic_info_id)
    hash_value = item.get("hash", item.get("coverHash", item.get("cover_hash")))
    file_name = item.get("fileName", item.get("file_name", ""))
    title = item.get("title", item.get("name", ""))

    return {
        **item,
        "id": favorite_id,
        "comic_id": comic_info_id,
        "comicId": comic_info_id,
        "comic_info_id": str(comic_info_id),
        "libraryId": library_id,
        "library_id": library_id,
        "name": item.get("name", title),
        "title": title,
        "fileName": file_name,
        "file_name": file_name,
        "coverHash": item.get("coverHash", hash_value),
        "cover_hash": item.get("cover_hash", hash_value),
        "favoriteDate": _to_int(item.get("favoriteDate", item.get("createdAt", 0))),
        "createdAt": _to_int(item.get("createdAt", item.get("favoriteDate", 0))),
    }


@router.get("/favorites")
async def get_favorites(request: Request):
    response = await v2_collections.get_favorites(request, None)
    payload = _read_json_response(response)
    if not isinstance(payload, list):
        return response
    return JSONResponse([_normalize_favorite_item(item) for item in payload])


@router.post("/favorites/{comic_id}")
async def add_favorite(comic_id: int, request: Request):
    db = request.app.state.db
    with db.get_session() as session:
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")
        library_id = comic.library_id

    return await v2_collections.add_to_favorites(library_id, comic_id, request)


@router.delete("/favorites/{comic_id}")
async def remove_favorite(comic_id: int, request: Request):
    db = request.app.state.db
    with db.get_session() as session:
        comic = get_comic_by_id(session, comic_id)
        if not comic:
            raise HTTPException(status_code=404, detail="Comic not found")
        library_id = comic.library_id

    return await v2_collections.remove_from_favorites(library_id, comic_id, request)


@router.get("/favorites/{comic_id}/check")
async def check_favorite(comic_id: int, request: Request):
    return await v2_collections.check_is_favorite(comic_id, request)


@router.get("/libraries/{library_id}/reading-lists")
async def get_reading_lists(library_id: int, request: Request):
    response = await v2_collections.get_reading_lists(library_id, request)
    payload = _read_json_response(response)
    if not isinstance(payload, list):
        return response
    return JSONResponse([_normalize_reading_list(item, fallback_library_id=library_id) for item in payload])


@router.post("/libraries/{library_id}/reading-lists")
async def create_reading_list(
    library_id: int,
    request: Request,
    name: str = None,
    description: str = "",
    is_public: bool = False,
):
    body = {}
    try:
        parsed = await request.json()
        if isinstance(parsed, dict):
            body = parsed
    except Exception:
        body = {}

    resolved_name = name if name is not None else body.get("name")
    resolved_description = description
    if description == "":
        resolved_description = body.get("description", "")

    resolved_is_public = _to_bool(
        body.get("is_public", body.get("isPublic", is_public)),
        default=is_public,
    )

    response = await v2_collections.create_reading_list_endpoint(
        library_id,
        request,
        resolved_name,
        resolved_description,
        resolved_is_public,
    )
    payload = _read_json_response(response)
    if isinstance(payload, dict):
        payload["isPublic"] = payload.get("isPublic", resolved_is_public)
        payload["is_public"] = payload.get("is_public", payload["isPublic"])
    return JSONResponse(payload) if isinstance(payload, dict) else response


@router.get("/libraries/{library_id}/reading-lists/{list_id}")
async def get_reading_list(library_id: int, list_id: int, request: Request):
    response = await v2_collections.get_reading_list_info(library_id, list_id, request)
    payload = _read_json_response(response)
    if not isinstance(payload, dict):
        return response
    return JSONResponse(_normalize_reading_list(payload, fallback_library_id=library_id))


@router.patch("/libraries/{library_id}/reading-lists/{list_id}")
async def update_reading_list(library_id: int, list_id: int, request: Request):
    response = await v2_collections.update_reading_list_endpoint(library_id, list_id, request)
    payload = _read_json_response(response)
    if not isinstance(payload, dict):
        return response
    # Keep API-native aliases available for mobile clients.
    payload["isPublic"] = payload.get("isPublic", payload.get("is_public", False))
    payload["is_public"] = payload.get("is_public", payload["isPublic"])
    return JSONResponse(payload)


@router.delete("/libraries/{library_id}/reading-lists/{list_id}")
async def delete_reading_list(library_id: int, list_id: int, request: Request):
    return await v2_collections.delete_reading_list_endpoint(library_id, list_id, request)


@router.get("/libraries/{library_id}/reading-lists/{list_id}/items")
async def get_reading_list_items(library_id: int, list_id: int, request: Request):
    response = await v2_collections.get_reading_list_content(library_id, list_id, request)
    payload = _read_json_response(response)
    if not isinstance(payload, list):
        return response
    return JSONResponse([_normalize_reading_list_item(item, fallback_library_id=library_id) for item in payload])


@router.post("/libraries/{library_id}/reading-lists/{list_id}/items/{comic_id}")
async def add_reading_list_item(library_id: int, list_id: int, comic_id: int, request: Request):
    return await v2_collections.add_comic_to_reading_list_endpoint(library_id, list_id, comic_id, request)


@router.delete("/libraries/{library_id}/reading-lists/{list_id}/items/{comic_id}")
async def remove_reading_list_item(
    library_id: int,
    list_id: int,
    comic_id: int,
    request: Request,
):
    return await v2_collections.remove_comic_from_reading_list_endpoint(library_id, list_id, comic_id, request)

"""
Kottlib-native library, browse, tree, and series endpoints.
"""

import json
from typing import Optional

from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from ..v2 import libraries as v2_libraries
from ..v2 import tree as v2_tree
from ..v2 import folders as v2_folders
from ..v2 import series as v2_series

router = APIRouter()


def _read_json_response(response):
    if isinstance(response, JSONResponse):
        return json.loads(response.body.decode("utf-8"))
    return response


def _normalize_tree_node(node, library_id: Optional[int] = None):
    node_type = node.get("type")
    normalized = {
        "id": node.get("id"),
        "name": node.get("name"),
        "type": node_type,
        "children": [],
    }

    if node_type == "library":
        normalized["comicCount"] = node.get("comicCount", node.get("comic_count", 0))
    elif node_type == "folder":
        normalized["folderId"] = node.get("folderId", node.get("id"))
        normalized["libraryId"] = library_id
        normalized["parentId"] = node.get("parentId", node.get("parent_id"))
        normalized["comicCount"] = node.get("comicCount", node.get("comic_count", 0))
    elif library_id is not None:
        normalized["libraryId"] = library_id

    for child in node.get("children", []) or []:
        child_library_id = library_id or (node.get("id") if node_type == "library" else node.get("libraryId"))
        normalized["children"].append(_normalize_tree_node(child, child_library_id))

    return normalized


@router.get("/libraries")
async def list_libraries(request: Request):
    db = request.app.state.db
    with db.get_session() as session:
        return v2_libraries.list_libraries_extended(session)


@router.post("/libraries")
async def create_library(request: Request, data: v2_libraries.CreateLibraryRequest, background_tasks: BackgroundTasks):
    return await v2_libraries.add_library(request, data, background_tasks)


@router.get("/libraries/tree")
async def get_libraries_tree(request: Request, max_depth: int = 10):
    db = request.app.state.db
    with db.get_session() as session:
        response = await v2_tree.get_libraries_series_tree(max_depth, session)
        payload = _read_json_response(response)
        normalized = [_normalize_tree_node(node) for node in payload]
        return JSONResponse(normalized)


@router.get("/libraries/{library_id}")
async def get_library(request: Request, library_id: int):
    db = request.app.state.db
    with db.get_session() as session:
        return v2_libraries.get_library(library_id, session)


@router.put("/libraries/{library_id}")
async def update_library(
    request: Request,
    library_id: int,
    data: v2_libraries.UpdateLibraryRequest,
):
    return await v2_libraries.update_library_details(library_id, request, data)


@router.delete("/libraries/{library_id}")
async def delete_library(request: Request, library_id: int):
    db = request.app.state.db
    with db.get_session() as session:
        return await v2_libraries.remove_library(library_id, request, session)


@router.post("/libraries/{library_id}/scan")
async def scan_library(library_id: int, request: Request, background_tasks: BackgroundTasks):
    return await v2_libraries.scan_library_manual(library_id, request, background_tasks)


@router.get("/libraries/{library_id}/scan/progress")
async def get_library_scan_progress(request: Request, library_id: int):
    db = request.app.state.db
    with db.get_session() as session:
        return await v2_libraries.get_file_scan_progress(library_id, session)


@router.delete("/libraries/{library_id}/scan/progress")
async def clear_library_scan_progress(request: Request, library_id: int):
    db = request.app.state.db
    with db.get_session() as session:
        return await v2_libraries.clear_file_scan_progress(library_id, session)


@router.get("/libraries/{library_id}/tree")
async def get_library_tree(
    request: Request,
    library_id: int,
    max_depth: int = 10,
    folder_id: Optional[int] = None,
):
    db = request.app.state.db
    with db.get_session() as session:
        response = await v2_tree.get_folder_tree(library_id, max_depth, folder_id, session)
        payload = _read_json_response(response)
        if folder_id is not None and folder_id != 0:
            return JSONResponse(_normalize_tree_node(payload, library_id))
        return JSONResponse(_normalize_tree_node(payload))


@router.get("/libraries/{library_id}/folders")
async def get_library_folders(
    request: Request,
    library_id: int,
    folder_id: Optional[int] = None,
):
    return await v2_folders.get_library_folders(library_id, request, folder_id)


@router.get("/library/{library_id}/folder/{folder_id}")
async def get_folder_content(
    request: Request,
    library_id: int,
    folder_id: int,
    sort: Optional[str] = "folders_first",
):
    """Backwards-compatible Kottlib-native folder content alias."""
    return await v2_folders.get_folder_v2(library_id, folder_id, request, sort)


@router.get("/libraries/{library_id}/series")
async def get_library_series(
    request: Request,
    library_id: int,
    sort: str = "name",
    offset: int = 0,
    limit: int = 50,
):
    return await v2_series.get_series_list(
        library_id=library_id,
        request=request,
        sort=sort,
        offset=offset,
        limit=limit,
    )


@router.get("/libraries/{library_id}/series/{series_name:path}")
async def get_series_detail(request: Request, library_id: int, series_name: str):
    return await v2_series.get_series_detail(library_id, series_name, request)


@router.get("/browse/libraries")
async def browse_all_libraries(
    request: Request,
    sort: str = "name",
    offset: int = 0,
    limit: int = 50,
    seed: Optional[int] = None,
):
    return await v2_series.browse_all_content(request, sort, offset, limit, seed)


@router.get("/browse/libraries/{library_id}")
async def browse_library(
    request: Request,
    library_id: int,
    path: Optional[str] = None,
    sort: Optional[str] = "name",
    offset: int = 0,
    limit: int = 50,
    seed: Optional[int] = None,
):
    return await v2_series.browse_folder(library_id, request, path, sort, offset, limit, seed)

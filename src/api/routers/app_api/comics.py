"""
Kottlib-native comic endpoints.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from ..v2 import comics as v2_comics
from ....database import get_comic_by_id, get_sibling_comics

router = APIRouter()


@router.get("/libraries/{library_id}/comics/{comic_id}")
async def get_comic(request: Request, library_id: int, comic_id: int):
    return await v2_comics.get_comic_fullinfo_v2(library_id, comic_id, request)


@router.get("/libraries/{library_id}/comics/{comic_id}/progress")
async def get_comic_progress(request: Request, library_id: int, comic_id: int):
    return await v2_comics.get_comic_progress_v2(library_id, comic_id, request)


@router.post("/libraries/{library_id}/comics/{comic_id}/progress")
async def update_comic_progress(request: Request, library_id: int, comic_id: int):
    return await v2_comics.update_comic_progress_v2_json(library_id, comic_id, request)


@router.get("/libraries/{library_id}/comics/{comic_id}/pages/{page_num}")
async def get_comic_page(request: Request, library_id: int, comic_id: int, page_num: int):
    return await v2_comics.get_comic_page_v2_remote(library_id, comic_id, page_num, request)


@router.get("/libraries/{library_id}/comics/{comic_id}/pages/{page_num}/remote")
async def get_comic_page_remote(request: Request, library_id: int, comic_id: int, page_num: int):
    return await v2_comics.get_comic_page_v2_remote(library_id, comic_id, page_num, request)


@router.get("/libraries/{library_id}/covers/{cover_path:path}")
async def get_cover(request: Request, library_id: int, cover_path: str):
    return await v2_comics.get_cover_v2(library_id, cover_path, request)


@router.get("/libraries/{library_id}/comics/{comic_id}/previous")
async def get_previous_comic(request: Request, library_id: int, comic_id: int):
    db = request.app.state.db
    with db.get_session() as session:
        previous_id, _ = get_sibling_comics(session, comic_id)
        if previous_id is None:
            raise HTTPException(status_code=404, detail="Previous comic not found")
        comic = get_comic_by_id(session, previous_id)
        return JSONResponse({"id": previous_id, "hash": comic.hash if comic else None})


@router.get("/libraries/{library_id}/comics/{comic_id}/next")
async def get_next_comic(request: Request, library_id: int, comic_id: int):
    db = request.app.state.db
    with db.get_session() as session:
        _, next_id = get_sibling_comics(session, comic_id)
        if next_id is None:
            raise HTTPException(status_code=404, detail="Next comic not found")
        comic = get_comic_by_id(session, next_id)
        return JSONResponse({"id": next_id, "hash": comic.hash if comic else None})

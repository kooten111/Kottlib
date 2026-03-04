"""
Kottlib-native favorites and reading list endpoints.
"""

from fastapi import APIRouter, Request

from ..v2 import collections as v2_collections

router = APIRouter()


@router.get("/favorites")
async def get_favorites(request: Request):
    return await v2_collections.get_favorites(request)


@router.post("/favorites/{comic_id}")
async def add_favorite(comic_id: int, request: Request):
    return await v2_collections.add_to_favorites(comic_id, request)


@router.delete("/favorites/{comic_id}")
async def remove_favorite(comic_id: int, request: Request):
    return await v2_collections.remove_from_favorites(comic_id, request)


@router.get("/favorites/{comic_id}/check")
async def check_favorite(comic_id: int, request: Request):
    return await v2_collections.check_is_favorite(comic_id, request)


@router.get("/libraries/{library_id}/reading-lists")
async def get_reading_lists(library_id: int, request: Request):
    return await v2_collections.get_reading_lists(library_id, request)


@router.post("/libraries/{library_id}/reading-lists")
async def create_reading_list(
    library_id: int,
    request: Request,
    name: str = None,
    description: str = "",
    is_public: bool = False,
):
    return await v2_collections.create_reading_list_endpoint(
        library_id,
        request,
        name,
        description,
        is_public,
    )


@router.get("/libraries/{library_id}/reading-lists/{list_id}")
async def get_reading_list(library_id: int, list_id: int, request: Request):
    return await v2_collections.get_reading_list_info(library_id, list_id, request)


@router.patch("/libraries/{library_id}/reading-lists/{list_id}")
async def update_reading_list(library_id: int, list_id: int, request: Request):
    return await v2_collections.update_reading_list_endpoint(library_id, list_id, request)


@router.delete("/libraries/{library_id}/reading-lists/{list_id}")
async def delete_reading_list(library_id: int, list_id: int, request: Request):
    return await v2_collections.delete_reading_list_endpoint(library_id, list_id, request)


@router.get("/libraries/{library_id}/reading-lists/{list_id}/items")
async def get_reading_list_items(library_id: int, list_id: int, request: Request):
    return await v2_collections.get_reading_list_content(library_id, list_id, request)


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

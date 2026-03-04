"""
Kottlib-native search endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Request

from ..v2 import search as v2_search

router = APIRouter()


@router.get("/libraries/{library_id}/search")
@router.post("/libraries/{library_id}/search")
async def search_comics(library_id: int, request: Request, q: Optional[str] = None):
    return await v2_search.search_comics_v2(library_id, request, q)


@router.get("/libraries/{library_id}/search/advanced")
@router.post("/libraries/{library_id}/search/advanced")
async def search_comics_advanced(
    library_id: int,
    request: Request,
    q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    return await v2_search.search_comics_advanced_v2(library_id, request, q, limit, offset)


@router.get("/libraries/{library_id}/search/fields")
async def get_search_fields(library_id: int, request: Request):
    return await v2_search.get_search_fields_v2(library_id, request)


@router.get("/search/query/parse")
async def parse_search_query(q: str):
    return await v2_search.parse_query_v2(q)

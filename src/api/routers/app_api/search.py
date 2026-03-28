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


@router.get("/libraries/{library_id}/search/values/{field}")
async def get_library_search_values(
    library_id: int,
    field: str,
    request: Request,
    q: Optional[str] = None,
    limit: int = 25,
):
    return await v2_search.get_search_values_v2(
        request,
        field=field,
        library_id=library_id,
        q=q,
        limit=limit,
    )


@router.get("/libraries/{library_id}/search/tags")
async def get_library_search_tags(
    library_id: int,
    request: Request,
    q: Optional[str] = None,
    limit: int = 25,
):
    return await v2_search.get_search_tags_v2(request, library_id=library_id, q=q, limit=limit)


@router.get("/search/tags")
async def get_search_tags(request: Request, q: Optional[str] = None, limit: int = 25):
    return await v2_search.get_search_tags_v2(request, q=q, limit=limit)


@router.get("/search/values/{field}")
async def get_search_values(
    field: str,
    request: Request,
    q: Optional[str] = None,
    limit: int = 25,
):
    return await v2_search.get_search_values_v2(
        request,
        field=field,
        q=q,
        limit=limit,
    )


@router.get("/search/query/parse")
async def parse_search_query(q: str):
    return await v2_search.parse_query_v2(q)


@router.get("/libraries/{library_id}/search/facets")
async def get_library_search_facets(
    library_id: int,
    request: Request,
    values_limit: int = 10,
):
    return await v2_search.get_search_facets_v2(
        request,
        library_id=library_id,
        values_limit=values_limit,
    )


@router.get("/libraries/{library_id}/search/facets/values")
async def get_library_search_facet_values(
    library_id: int,
    request: Request,
    fields: str,
    q: Optional[str] = None,
    limit: int = 25,
):
    return await v2_search.get_search_values_batch_v2(
        request,
        fields=fields,
        library_id=library_id,
        q=q,
        limit=limit,
    )

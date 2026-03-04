"""
Kottlib-native reading endpoints.
"""

from fastapi import APIRouter, Request

from ..v2 import reading as v2_reading

router = APIRouter()


@router.get("/reading")
async def get_reading(request: Request, limit: int = 100):
    return await v2_reading.get_all_libraries_reading(request, limit)


@router.get("/libraries/{library_id}/reading")
async def get_library_reading(request: Request, library_id: int, limit: int = 10):
    return await v2_reading.get_reading_list(library_id, request, limit)

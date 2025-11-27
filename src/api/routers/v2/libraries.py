"""
API v2 Router - Libraries

Endpoints for library management and version information.
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

from ....database import get_library_by_id, get_all_libraries
from ....database.models import Comic

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Version Endpoint
# ============================================================================

@router.get("/version")
async def get_version():
    """
    Get server version information

    This is one of the first endpoints the mobile app calls
    Returns plain text version number like YACReader does
    """
    return PlainTextResponse("9.14.2")


# ============================================================================
# Libraries
# ============================================================================

@router.get("/libraries")
async def get_libraries(request: Request):
    """
    Get all libraries (v2 JSON format)

    Returns list of libraries as JSON
    """
    db = request.app.state.db

    with db.get_session() as session:
        libraries = get_all_libraries(session)

        result = []
        for lib in libraries:
            # Count comics in library
            comic_count = session.query(Comic).filter(Comic.library_id == lib.id).count()

            result.append({
                "name": lib.name,
                "id": lib.id,
                "uuid": lib.uuid,
                "path": lib.path,
                "comicCount": comic_count
            })

        return JSONResponse(result)


@router.get("/library/{library_id}/info")
async def get_library_info(library_id: int, request: Request):
    """
    Get library information (v2 JSON format)

    Returns detailed library info
    """
    db = request.app.state.db

    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Count comics in library
        comic_count = session.query(Comic).filter(Comic.library_id == library.id).count()

        return JSONResponse({
            "name": library.name,
            "id": library.id,
            "uuid": library.uuid,
            "path": library.path,
            "comicCount": comic_count
        })

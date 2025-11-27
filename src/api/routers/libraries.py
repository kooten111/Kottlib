"""
Libraries API Router

Modern JSON API for library management
"""

import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from fastapi import APIRouter, Request, HTTPException

from ...database import (
    get_all_libraries,
    get_library_by_id,
    create_library,
    get_library_stats,
    update_library,
    delete_library,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================

class LibraryInfo(BaseModel):
    """Library information response"""
    id: int
    uuid: str
    name: str
    path: str
    created_at: int
    updated_at: int
    last_scan_at: int | None
    scan_status: str
    comic_count: int = 0
    folder_count: int = 0


class CreateLibraryRequest(BaseModel):
    """Create library request"""
    name: str
    path: str
    settings: Optional[Dict[str, Any]] = None


class UpdateLibraryRequest(BaseModel):
    """Update library request"""
    name: Optional[str] = None
    path: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/", response_model=List[LibraryInfo])
async def list_libraries(request: Request):
    """Get all libraries"""
    db = request.app.state.db

    with db.get_session() as session:
        libraries = get_all_libraries(session)

        result = []
        for lib in libraries:
            stats = get_library_stats(session, lib.id)

            result.append(LibraryInfo(
                id=lib.id,
                uuid=lib.uuid,
                name=lib.name,
                path=lib.path,
                created_at=lib.created_at,
                updated_at=lib.updated_at,
                last_scan_at=lib.last_scan_at,
                scan_status=lib.scan_status,
                comic_count=stats.get('comic_count', 0),
                folder_count=stats.get('folder_count', 0),
            ))

        return result


@router.get("/{library_id}", response_model=LibraryInfo)
async def get_library(library_id: int, request: Request):
    """Get library by ID"""
    db = request.app.state.db

    with db.get_session() as session:
        library = get_library_by_id(session, library_id)
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        stats = get_library_stats(session, library.id)

        return LibraryInfo(
            id=library.id,
            uuid=library.uuid,
            name=library.name,
            path=library.path,
            created_at=library.created_at,
            updated_at=library.updated_at,
            last_scan_at=library.last_scan_at,
            scan_status=library.scan_status,
            comic_count=stats.get('comic_count', 0),
            folder_count=stats.get('folder_count', 0),
        )


@router.post("/", response_model=LibraryInfo)
async def add_library(request: Request, data: CreateLibraryRequest):
    """Create a new library"""
    db = request.app.state.db

    with db.get_session() as session:
        library = create_library(
            session,
            name=data.name,
            path=data.path,
            settings=data.settings
        )

        stats = get_library_stats(session, library.id)

        return LibraryInfo(
            id=library.id,
            uuid=library.uuid,
            name=library.name,
            path=library.path,
            created_at=library.created_at,
            updated_at=library.updated_at,
            last_scan_at=library.last_scan_at,
            scan_status=library.scan_status,
            folder_count=stats.get('folder_count', 0),
        )


@router.put("/{library_id}", response_model=LibraryInfo)
async def update_library_details(library_id: int, request: Request, data: UpdateLibraryRequest):
    """Update library details"""
    db = request.app.state.db

    with db.get_session() as session:
        library = update_library(
            session,
            library_id,
            name=data.name,
            path=data.path,
            settings=data.settings
        )
        
        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        stats = get_library_stats(session, library.id)

        return LibraryInfo(
            id=library.id,
            uuid=library.uuid,
            name=library.name,
            path=library.path,
            created_at=library.created_at,
            updated_at=library.updated_at,
            last_scan_at=library.last_scan_at,
            scan_status=library.scan_status,
            comic_count=stats.get('comic_count', 0),
            folder_count=stats.get('folder_count', 0),
        )


@router.delete("/{library_id}")
async def remove_library(library_id: int, request: Request):
    """Delete a library"""
    db = request.app.state.db

    with db.get_session() as session:
        success = delete_library(session, library_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Library not found")
            
        return {"success": True, "message": "Library deleted"}
